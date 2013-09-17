# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
import jsonschema
import os
import random
import string

from rally.benchmark import config
from rally.benchmark import tests
from rally.benchmark import utils
from rally import exceptions


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

    def __init__(self, test_config):
        """TestEngine constructor.

        :param test_config: Dictionary of form {
            "verify": {
                "tests_to_run": ["sanity", "snapshot", "smoke"]
            },
            "benchmark": {
                "tests_setUp": {
                    "nova.server_metadata": {"servers_to_boot": 10}
                }
                "tests_to_run": {
                    "nova.server_metadata.test_set_and_delete_meta": [
                        {"args": {"amount": 5}, "times": 1, "concurrent": 1},
                        {"args": {"amount": 10}, "times": 4, "concurrent": 2}
                    ]
                }
            }
        }
        """
        self._validate_test_config(test_config)
        test_config = self._format_test_config(test_config)
        self.test_config = config.TestConfigManager(test_config)

    def _validate_test_config(self, test_config):
        """Checks whether the given test config is valid and can be used during
        verification and benchmarking tests.

        :param test_config: Dictionary in the same format as for the __init__
                            method.

        :raises: Exception if the test config is not valid
        """
        # Perform schema verification
        try:
            jsonschema.validate(test_config, config.test_config_schema)
        except jsonschema.ValidationError as e:
            raise exceptions.InvalidConfigException(message=e.message)

        # Check for test names
        for test_type in ['verify', 'benchmark']:
            if (test_type not in test_config or
               'tests_to_run' not in test_config[test_type]):
                continue
            for test in test_config[test_type]['tests_to_run']:
                if test not in tests.tests[test_type]:
                    raise exceptions.NoSuchTestException(test_name=test)

    def _format_test_config(self, test_config):
        """Returns a formatted copy of the given valid test config so that
        it can be used during verification and benchmarking tests.

        :param test_config: Dictionary in the same format as for the __init__
                            method.

        :returns: Dictionary
        """
        formatted_test_config = copy.deepcopy(test_config)
        # NOTE(msdubov): if 'verify' or 'benchmark' tests are not specified,
        #                run them all by default.
        if ('verify' not in formatted_test_config or
           'tests_to_run' not in formatted_test_config['verify']):
            formatted_test_config['verify'] = {
                'tests_to_run': tests.verification_tests.keys()
            }
        if ('benchmark' not in formatted_test_config or
           'tests_to_run' not in formatted_test_config['benchmark']):
            tests_to_run = dict((test_name, [{}])
                                for test_name in tests.benchmark_tests.keys())
            formatted_test_config['benchmark'] = {
                'tests_to_run': tests_to_run
            }
        return formatted_test_config

    def _delete_temporary_config(self, config_path):
        os.remove(config_path)

    def _generate_temporary_file_path(self):
        file_name = ''.join(random.choice(string.letters) for i in xrange(16))
        file_path = 'rally/benchmark/temp/'
        return os.path.abspath(file_path + file_name)

    def __enter__(self):
        with open(self.cloud_config_path, 'w') as f:
            self.cloud_config.write(f)
        with open(self.test_config_path, 'w') as f:
            self.test_config.write(f)

    def __exit__(self, type, value, traceback):
        os.remove(self.cloud_config_path)
        os.remove(self.test_config_path)

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

        self.cloud_config_path = self._generate_temporary_file_path()
        self.test_config_path = self._generate_temporary_file_path()

        return self

    def verify(self):
        """Runs OSTF tests to verify the current cloud deployment.

        :raises: VerificationException if some of the verification tests failed
        """
        tester = utils.Tester(self.cloud_config_path)
        tests_to_run = self.test_config.to_dict()['verify']['tests_to_run']
        verification_tests = dict((test, tests.verification_tests[test])
                                  for test in tests_to_run)
        for test_results in tester.run_all(verification_tests):
            for result in test_results.itervalues():
                if result['status'] != 0:
                    raise exceptions.DeploymentVerificationException(
                                                    test_message=result['msg'])

    def benchmark(self):
        """Runs the benchmarks according to the test configuration
        the test engine was initialized with.

        :returns: List of dicts, each dict containing the results of all the
                  corresponding benchmark test launches
        """
        tester = utils.Tester(self.cloud_config_path, self.test_config_path)
        tests_to_run = self.test_config.to_dict()['benchmark']['tests_to_run']
        benchmark_tests = dict((test, tests.benchmark_tests[test])
                               for test in tests_to_run)
        return tester.run_all(benchmark_tests)
