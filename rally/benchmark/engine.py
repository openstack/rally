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

import json
import threading
import time
import traceback

import jsonschema
import six

from rally.benchmark.context import base as base_ctx
from rally.benchmark.context import users as users_ctx
from rally.benchmark.runners import base as base_runner
from rally.benchmark.scenarios import base as base_scenario
from rally.benchmark.sla import base as base_sla
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import objects
from rally import osclients


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
                        "type": "object",
                    },
                },
                "additionalProperties": False
            }
        }
    }
}


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

    def __init__(self, config, task, admin=None, users=None):
        """BenchmarkEngine constructor.

        :param config: The configuration with specified benchmark scenarios
        :param task: The current task which is being performed
        :param admin: Dict with admin credentials
        :param users: List of dicts with user credentials
        """
        self.config = config
        self.task = task
        self.admin = admin and objects.Endpoint(**admin) or None
        self.users = map(lambda u: objects.Endpoint(**u), users or [])

    @rutils.log_task_wrapper(LOG.info, _("Task validation check cloud."))
    def _check_cloud(self):
        clients = osclients.Clients(self.admin)
        clients.verified_keystone()

    @rutils.log_task_wrapper(LOG.info,
                             _("Task validation of scenarios names."))
    def _validate_config_scenarios_name(self, config):
        available = set(base_scenario.Scenario.list_benchmark_scenarios())
        specified = set(six.iterkeys(config))

        if not specified.issubset(available):
            names = ", ".join(specified - available)
            raise exceptions.NotFoundScenarios(names=names)

    @rutils.log_task_wrapper(LOG.info, _("Task validation of syntax."))
    def _validate_config_syntax(self, config):
        for scenario, values in six.iteritems(config):
            for pos, kw in enumerate(values):
                try:
                    base_runner.ScenarioRunner.validate(kw.get("runner", {}))
                    base_ctx.ContextManager.validate(kw.get("context", {}),
                                                     non_hidden=True)
                    base_sla.SLA.validate(kw.get("sla", {}))
                except (exceptions.RallyException,
                        jsonschema.ValidationError) as e:
                    raise exceptions.InvalidBenchmarkConfig(
                        name=scenario,
                        pos=pos, config=kw,
                        reason=six.text_type(e)
                    )

    def _validate_config_semantic_helper(self, admin, user, name, pos,
                                         deployment, kwargs):
        try:
            base_scenario.Scenario.validate(name, kwargs, admin=admin,
                                            users=[user],
                                            deployment=deployment)
        except exceptions.InvalidScenarioArgument as e:
            kw = {"name": name, "pos": pos,
                  "config": kwargs, "reason": six.text_type(e)}
            raise exceptions.InvalidBenchmarkConfig(**kw)

    @rutils.log_task_wrapper(LOG.info, _("Task validation of semantic."))
    def _validate_config_semantic(self, config):
        self._check_cloud()

        # NOTE(boris-42): In future we will have more complex context, because
        #                 we will have pre-created users mode as well.
        context = {"task": self.task, "admin": {"endpoint": self.admin}}
        deployment = objects.Deployment.get(self.task["deployment_uuid"])

        with users_ctx.UserGenerator(context) as ctx:
            ctx.setup()
            admin = osclients.Clients(self.admin)
            user = osclients.Clients(context["users"][0]["endpoint"])

            for name, values in six.iteritems(config):
                for pos, kwargs in enumerate(values):
                    self._validate_config_semantic_helper(admin, user, name,
                                                          pos, deployment,
                                                          kwargs)

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
        runner = config.get("runner", {})
        runner.setdefault("type", consts.RunnerType.SERIAL)
        return base_runner.ScenarioRunner.get_runner(self.task,
                                                     runner)

    def _prepare_context(self, context, name, endpoint):
        scenario_context = base_scenario.Scenario.meta(name, "context")
        scenario_context.setdefault("users", {})
        scenario_context.update(context)
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
                key = {'name': name, 'pos': n, 'kw': kw}
                LOG.info("Running benchmark with key: \n%s"
                         % json.dumps(key, indent=2))
                runner = self._get_runner(kw)
                is_done = threading.Event()
                consumer = threading.Thread(
                    target=self.consume_results,
                    args=(key, self.task, runner.result_queue, is_done))
                consumer.start()
                context_obj = self._prepare_context(kw.get("context", {}),
                                                    name, self.admin)
                self.duration = 0
                self.full_duration = 0
                try:
                    with rutils.Timer() as timer:
                        with base_ctx.ContextManager(context_obj):
                            self.duration = runner.run(name, context_obj,
                                                       kw.get("args", {}))
                except Exception as e:
                    LOG.exception(e)
                finally:
                    self.full_duration = timer.duration()
                    is_done.set()
                    consumer.join()
        self.task.update_status(consts.TaskStatus.FINISHED)

    def consume_results(self, key, task, result_queue, is_done):
        """Consume scenario runner results from queue and send them to db.

        Has to be run from different thread simultaneously with the runner.run
        method.

        :param key: Scenario identifier
        :param task: Running task
        :param result_queue: Deque with runner results
        :param is_done: Event which is set from the runner thread after the
                        runner finishes it's work.
        """
        results = []
        while True:
            if result_queue:
                result = result_queue.popleft()
                results.append(result)
            elif is_done.isSet():
                break
            else:
                time.sleep(0.1)

        sla = base_sla.SLA.check_all(key["kw"], results)
        task.append_results(key, {"raw": results,
                                  "load_duration": self.duration,
                                  "full_duration": self.full_duration,
                                  "sla": sla})
