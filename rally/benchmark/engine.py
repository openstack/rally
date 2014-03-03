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
import jsonschema

from rally.benchmark.context import users as users_ctx
from rally.benchmark.runners import base as base_runner
from rally.benchmark.scenarios import base as base_scenario
from rally.benchmark import utils
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
    "$schema": "http://json-schema.org/draft-03/schema",
    "patternProperties": {
        ".*": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "args": {"type": "object"},
                    "init": {"type": "object"},
                    "execution": {"enum": ["continuous", "periodic"]},
                    "config": {
                        "type": "object",
                        "properties": {
                            "times": {"type": "integer"},
                            "duration": {"type": "number"},
                            "active_users": {"type": "integer"},
                            "period": {"type": "number"},
                            "tenants": {"type": "integer"},
                            "users_per_tenant": {"type": "integer"},
                            "timeout": {"type": "number"}
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            }
        }
    }
}


class BenchmarkEngine(object):
    """The Benchmark engine class, an instance of which is initialized by the
    Orchestrator with the benchmarks configuration and then is used to execute
    all specified benchmark scnearios.
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
        self._validate_config()

    @rutils.log_task_wrapper(LOG.info,
                             _("Benchmark config format validation."))
    def _validate_config(self):
        task_uuid = self.task['uuid']
        # Perform schema validation
        try:
            jsonschema.validate(self.config, CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            LOG.exception(_('Task %s: Error: %s') % (task_uuid, e.message))
            raise exceptions.InvalidConfigException(message=e.message)

        # Check for benchmark scenario names
        available_scenarios = \
            set(base_scenario.Scenario.list_benchmark_scenarios())
        for scenario in self.config:
            if scenario not in available_scenarios:
                LOG.exception(_('Task %s: Error: the specified '
                                'benchmark scenario does not exist: %s') %
                              (task_uuid, scenario))
                raise exceptions.NoSuchScenario(name=scenario)
            # Check for conflicting config parameters
            for run in self.config[scenario]:
                if 'times' in run['config'] and 'duration' in run['config']:
                    message = _("'times' and 'duration' cannot be set "
                                "simultaneously for one continuous "
                                "scenario run.")
                    LOG.exception(_('Task %s: Error: %s') % (task_uuid,
                                                             message))
                    raise exceptions.InvalidConfigException(message=message)
                if ((run.get('execution', 'continuous') == 'periodic' and
                     'active_users' in run['config'])):
                    message = _("'active_users' parameter cannot be set "
                                "for periodic test runs.")
                    LOG.exception(_('Task %s: Error: %s') % (task_uuid,
                                                             message))
                    raise exceptions.InvalidConfigException(message=message)

    @rutils.log_task_wrapper(LOG.info,
                             _("Benchmark config parameters validation."))
    def _validate_scenario_args(self, name, kwargs):
        cls_name, method_name = name.split(".")
        cls = base_scenario.Scenario.get_by_name(cls_name)

        method = getattr(cls, method_name)
        validators = getattr(method, "validators", [])

        args = kwargs.get("args", {})

        # NOTE(msdubov): Some scenarios may require validation from admin,
        #                while others use ordinary clients.
        admin_validators = [v for v in validators
                            if v.permission == consts.EndpointPermission.ADMIN]
        user_validators = [v for v in validators
                           if v.permission == consts.EndpointPermission.USER]

        def validate(validators, clients):
            for validator in validators:
                result = validator(clients=clients, **args)
                if not result.is_valid:
                    raise exceptions.InvalidScenarioArgument(
                                                            message=result.msg)

        # NOTE(msdubov): In case of generated users (= admin mode) - validate
        #                first the admin validators, then the user ones
        #                (with one temporarily created user).
        if self.admin_endpoint:
            admin_client = utils.create_openstack_clients(self.admin_endpoint)
            validate(admin_validators, admin_client)
            context = {
                "task": self.task,
                "admin": {"endpoint": self.admin_endpoint}
            }
            with users_ctx.UserGenerator(context) as generator:
                # TODO(boris-42): refactor this peace
                generator.setup()
                user = context["users"][0]
                user_client = utils.create_openstack_clients(user["endpoint"])
                validate(user_validators, user_client)
        # NOTE(msdubov): In case of pre-created users - validate
        #                for all of them.
        else:
            for user in self.users:
                user_client = utils.create_openstack_clients(user)
                validate(user_validators, user_client)

    def run(self):
        """Runs the benchmarks according to the test configuration
        the benchmark engine was initialized with.

        :returns: List of dicts, each dict containing the results of all the
                  corresponding benchmark test launches
        """
        self.task.update_status(consts.TaskStatus.TEST_TOOL_BENCHMARKING)

        results = {}
        for name in self.config:
            for n, kwargs in enumerate(self.config[name]):
                key = {'name': name, 'pos': n, 'kw': kwargs}
                try:
                    self._validate_scenario_args(name, kwargs)
                    scenario_runner = base_runner.ScenarioRunner.get_runner(
                                            self.task, self.endpoints, kwargs)
                    result = scenario_runner.run(name, kwargs)
                    self.task.append_results(key, {"raw": result,
                                                   "validation":
                                                   {"is_valid": True}})
                    results[json.dumps(key)] = result
                except exceptions.InvalidScenarioArgument as e:
                    self.task.append_results(key, {"raw": [],
                                                   "validation":
                                                   {"is_valid": False,
                                                    "exc_msg": e.message}})
                    self.task.set_failed()
                    LOG.error(_("Scenario (%(pos)s, %(name)s) input arguments "
                                "validation error: %(msg)s") %
                              {"pos": n, "name": name, "msg": e.message})

        return results

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
        clients.get_verified_keystone_client()
        return self

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            self.task.set_failed()
        else:
            self.task.update_status(consts.TaskStatus.FINISHED)
