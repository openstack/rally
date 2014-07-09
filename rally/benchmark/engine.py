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
from rally import consts
from rally import exceptions
from rally.objects import endpoint
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


CONFIG_SCHEMA = {
    "type": "object",
    "$schema": rutils.JSON_SCHEMA,
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

    An instance of class is initialized by the Orchestrator with the benchmarks
    configuration and then is used to execute all specified scenarios.
    .. note::

        Typical usage:
            ...
            benchmark_engine = BenchmarkEngine(config, task)
            # Deploying the cloud...
            # endpoint - is a dict with data on endpoint of deployed cloud
            with benchmark_engine.bind(endpoints):
                benchmark_engine.run()
    """

    def __init__(self, config, task):
        """BenchmarkEngine constructor.

        :param config: The configuration with specified benchmark scenarios
        :param task: The current task which is being performed
        """
        self.config = config
        self.task = task

    @rutils.log_task_wrapper(LOG.info,
                             _("Task validation of scenarios names."))
    def _validate_config_scenarios_name(self, config):
        available = set(base_scenario.Scenario.list_benchmark_scenarios())
        specified = set(config.iterkeys())

        if not specified.issubset(available):
            names = ", ".join(specified - available)
            raise exceptions.NotFoundScenarios(names=names)

    @rutils.log_task_wrapper(LOG.info, _("Task validation of syntax."))
    def _validate_config_syntax(self, config):
        for scenario, values in config.iteritems():
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
                        pos=pos, args=kw,
                        reason=six.text_type(e)
                    )

    def _validate_config_semantic_helper(self, admin, user, name, pos,
                                         task, kwargs):
        args = {} if not kwargs else kwargs.get("args", {})
        context = {} if not kwargs else kwargs.get("context", {})

        try:
            base_scenario.Scenario.validate(name, args, admin=admin,
                                            users=[user], task=task)
            base_ctx.ContextManager.validate_semantic(context, admin=admin,
                                                      users=[user], task=task)
        except exceptions.InvalidScenarioArgument as e:
            kw = {"name": name, "pos": pos,
                  "args": args, "reason": six.text_type(e)}
            raise exceptions.InvalidBenchmarkConfig(**kw)

    @rutils.log_task_wrapper(LOG.info, _("Task validation of semantic."))
    def _validate_config_semantic(self, config):
        # NOTE(boris-42): In future we will have more complex context, because
        #                 we will have pre-created users mode as well.
        context = {
            "task": self.task,
            "admin": {"endpoint": self.admin_endpoint}
        }
        with users_ctx.UserGenerator(context) as ctx:
            ctx.setup()
            admin = osclients.Clients(self.admin_endpoint)
            user = osclients.Clients(context["users"][0]["endpoint"])

            for name, values in config.iteritems():
                for pos, kwargs in enumerate(values):
                    self._validate_config_semantic_helper(admin, user, name,
                                                          pos, self.task,
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
            raise exceptions.InvalidTaskException(message=str(e))

    def _get_runner(self, config):
        runner = config.get("runner", {})
        runner.setdefault("type", consts.RunnerType.SERIAL)
        return base_runner.ScenarioRunner.get_runner(self.task, self.endpoints,
                                                     runner)

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
                LOG.info("Running benchmark with key: %s" % key)
                runner = self._get_runner(kw)
                is_done = threading.Event()
                consumer = threading.Thread(
                    target=self.consume_results,
                    args=(key, self.task, runner.result_queue, is_done))
                consumer.start()
                runner.run(name, kw.get("context", {}), kw.get("args", {}))
                is_done.set()
                consumer.join()
        self.task.update_status(consts.TaskStatus.FINISHED)

    @rutils.log_task_wrapper(LOG.info, _("Check cloud."))
    def bind(self, endpoints):
        self.endpoints = [endpoint.Endpoint(**endpoint_dict)
                          for endpoint_dict in endpoints]
        # NOTE(msdubov): Passing predefined user endpoints hasn't been
        #                implemented yet, so the scenario runner always gets
        #                a single admin endpoint here.
        self.admin_endpoint = self.endpoints[0]
        self.admin_endpoint.permission = consts.EndpointPermission.ADMIN
        # Try to access cloud via keystone client
        clients = osclients.Clients(self.admin_endpoint)
        clients.verified_keystone()
        return self

    @staticmethod
    def consume_results(key, task, result_queue, is_done):
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
        task.append_results(key, {"raw": results})
