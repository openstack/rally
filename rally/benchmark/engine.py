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

import os
import random
import string

from rally.benchmark import tests
from rally.benchmark import utils
from rally import exceptions

import ConfigParser


class TestEngine(object):
    """The test engine class, an instance of which is initialized by the
    Orchestrator with the test configuration and then is used to launch OSTF
    tests, to benchmark the deployment and finally to process the results.

    .. note::

        Typical usage:
            ...
            test = TestEngine(test_config)
            # Deploying the cloud...
            with test.bind(deployment_config):
                test.verify()
                test.benchmark()
                test.process_results()
    """

    def __init__(self, test_config):
        """TestEngine constructor.

        :param test_config: {
                                'verify': ['sanity', 'snapshot', 'smoke'],
                                'benchmark': [
                                    {'method1': {'args': [...], 'times': 1,
                                                 'concurrency': 1}},
                                    {'method2': {'args': [...], 'times': 2,
                                                 'concurrency': 4}},
                                ],
                            }
        """
        self._verify_test_config(test_config)
        self.test_config = test_config

    def _verify_test_config(self, test_config):
        """Verifies and possibly modifies the given test config so that it can
        be used during verification and benchmarking tests.

        :param test_config: Dictionary in the same format as for the __init__
                            method.

        :raises: Exception if the test config is not valid
        """
        if 'verify' in test_config:
            for test_name in test_config['verify']:
                if test_name not in tests.verification_tests:
                    raise exceptions.NoSuchTestException(test_name=test_name)
        else:
            # NOTE(msdubov): if 'verify' not specified, run all verification
            #                tests by default.
            test_config['verify'] = tests.verification_tests.keys()
        # TODO(msdubov): Also verify the 'benchmark' part of the config here.

    def _write_temporary_config(self, config, config_path):
        cp = ConfigParser.RawConfigParser()
        for section in config.iterkeys():
            cp.add_section(section)
            for option in config[section].iterkeys():
                value = config[section][option]
                cp.set(section, option, value)
        with open(config_path, 'w') as f:
            cp.write(f)

    def _delete_temporary_config(self, config_path):
        os.remove(config_path)

    def _random_file_path(self):
        file_name = ''.join(random.choice(string.letters) for i in xrange(16))
        file_path = 'rally/benchmark/temp/'
        return os.path.abspath(file_path + file_name)

    def __enter__(self):
        self._write_temporary_config(self.cloud_config, self.cloud_config_path)

    def __exit__(self, type, value, traceback):
        self._delete_temporary_config(self.cloud_config_path)

    def bind(self, cloud_config):
        """Binds an existing deployment configuration to the test engine.

        :param cloud_config: The deployment configuration, which sould be
                             passed as a two-level dictionary: the top-level
                             keys should be section names while the keys on
                             the second level should represent option names.
                             E.g., {
                                      'identity': {
                                        'admin_name': 'admin',
                                        'admin_password': 'admin',
                                         ...
                                      },
                                      'compute': {
                                        'controller_nodes': 'localhost',
                                        ...
                                      },
                                      ...
                                   }

        :returns: self (the method should be called in a 'with' statement)
        """
        self.cloud_config = cloud_config
        self.cloud_config_path = self._random_file_path()
        return self

    def verify(self):
        """Runs OSTF tests to verify the current cloud deployment.

        :raises: VerificationException if some of the verification tests failed
        """
        tester = utils.Tester(self.cloud_config_path)
        verification_tests = [tests.verification_tests[test_name]
                              for test_name in self.test_config['verify']]
        for test_results in tester.run_all(verification_tests):
            for result in test_results.itervalues():
                if result['status'] != 0:
                    raise exceptions.VerificationException(
                                            test_message=result['msg'])

    def benchmark(self):
        """Runs the benchmarks according to the test configuration
        the test engine was initialized with.
        """
        raise NotImplementedError()

    def process_results(self):
        """Processes benchmarking results using Zipkin & Tomograph."""
        # TODO(msdubov): process results.
        raise NotImplementedError()
