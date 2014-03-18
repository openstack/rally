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

import mock
import multiprocessing

from rally.benchmark.runners import base
from rally.benchmark.runners import continuous
from rally import consts
from tests import fakes
from tests import test


class ScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ScenarioRunnerTestCase, self).setUp()
        admin_keys = ["username", "password", "tenant_name", "auth_url"]
        endpoint_dicts = [dict(zip(admin_keys, admin_keys))]
        endpoint_dicts[0]["permission"] = consts.EndpointPermission.ADMIN
        self.fake_endpoints = endpoint_dicts

    @mock.patch("rally.benchmark.runners.base.jsonschema.validate")
    @mock.patch("rally.benchmark.runners.base.ScenarioRunner._get_cls")
    def test_validate(self, mock_get_cls, mock_validate):
        mock_get_cls.return_value = fakes.FakeRunner

        config = {"type": "fake", "a": 10}
        base.ScenarioRunner.validate(config)
        mock_get_cls.assert_called_once_with("fake")
        mock_validate.assert_called_once_with(config,
                                              fakes.FakeRunner.CONFIG_SCHEMA)

    @mock.patch("rally.benchmark.runners.base.jsonschema.validate")
    def test_validate_default_runner(self, mock_validate):
        config = {"a": 10}
        base.ScenarioRunner.validate(config)
        mock_validate.assert_called_once_with(
                config,
                continuous.ContinuousScenarioRunner.CONFIG_SCHEMA)

    @mock.patch("rally.benchmark.runners.base.rutils")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario(self, mock_osclients, mock_utils):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                      self.fake_endpoints)
        active_users = 2
        times = 3
        duration = 0.1

        mock_utils.Timer = fakes.FakeTimer
        results = srunner._run_scenario(fakes.FakeScenario, "do_it",
                                        fakes.FakeUserContext({}).context, {},
                                        {"times": times,
                                         "active_users": active_users,
                                         "timeout": 2})
        expected = [{"time": 10, "idle_time": 0, "error": None,
                     "scenario_output": None, "atomic_actions_time": []}
                    for i in range(times)]
        self.assertEqual(results, expected)

        results = srunner._run_scenario(fakes.FakeScenario, "do_it",
                                        fakes.FakeUserContext({}).context, {},
                                        {"duration": duration,
                                         "active_users": active_users,
                                         "timeout": 2})
        expected = [{"time": 10, "idle_time": 0, "error": None,
                     "scenario_output": None, "atomic_actions_time": []}
                    for i in range(active_users)]
        self.assertEqual(results, expected)

    @mock.patch("rally.benchmark.runners.base.osclients")
    @mock.patch("rally.benchmark.runners.continuous.multiprocessing."
                "pool.IMapIterator.next")
    @mock.patch("rally.benchmark.runners.continuous.time.time")
    @mock.patch("rally.benchmark.context.secgroup._prepare_open_secgroup")
    def test_run_scenario_timeout(self, mock_prepare_for_instance_ssh,
                                  mock_time, mock_next, mock_osclients):

        mock_time.side_effect = [1, 2, 3, 10]
        mock_next.side_effect = multiprocessing.TimeoutError()
        mock_osclients.Clients.return_value = fakes.FakeClients()
        runner = base.ScenarioRunner.get_runner(mock.MagicMock(),
                                                self.fake_endpoints,
                                                "continuous")
        times = 4
        active_users = 2
        results = runner._run_scenario(fakes.FakeScenario,
                                       "too_long",
                                       fakes.FakeUserContext({}).context, {},
                                       {"times": times,
                                        "active_users": active_users,
                                        "timeout": 0.01})
        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 0.01)
            self.assertEqual(r['error'][0],
                             str(multiprocessing.TimeoutError))

        duration = 4
        results = runner._run_scenario(fakes.FakeScenario,
                                       "too_long",
                                       fakes.FakeUserContext({}).context, {},
                                       {"duration": duration,
                                        "active_users": active_users,
                                        "timeout": 0.01})
        self.assertEqual(len(results), active_users)
        for r in results:
            self.assertEqual(r['time'], 0.01)
            self.assertEqual(r['error'][0],
                             str(multiprocessing.TimeoutError))

    @mock.patch("rally.benchmark.runners.base.rutils")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_times_exception_inside_test(self, mock_osclients,
                                                      mock_utils):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        mock_utils.Timer = fakes.FakeTimer
        srunner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                      self.fake_endpoints)
        times = 1
        active_users = 2

        results = srunner._run_scenario(fakes.FakeScenario,
                                        "something_went_wrong",
                                        fakes.FakeUserContext({}).context, {},
                                        {"times": times, "timeout": 1,
                                         "active_users": active_users})
        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 10)
            self.assertEqual(r['error'][:2],
                             [str(Exception), "Something went wrong"])

    @mock.patch("rally.benchmark.runners.base.rutils")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_duration_exception_inside_test(self, mock_osclients,
                                                         mock_utils):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        mock_utils.Timer = fakes.FakeTimer
        runner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                     self.fake_endpoints)
        active_users = 2
        results = runner._run_scenario(fakes.FakeScenario,
                                       "something_went_wrong",
                                       fakes.FakeUserContext({}).context, {},
                                       {"duration": 0,
                                        "timeout": 1,
                                        "active_users": active_users})
        for r in results:
            self.assertEqual(r['time'], 10)
            self.assertEqual(r['error'][:2],
                             [str(Exception), "Something went wrong"])
