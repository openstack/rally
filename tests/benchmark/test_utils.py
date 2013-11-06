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
import tempfile
import time

from rally.benchmark import base
from rally.benchmark import config
from rally.benchmark import utils
from rally import test
from rally import utils as rally_utils
from tests.benchmark.scenarios.nova import test_utils


class FakeScenario(base.Scenario):

    @classmethod
    def class_init(cls, endpoints):
        pass

    @classmethod
    def do_it(cls, **kwargs):
        pass

    @classmethod
    def too_long(cls, **kwargs):
        time.sleep(2)

    @classmethod
    def something_went_wrong(cls, **kwargs):
        raise Exception("Something went wrong")


class FakeTimer(rally_utils.Timer):

    def duration(self):
        return 10


class ScenarioTestCase(test.TestCase):

    def setUp(self):
        super(ScenarioTestCase, self).setUp()
        admin_keys = ["admin_username", "admin_password",
                      "admin_tenant_name", "uri"]
        self.fake_kw = dict(zip(admin_keys, admin_keys))

    def test_init_calls_register(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            with mock.patch("rally.benchmark.utils.base") as mock_base:
                utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            self.assertEqual(mock_base.mock_calls,
                             [mock.call.Scenario.register()])

    def test_create_temp_tenants_and_users(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            tenants = 10
            users_per_tenant = 5
            endpoints = runner._create_temp_tenants_and_users(tenants,
                                                              users_per_tenant)
            self.assertEqual(len(endpoints), tenants * users_per_tenant)
            endpoint_keys = set(["username", "password", "tenant_name", "uri"])
            for endpoint in endpoints:
                self.assertEqual(set(endpoint.keys()), endpoint_keys)

    def test_run_scenario(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            with mock.patch("rally.benchmark.utils.utils") as mock_utils:
                runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
                utils.__openstack_clients__ = ["client"]
                times = 3

                mock_utils.Timer = FakeTimer
                results = runner._run_scenario(FakeScenario, "do_it", {},
                                               "continuous",
                                               {"times": times,
                                                "active_users": 1,
                                                "timeout": 2})

        expected = [{"time": 10, "idle_time": 0, "error": None}
                    for i in range(times)]
        self.assertEqual(results, expected)

    def test_run_scenario_timeout(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            utils.__openstack_clients__ = ["client"]
            times = 4
            results = runner._run_scenario(FakeScenario, "too_long", {},
                                           "continuous",
                                           {"times": times,
                                           "active_users": 1,
                                           "timeout": 0.1})
        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 0.1)
            self.assertEqual(r['error'][0], str(multiprocessing.TimeoutError))

    def test_run_scenario_exception_inside_test(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            utils.__openstack_clients__ = ["client"]
            times = 1
            with mock.patch("rally.benchmark.utils.utils") as mock_utils:
                mock_utils.Timer = FakeTimer
                results = runner._run_scenario(FakeScenario,
                                               "something_went_wrong", {},
                                               "continuous",
                                               {"times": times,
                                                "active_users": 1,
                                                "timeout": 1})

        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 10)
            self.assertEqual(r['error'][:2],
                             [str(Exception), "Something went wrong"])

    def test_run_scenario_exception_outside_test(self):
        pass

    @mock.patch("rally.benchmark.utils.multiprocessing")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_continuously_for_times(self, mock_osclients,
                                                 mock_multi):
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        utils.__openstack_clients__ = ["client"]
        times = 3
        active_users = 4
        timeout = 5
        mock_multi.Pool = mock.MagicMock()
        runner._run_scenario_continuously_for_times(FakeScenario, "do_it", {},
                                                    times, active_users,
                                                    timeout)

        expect = [
            mock.call(active_users),
            mock.call().imap(
                utils._run_scenario_loop,
                [(i, FakeScenario, "do_it", {})
                    for i in xrange(times)]
            )
        ]
        expect.extend([mock.call().imap().next(timeout) for i in range(times)])
        expect.extend([mock.call().close(), mock.call().join()])
        self.assertEqual(mock_multi.Pool.mock_calls, expect)

    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.utils.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_concurrency(self, mock_osclients, mock_base,
                                      mock_clients):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        runner._run_scenario_continuously_for_times = \
            mock.MagicMock(return_value="result")
        runner._create_temp_tenants_and_users = mock.MagicMock(
                                                            return_value=[])
        runner._delete_temp_tenants_and_users = mock.MagicMock()

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)
        mock_clients.return_value = ["client"]
        result = runner._run_scenario(FakeScenario, "do_it", {"a": 1},
                                      "continuous", {"times": 2,
                                                     "active_users": 3,
                                                     "timeout": 1})
        self.assertEqual(result, "result")
        expected = [
            mock.call(FakeScenario, "do_it", {"a": 1}, 2, 3, 1)
        ]
        self.assertEqual(runner._run_scenario_continuously_for_times.
                         mock_calls, expected)

    @mock.patch("rally.benchmark.utils._create_openstack_clients")
    @mock.patch("rally.benchmark.utils.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run(self, mock_osclients, mock_base, mock_clients):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        runner._run_scenario = mock.MagicMock(return_value="result")
        runner._create_temp_tenants_and_users = mock.MagicMock(
                                                        return_value=[])
        runner._delete_temp_tenants_and_users = mock.MagicMock()

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)
        result = runner.run("FakeScenario.do_it", {})
        self.assertEqual(result, "result")
        runner.run("FakeScenario.do_it",
                   {"args": {"a": 1}, "init": {"arg": 1},
                    "config": {"timeout": 1, "times": 2, "active_users": 3,
                               "tenants": 5, "users_per_tenant": 2}})

        expected = [
            mock.call(FakeScenario, "do_it", {}, "continuous", {}),
            mock.call(FakeScenario, "do_it", {"a": 1}, "continuous",
                      {"timeout": 1, "times": 2, "active_users": 3,
                       "tenants": 5, "users_per_tenant": 2})
        ]
        self.assertEqual(runner._run_scenario.mock_calls, expected)

        expected = [
            mock.call(1, 1),
            mock.call(5, 2)
        ]
        self.assertEqual(runner._create_temp_tenants_and_users.mock_calls,
                         expected)

        expected = [
            mock.call.init({}),
            mock.call.init({'arg': 1}),
        ]
        self.assertEqual(FakeScenario.mock_calls, expected)


def test_dummy_1():
    pass


def test_dummy_2():
    pass


def test_dummy_timeout():
    time.sleep(1.1)


class VerifierTestCase(test.TestCase):

    def setUp(self):
        super(VerifierTestCase, self).setUp()
        self.cloud_config_manager = config.CloudConfigManager()
        self.cloud_config_fd, self.cloud_config_path = tempfile.mkstemp(
                                                suffix='rallycfg', text=True)
        with os.fdopen(self.cloud_config_fd, 'w') as f:
            self.cloud_config_manager.write(f)

    def tearDown(self):
        if os.path.exists(self.cloud_config_path):
            os.remove(self.cloud_config_path)
        super(VerifierTestCase, self).tearDown()

    def test_running_test(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            test = ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_1']
            result = verifier.run(test)
            self.assertEqual(result['status'], 0)

    def test_running_multiple_tests(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        tests_dict = {
            'test1': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_1'],
            'test2': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_2']
        }
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            for result in verifier.run_all(tests_dict):
                self.assertEqual(result['status'], 0)

    def test_verifier_timeout(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k',
                'test_dummy_timeout', '--timeout', '1']
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            result = verifier.run(test)
            self.assertTrue('Timeout' in result['msg'])
            self.assertTrue(result['status'] != 0)

    def test_verifier_no_timeout(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k',
                'test_dummy_timeout', '--timeout', '2']
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            result = verifier.run(test)
            self.assertTrue('Timeout' not in result['msg'])
            self.assertTrue(result['status'] == 0)
