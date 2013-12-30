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

from rally.benchmark import base
from rally.benchmark import runner
from rally import consts
from rally import exceptions
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


class TestEngine(object):
    """The test engine class, an instance of which is initialized by the
    Orchestrator with the benchmarks configuration and then is used to execute
    all specified benchmark scnearios.
    .. note::

        Typical usage:
            ...
            tester = TestEngine(config, task)
            # Deploying the cloud...
            # cloud_endpoints - contains endpoints of deployed cloud
            with tester.bind(cloud_endpoints):
                tester.run()
    """

    def __init__(self, config, task):
        """TestEngine constructor.
        :param config: The configuration with specified benchmark scenarios
        :param task: The current task which is being performed
        """
        self.config = config
        self.task = task
        self._validate_config()

    @rutils.log_task_wrapper(LOG.info, _("Benchmark configs validation."))
    def _validate_config(self):
        task_uuid = self.task['uuid']
        # Perform schema validation
        try:
            jsonschema.validate(self.config, CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            LOG.exception(_('Task %s: Error: %s') % (task_uuid, e.message))
            raise exceptions.InvalidConfigException(message=e.message)

        # Check for benchmark scenario names
        available_scenarios = set(base.Scenario.list_benchmark_scenarios())
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

    def run(self):
        """Runs the benchmarks according to the test configuration
        the test engine was initialized with.

        :returns: List of dicts, each dict containing the results of all the
                  corresponding benchmark test launches
        """
        self.task.update_status(consts.TaskStatus.TEST_TOOL_BENCHMARKING)
        scenario_runner = runner.ScenarioRunner(self.task, self.endpoints)

        results = {}
        for name in self.config:
            for n, kwargs in enumerate(self.config[name]):
                key = {'name': name, 'pos': n, 'kw': kwargs}
                result = scenario_runner.run(name, kwargs)
                self.task.append_results(key, {"raw": result})
                results[json.dumps(key)] = result
        return results

    def bind(self, endpoints):
        self.endpoints = endpoints["identity"]
        # Try to access cloud via keystone client
        clients = osclients.Clients(username=self.endpoints["admin_username"],
                                    password=self.endpoints["admin_password"],
                                    tenant_name=
                                    self.endpoints["admin_tenant_name"],
                                    auth_url=self.endpoints["uri"])

        # Ensure that user is admin
        roles = clients.get_keystone_client().auth_ref['user']['roles']
        if not any("admin" == role['name'] for role in roles):
            message = _("user '%s' doesn't have "
                        "'admin' role") % self.endpoints["admin_username"]
            raise exceptions.InvalidArgumentsException(message=message)
        return self

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            self.task.update_status(consts.TaskStatus.FAILED)
        else:
            self.task.update_status(consts.TaskStatus.FINISHED)
