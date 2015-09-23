# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import json
import threading
import time
import traceback

import jsonschema
import six

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import objects
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.context.keystone import existing_users
from rally.plugins.openstack.context.keystone import users as users_ctx
from rally.task import context
from rally.task import runner
from rally.task import scenario
from rally.task import sla


LOG = logging.getLogger(__name__)


CONFIG_SCHEMA = {
    "type": "object",
    "$schema": consts.JSON_SCHEMA,
    "patternProperties": {
        ".*": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "object"
                    },
                    "runner": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"}
                        },
                        "required": ["type"]
                    },
                    "context": {
                        "type": "object"
                    },
                    "sla": {
                        "type": "object"
                    },
                },
                "additionalProperties": False
            }
        }
    }
}


class ResultConsumer(object):
    """ResultConsumer class stores results from ScenarioRunner, checks SLA."""

    def __init__(self, key, task, runner, abort_on_sla_failure):
        """ResultConsumer constructor.

        :param key: Scenario identifier
        :param task: Task to run
        :param runner: ScenarioRunner instance that produces results to be
                       consumed
        :param abort_on_sla_failure: True if the execution should be stopped
                                     when some SLA check fails
        """

        self.key = key
        self.task = task
        self.runner = runner
        self.sla_checker = sla.SLAChecker(key["kw"])
        self.abort_on_sla_failure = abort_on_sla_failure
        self.is_done = threading.Event()
        self.unexpected_failure = {}
        self.results = []
        self.thread = threading.Thread(
            target=self._consume_results
        )
        self.aborting_checker = threading.Thread(target=self.wait_and_abort)

    def __enter__(self):
        self.thread.start()
        self.aborting_checker.start()
        self.start = time.time()
        return self

    def _consume_results(self):
        while True:
            if self.runner.result_queue:
                result = self.runner.result_queue.popleft()
                self.results.append(result)
                success = self.sla_checker.add_iteration(result)
                if self.abort_on_sla_failure and not success:
                    self.sla_checker.set_aborted_on_sla()
                    self.runner.abort()
            elif self.is_done.isSet():
                break
            else:
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.finish = time.time()
        self.is_done.set()
        self.aborting_checker.join()
        self.thread.join()

        if exc_type:
            self.sla_checker.set_unexpected_failure(exc_value)

        if objects.Task.get_status(
                self.task["uuid"]) == consts.TaskStatus.ABORTED:
            self.sla_checker.set_aborted_manually()

        self.task.append_results(self.key, {
            "raw": self.results,
            "load_duration": self.runner.run_duration,
            "full_duration": self.finish - self.start,
            "sla": self.sla_checker.results()})

    @staticmethod
    def is_task_in_aborting_status(task_uuid, check_soft=True):
        """Checks task is in abort stages

        :param task_uuid: UUID of task to check status
        :type task_uuid: str
        :param check_soft: check or not SOFT_ABORTING status
        :type check_soft: bool
        """
        stages = [consts.TaskStatus.ABORTING, consts.TaskStatus.ABORTED]
        if check_soft:
            stages.append(consts.TaskStatus.SOFT_ABORTING)
        return objects.Task.get_status(task_uuid) in stages

    def wait_and_abort(self):
        """Waits until abort signal is received and aborts runner in this case.

        Has to be run from different thread simultaneously with the
        runner.run method.
        """

        while not self.is_done.isSet():
            if self.is_task_in_aborting_status(self.task["uuid"],
                                               check_soft=False):
                self.runner.abort()
                self.task.update_status(consts.TaskStatus.ABORTED)
                break
            time.sleep(2.0)


