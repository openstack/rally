# Copyright 2014: Mirantis Inc.
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

import mock

from rally.benchmark import runner
from rally.benchmark.runners import continuous
from rally import consts
from tests import fakes
from tests import test


class ContinuousScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ContinuousScenarioRunnerTestCase, self).setUp()
        admin_keys = ["username", "password", "tenant_name", "auth_url"]
        endpoint_dicts = [dict(zip(admin_keys, admin_keys))]
        endpoint_dicts[0]["permission"] = consts.EndpointPermission.ADMIN
        self.fake_endpoints = endpoint_dicts

    @mock.patch("rally.benchmark.runners.continuous.multiprocessing")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_continuously_for_times(self, mock_osclients,
                                                 mock_multi):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                      self.fake_endpoints)
        srunner.temp_users = ["client"]
        times = 3
        active_users = 4
        timeout = 5
        fake_pool = mock.Mock()
        mock_multi.Pool.return_value = fake_pool
        srunner._run_scenario_continuously_for_times(fakes.FakeScenario,
                                                     "do_it", {},
                                                     times, active_users,
                                                     timeout)
        mock_multi.Pool.assert_called_once_with(active_users)

        expected_pool_calls = [
            mock.call.imap(
                runner._run_scenario_once,
                [(i, fakes.FakeScenario, "do_it", self.fake_endpoints[0],
                 "client", {}) for i in xrange(times)]
            )
        ]
        expected_pool_calls.extend([mock.call.imap().next(timeout)
                                    for i in range(times)])
        expected_pool_calls.extend([
            mock.call.close(),
            mock.call.join()
        ])
        self.assertEqual(fake_pool.mock_calls, expected_pool_calls)

    @mock.patch("rally.benchmark.utils.infinite_run_args")
    @mock.patch("rally.benchmark.runners.continuous.multiprocessing")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_continuously_for_duration(self, mock_osclients,
                                                    mock_multi, mock_generate):
        self.skipTest("This test produce a lot of races so we should fix it "
                      "before running inside in gates")
        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                      self.fake_endpoints)
        srunner.temp_users = ["client"]
        duration = 0
        active_users = 4
        timeout = 5
        mock_multi.Pool.return_value = mock.MagicMock()
        mock_generate.return_value = {}
        srunner._run_scenario_continuously_for_duration(fakes.FakeScenario,
                                                        "do_it", {}, duration,
                                                        active_users, timeout)
        expect = [
            mock.call(active_users),
            mock.call().imap(runner._run_scenario_once, {}),
            mock.call().terminate(),
            mock.call().join()
        ]
        self.assertEqual(mock_multi.Pool.mock_calls, expect)

    @mock.patch("rally.benchmark.runner.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_get_and_run_continuous_runner(self, mock_osclients, mock_base):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = fakes.FakeClients()

        srunner = runner.ScenarioRunner.get_runner(mock.MagicMock(),
                                                   self.fake_endpoints,
                                                   {"execution": "continuous"})
        srunner.temp_users = ["user"]
        self.assertTrue(srunner is not None)

        srunner._run_scenario_continuously_for_times = \
            mock.MagicMock(return_value="times")
        srunner._run_scenario_continuously_for_duration = \
            mock.MagicMock(return_value="duration")

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)
        mock_osclients.return_value = ["client"]
        result = srunner._run_scenario(FakeScenario, "do_it", {"a": 1},
                                       {"times": 2, "active_users": 3,
                                        "timeout": 1})
        self.assertEqual(result, "times")
        srunner._run_scenario_continuously_for_times.assert_called_once_with(
                                    FakeScenario, "do_it", {"a": 1}, 2, 3, 1)
        result = srunner._run_scenario(FakeScenario, "do_it", {"a": 1},
                                       {"duration": 2, "active_users": 3,
                                        "timeout": 1})
        self.assertEqual(result, "duration")
        srunner._run_scenario_continuously_for_duration.\
            assert_called_once_with(FakeScenario, "do_it", {"a": 1}, 2, 3, 1)
