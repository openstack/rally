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
import jsonschema
import os
import tempfile

from rally.benchmark import base
from rally.benchmark import config
from rally.benchmark import utils
from rally import consts
from rally import exceptions
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class TestEngine(object):
    """The test engine class, an instance of which is initialized by the
    Orchestrator with the test configuration and then is used to launch OSTF
    tests and to benchmark the deployment.

    .. note::

        Typical usage:
            ...
            test = TestEngine(test_config)
            # Deploying the cloud...
            with test.bind(cloud_config):
                test.verify()
                test.benchmark()
    """

    def __init__(self, test_config, task):
        """TestEngine constructor.

        :param test_config: Dictionary of form {
            "verify": ["sanity", "smoke"]
            "benchmark": {
                "NovaServers.boot_and_delete_server": [
                    {"args": {"flavor_id": <flavor_id>,
                              "image_id": "<image_id>"},
                     "execution": "continuous",
                     "config": {"times": 1, "active_users": 1}},
                    {"args": {"flavor_id": <flavor_id>,
                              "image_id": "<image_id>"},
                     "execution": "continuous",
                     "config": {"times": 4, "active_users": 2}}
                ]
            }
        }
        :param task: The current task which is being performed
        """
        self.task = task

        # NOTE(msdubov): self.verification_tests is a dict since it has
        #                to contain pytest running args, while
        #                self.benchmark_scenarios is just a list of names.
        self.verification_tests = utils.Verifier.list_verification_tests()
        self.benchmark_scenarios = base.Scenario.list_benchmark_scenarios()

        self._validate_test_config(test_config)
        test_config = self._format_test_config(test_config)
        self.test_config = test_config

    @rutils.log_task_wrapper(LOG.info,
                             _("Benchmark & Verification configs validation."))
    def _validate_test_config(self, test_config):
        """Checks whether the given test config is valid and can be used during
        verification and benchmarking tests.

        :param test_config: Dictionary in the same format as for the __init__
                            method.

        :raises: Exception if the test config is not valid
        """
        task_uuid = self.task['uuid']
        # Perform schema validation
        try:
            jsonschema.validate(test_config, config.test_config_schema)
        except jsonschema.ValidationError as e:
            LOG.exception(_('Task %s: Error: %s') % (task_uuid, e.message))
            raise exceptions.InvalidConfigException(message=e.message)

        # Check for verification test names
        for test in test_config['verify']:
            if test not in self.verification_tests:
                LOG.exception(_('Task %s: Error: the specified '
                                'verification test does not exist: %s') %
                              (task_uuid, test))
                raise exceptions.NoSuchVerificationTest(test_name=test)
        # Check for benchmark scenario names
        benchmark_scenarios_set = set(self.benchmark_scenarios)
        for scenario in test_config['benchmark']:
            if scenario not in benchmark_scenarios_set:
                LOG.exception(_('Task %s: Error: the specified '
                                'benchmark scenario does not exist: %s') %
                              (task_uuid, scenario))
                raise exceptions.NoSuchScenario(name=scenario)
            for run in test_config['benchmark'][scenario]:
                if 'times' in run['config'] and 'duration' in run['config']:
                    message = _("'times' and 'duration' cannot be set "
                                "simultaneously for one continuous "
                                "scenario run.")
                    LOG.exception(_('Task %s: Error: %s') % (task_uuid,
                                                             message))
                    raise exceptions.InvalidConfigException(message=message)

    @rutils.log_task_wrapper(LOG.debug, _("Test config formatting."))
    def _format_test_config(self, test_config):
        """Returns a formatted copy of the given valid test config so that
        it can be used during verification and benchmarking tests.

        :param test_config: Dictionary in the same format as for the __init__
                            method.

        :returns: Dictionary
        """
        formatted_test_config = copy.deepcopy(test_config)
        # NOTE(msdubov): if 'verify' is not specified, just run all
        #                verification tests.
        if 'verify' not in formatted_test_config:
            formatted_test_config['verify'] = self.verification_tests.keys()
        return formatted_test_config

    @rutils.log_task_wrapper(LOG.debug,
                             _("Verification configs writing into temp file."))
    def __enter__(self):
        with os.fdopen(self.cloud_config_fd, 'w') as f:
            self.cloud_config.write(f)

    @rutils.log_task_wrapper(LOG.debug, _("Deleting the temp verification "
                                          "config file & Finishing the task."))
    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.remove(self.cloud_config_path)
        if exc_type is not None:
            self.task.update_status(consts.TaskStatus.FAILED)
        else:
            self.task.update_status(consts.TaskStatus.FINISHED)

    @rutils.log_task_wrapper(LOG.info, _('OS cloud binding to Rally.'))
    def bind(self, cloud_config):
        """Binds an existing deployment configuration to the test engine.

        :param cloud_config: The deployment configuration, which sould be
                             passed as a two-level dictionary: the top-level
                             keys should be section names while the keys on
                             the second level should represent option names.
                             E.g., see the default cloud configuration in the
                             rally.benchmark.config.CloudConfigManager class.

        :returns: self (the method should be called in a 'with' statement)
        """
        self.cloud_config = config.CloudConfigManager()
        self.cloud_config.read_from_dict(cloud_config)

        self.cloud_config_fd, self.cloud_config_path = tempfile.mkstemp(
                                                suffix='rallycfg', text=True)
        return self

    @rutils.log_task_wrapper(LOG.info, _('OpenStack cloud verification.'))
    def verify(self):
        """Runs OSTF tests to verify the current cloud deployment.

        :raises: VerificationException if some of the verification tests failed
        """
        self.task.update_status(consts.TaskStatus.TEST_TOOL_VERIFY_OPENSTACK)
        verifier = utils.Verifier(self.task, self.cloud_config_path)
        tests_to_run = self.test_config['verify']
        verification_tests = dict((test, self.verification_tests[test])
                                  for test in tests_to_run)
        test_run_results = verifier.run_all(verification_tests)
        self.task.update_verification_log(json.dumps(test_run_results))
        for result in test_run_results:
            if result['status'] != 0:
                params = {'task': self.task['uuid'], 'err': result['msg']}
                LOG.exception(_('Task %(task)s: One of verification tests '
                                'failed: %(err)s') % params)
                raise exceptions.DeploymentVerificationException(params['err'])

    @rutils.log_task_wrapper(LOG.info, _("Benchmarking."))
    def benchmark(self):
        """Runs the benchmarks according to the test configuration
        the test engine was initialized with.

        :returns: List of dicts, each dict containing the results of all the
                  corresponding benchmark test launches
        """
        self.task.update_status(consts.TaskStatus.TEST_TOOL_BENCHMARKING)
        runer = utils.ScenarioRunner(self.task,
                                     self.cloud_config.to_dict()["identity"])

        results = {}
        scenarios = self.test_config['benchmark']
        for name in scenarios:
            for n, kwargs in enumerate(scenarios[name]):
                key = {'name': name, 'pos': n, 'kw': kwargs}
                result = runer.run(name, kwargs)
                self.task.append_results(key, {"raw": result})
                results[json.dumps(key)] = result
        return results
