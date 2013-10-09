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
import multiprocessing
import os
import time

from rally.benchmark import base
from rally.benchmark import config
from rally.benchmark import utils
from rally import test
from rally import utils as rally_utils


class FakeScenario(base.Scenario):

    @classmethod
    def class_init(cls, endpoints):
        pass

    @classmethod
    def do_it(cls, ctx, **kwargs):
        pass

    @classmethod
    def too_long(cls, ctx, **kwargs):
        time.sleep(2)

    @classmethod
    def something_went_wrong(cls, ctx, **kwargs):
        raise Exception("Something went wrong")


class FakeTimer(rally_utils.Timer):

    def duration(self):
        return 10


class ScenarioTestCase(test.NoDBTestCase):

    def test_init_calls_register(self):
        with mock.patch("rally.benchmark.utils.base") as mock_base:
            utils.ScenarioRunner(mock.MagicMock(), {})
        self.assertEqual(mock_base.mock_calls, [mock.call.Scenario.register()])

    def test_run_scenario(self):
        runner = utils.ScenarioRunner(mock.MagicMock(), {})
        times = 3

        with mock.patch("rally.benchmark.utils.utils") as mock_utils:
            mock_utils.Timer = FakeTimer
            results = runner._run_scenario("context", FakeScenario, "do_it",
                                           {}, times, 1, 2)

        expected = [{"time": 10, "error": None} for i in range(times)]
        self.assertEqual(results, expected)

    def test_run_scenario_timeout(self):
        runner = utils.ScenarioRunner(mock.MagicMock(), {})
        times = 4
        results = runner._run_scenario("context", FakeScenario, "too_long",
                                       {}, times, 1, 0.1)
        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 0.1)
            self.assertEqual(r['error'][0], str(multiprocessing.TimeoutError))

    def test_run_scenario_exception_inside_test(self):
        runner = utils.ScenarioRunner(mock.MagicMock(), {})
        times = 1
        with mock.patch("rally.benchmark.utils.utils") as mock_utils:
            mock_utils.Timer = FakeTimer
            results = runner._run_scenario("context", FakeScenario,
                                           "something_went_wrong",
                                           {}, times, 1, 1)

        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 10)
            self.assertEqual(r['error'][:2],
                             [str(Exception), "Something went wrong"])

    def test_run_scenario_exception_outside_test(self):
        pass

    def test_run_scenario_concurrency(self):
        runner = utils.ScenarioRunner(mock.MagicMock(), {})
        times = 3
        concurrent = 4
        timeout = 5
        with mock.patch("rally.benchmark.utils.multiprocessing") as mock_multi:
            mock_multi.Pool = mock.MagicMock()
            runner._run_scenario("context", FakeScenario, "do_it",
                                 {}, times, concurrent, timeout)

        expect = [
            mock.call(concurrent),
            mock.call().imap(
                utils._run_scenario_loop,
                [(i, FakeScenario, {}, "do_it", "context", {})
                    for i in xrange(times)]
            )
        ]
        expect.extend([mock.call().imap().next(timeout) for i in range(times)])
        self.assertEqual(mock_multi.Pool.mock_calls, expect)

    def test_run(self):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value="context")

        runner = utils.ScenarioRunner(mock.MagicMock(), {})
        runner._run_scenario = mock.MagicMock(return_value="result")

        with mock.patch("rally.benchmark.utils.base") as mock_base:
            mock_base.Scenario.get_by_name = \
                mock.MagicMock(return_value=FakeScenario)

            result = runner.run("FakeScenario.fake", {})
            self.assertEqual(result, "result")
            runner.run("FakeScenario.fake",
                       {'args': {'a': 1}, 'init': {'arg': 1},
                        'timeout': 1, 'times': 2, 'concurrent': 3})

        expected = [
            mock.call("context", FakeScenario, "fake", {}, 1, 1, 10000),
            mock.call("context", FakeScenario, "fake", {'a': 1}, 2, 3, 1)
        ]
        self.assertEqual(runner._run_scenario.mock_calls, expected)

        expected = [
            mock.call.class_init({}),
            mock.call.init({}),
            mock.call.cleanup('context'),
            mock.call.class_init({}),
            mock.call.init({'arg': 1}),
            mock.call.cleanup('context')
        ]
        self.assertEqual(FakeScenario.mock_calls, expected)


def test_dummy_1():
    pass


def test_dummy_2():
    pass


def test_dummy_timeout():
    time.sleep(1.1)


class VerifierTestCase(test.NoDBTestCase):
    def setUp(self):
        super(VerifierTestCase, self).setUp()
        self.cloud_config_manager = config.CloudConfigManager()
        self.cloud_config_path = os.path.abspath('dummy_test.conf')
        with open(self.cloud_config_path, 'w') as f:
            self.cloud_config_manager.write(f)

    def tearDown(self):
        if os.path.exists(self.cloud_config_path):
            os.remove(self.cloud_config_path)
        super(VerifierTestCase, self).tearDown()

    def test_running_test(self):
        tester = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            test = ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_1']
            for (times, concurrent) in [(1, 1), (3, 2), (2, 3)]:
                results = tester.run(test, times=times, concurrent=concurrent)
                self.assertEqual(len(results), times)
                for result in results.itervalues():
                    self.assertEqual(result['status'], 0)

    def test_running_multiple_tests(self):
        tester = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        tests_dict = {
            'test1': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_1'],
            'test2': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_2']
        }
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            for test_results in tester.run_all(tests_dict):
                for result in test_results.itervalues():
                    self.assertEqual(result['status'], 0)

    def test_tester_timeout(self):
        tester = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k',
                'test_dummy_timeout', '--timeout', '1']
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            results = tester.run(test, times=2, concurrent=2)
            for result in results.values():
                self.assertTrue('Timeout' in result['msg'])
                self.assertTrue(result['status'] != 0)

    def test_tester_no_timeout(self):
        tester = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k',
                'test_dummy_timeout', '--timeout', '2']
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            results = tester.run(test, times=2, concurrent=2)
            for result in results.values():
                self.assertTrue('Timeout' not in result['msg'])
                self.assertTrue(result['status'] == 0)
