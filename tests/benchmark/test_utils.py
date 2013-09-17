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

"""Tests for utils."""
import mock
import os

from rally.benchmark import config
from rally.benchmark import engine
from rally.benchmark import tests
from rally.benchmark import utils
from rally import test


def test_dummy():
    pass


def test_dummy_2():
    pass


class UtilsTestCase(test.NoDBTestCase):
    def setUp(self):
        super(UtilsTestCase, self).setUp()
        self.fc = mock.patch('fuel_health.cleanup.cleanup')
        self.fc.start()
        self.cloud_config_manager = config.CloudConfigManager()
        self.cloud_config_path = os.path.abspath('dummy_test.conf')
        with open(self.cloud_config_path, 'w') as f:
            self.cloud_config_manager.write(f)

    def tearDown(self):
        self.fc.stop()
        if os.path.exists(self.cloud_config_path):
            os.remove(self.cloud_config_path)
        super(UtilsTestCase, self).tearDown()

    def test_running_test(self):
        tester = utils.Tester(self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k', 'test_dummy']
        for (times, concurrent) in [(1, 1), (3, 2), (2, 3)]:
            results = tester.run(test, times=times, concurrent=concurrent)
            self.assertEqual(len(results), times)
            for result in results.itervalues():
                self.assertEqual(result['status'], 0)

    def test_running_multiple_tests(self):
        tester = utils.Tester(self.cloud_config_path)
        tests_dict = {
            'test1': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy'],
            'test2': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_2']
        }
        for test_results in tester.run_all(tests_dict):
            for result in test_results.itervalues():
                self.assertEqual(result['status'], 0)

    def test_parameterize_inside_class_from_test_config(self):
        old_benchmark_tests = tests.benchmark_tests.copy()
        tests.benchmark_tests.update({
            'fake.test_parameterize': ['--pyargs',
                                       'rally.benchmark.test_scenarios.fake',
                                       '-k', 'test_parameterize']
        })
        cloud_config = {}
        test_config = {
            'benchmark': {
                'tests_to_run': {
                    'fake.test_parameterize': [{'args': {'arg': 5}}]
                }
            }
        }
        test_engine = engine.TestEngine(test_config)
        with test_engine.bind(cloud_config):
            res = test_engine.benchmark()
            self.assertEqual(res[0].values()[0]['status'], 0)
        tests.benchmark_tests = old_benchmark_tests