class BenchmarkEngine(object):
    """The Benchmark engine class is used to execute benchmark scenarios.

    An instance of this class is initialized by the API with the benchmarks
    configuration and then is used to validate and execute all specified
    in config benchmarks.

    .. note::

        Typical usage:
            ...
            admin = ....  # contains dict representations of objects.Endpoint
                          # with OpenStack admin credentials

            users = ....  # contains a list of dicts of representations of
                          # objects.Endpoint with OpenStack users credentials.

            engine = BenchmarkEngine(config, task, admin=admin, users=users)
            engine.validate()   # to test config
            engine.run()        # to run config
    """

    def __init__(self, config, task, admin=None, users=None,
                 abort_on_sla_failure=False):
        """BenchmarkEngine constructor.

        :param config: The configuration with specified benchmark scenarios
        :param task: The current task which is being performed
        :param admin: Dict with admin credentials
        :param users: List of dicts with user credentials
        :param abort_on_sla_failure: True if the execution should be stopped
                                     when some SLA check fails
        """
        self.config = config
        self.task = task
        self.admin = admin and objects.Endpoint(**admin) or None
        self.existing_users = users or []
        self.abort_on_sla_failure = abort_on_sla_failure

    @rutils.log_task_wrapper(LOG.info, _("Task validation check cloud."))
    def _check_cloud(self):
        clients = osclients.Clients(self.admin)
        clients.verified_keystone()

    @rutils.log_task_wrapper(LOG.info,
                             _("Task validation of scenarios names."))
    def _validate_config_scenarios_name(self, config):
        available = set(s.get_name() for s in scenario.Scenario.get_all())
        specified = set(six.iterkeys(config))

        if not specified.issubset(available):
            names = ", ".join(specified - available)
            raise exceptions.NotFoundScenarios(names=names)

    @rutils.log_task_wrapper(LOG.info, _("Task validation of syntax."))
    def _validate_config_syntax(self, config):
        for scenario_name, values in six.iteritems(config):
            for pos, kw in enumerate(values):
                try:
                    runner.ScenarioRunner.validate(kw.get("runner", {}))
                    context.ContextManager.validate(kw.get("context", {}),
                                                    non_hidden=True)
                    sla.SLA.validate(kw.get("sla", {}))
                except (exceptions.RallyException,
                        jsonschema.ValidationError) as e:
                    raise exceptions.InvalidBenchmarkConfig(
                        name=scenario_name,
                        pos=pos, config=kw,
                        reason=six.text_type(e)
                    )

    def _validate_config_semantic_helper(self, admin, user, name, pos,
                                         deployment, kwargs):
        try:
            scenario.Scenario.validate(
                name, kwargs, admin=admin, users=[user], deployment=deployment)
        except exceptions.InvalidScenarioArgument as e:
            kw = {"name": name, "pos": pos,
                  "config": kwargs, "reason": six.text_type(e)}
            raise exceptions.InvalidBenchmarkConfig(**kw)

    def _get_user_ctx_for_validation(self, ctx):
        if self.existing_users:
            ctx["config"] = {"existing_users": self.existing_users}
            user_context = existing_users.ExistingUsers(ctx)
        else:
            user_context = users_ctx.UserGenerator(ctx)

        return user_context

    @rutils.log_task_wrapper(LOG.info, _("Task validation of semantic."))
    def _validate_config_semantic(self, config):
        self._check_cloud()

        ctx_conf = {"task": self.task, "admin": {"endpoint": self.admin}}
        deployment = objects.Deployment.get(self.task["deployment_uuid"])

        # TODO(boris-42): It's quite hard at the moment to validate case
        #                 when both user context and existing_users are
        #                 specified. So after switching to plugin base
        #                 and refactoring validation mechanism this place
        #                 will be replaced
        with self._get_user_ctx_for_validation(ctx_conf) as ctx:
            ctx.setup()
            admin = osclients.Clients(self.admin)
            user = osclients.Clients(ctx_conf["users"][0]["endpoint"])

            for u in ctx_conf["users"]:
                user = osclients.Clients(u["endpoint"])
                for name, values in six.iteritems(config):
                    for pos, kwargs in enumerate(values):
                        self._validate_config_semantic_helper(
                            admin, user, name, pos, deployment, kwargs)

    @rutils.log_task_wrapper(LOG.info, _("Task validation."))
    def validate(self):
        """Perform full task configuration validation."""
        self.task.update_status(consts.TaskStatus.VERIFYING)
        try:
            jsonschema.validate(self.config, CONFIG_SCHEMA)
            self._validate_config_scenarios_name(self.config)
            self._validate_config_syntax(self.config)
            self._validate_config_semantic(self.config)
        except Exception as e:
            log = [str(type(e)), str(e), json.dumps(traceback.format_exc())]
            self.task.set_failed(log=log)
            raise exceptions.InvalidTaskException(str(e))

    def _get_runner(self, config):
        conf = config.get("runner", {"type": "serial"})
        return runner.ScenarioRunner.get(conf["type"])(self.task, conf)

    def _prepare_context(self, ctx, name, endpoint):
        scenario_context = copy.deepcopy(
            scenario.Scenario.get(name)._meta_get("default_context"))
        if self.existing_users and "users" not in ctx:
            scenario_context.setdefault("existing_users", self.existing_users)
        elif "users" not in ctx:
            scenario_context.setdefault("users", {})

        scenario_context.update(ctx)
        context_obj = {
            "task": self.task,
            "admin": {"endpoint": endpoint},
            "scenario_name": name,
            "config": scenario_context
        }

        return context_obj

    @rutils.log_task_wrapper(LOG.info, _("Benchmarking."))
    def run(self):
        """Run the benchmark according to the test configuration.

        Test configuration is specified on engine initialization.

        :returns: List of dicts, each dict containing the results of all the
                  corresponding benchmark test launches
        """
        self.task.update_status(consts.TaskStatus.RUNNING)
        for name in self.config:
            for n, kw in enumerate(self.config[name]):
                if ResultConsumer.is_task_in_aborting_status(
                        self.task["uuid"]):
                    LOG.info("Received aborting signal.")
                    self.task.update_status(consts.TaskStatus.ABORTED)
                    return
                key = {"name": name, "pos": n, "kw": kw}
                LOG.info("Running benchmark with key: \n%s"
                         % json.dumps(key, indent=2))
                runner_obj = self._get_runner(kw)
                context_obj = self._prepare_context(kw.get("context", {}),
                                                    name, self.admin)
                try:
                    with ResultConsumer(key, self.task, runner_obj,
                                        self.abort_on_sla_failure):
                        with context.ContextManager(context_obj):
                            runner_obj.run(
                                name, context_obj, kw.get("args", {}))
                except Exception as e:
                    LOG.exception(e)

        if objects.Task.get_status(
                self.task["uuid"]) != consts.TaskStatus.ABORTED:
            self.task.update_status(consts.TaskStatus.FINISHED)
