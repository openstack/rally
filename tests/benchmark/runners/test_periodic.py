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

from rally.benchmark.runners import base
from rally.benchmark.runners import periodic
from rally import consts
from tests import fakes
from tests import test


class PeriodicScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(PeriodicScenarioRunnerTestCase, self).setUp()
        admin_keys = ["username", "password", "tenant_name", "auth_url"]
        endpoint_dicts = [dict(zip(admin_keys, admin_keys))]
        endpoint_dicts[0]["permission"] = consts.EndpointPermission.ADMIN
        self.fake_endpoints = endpoint_dicts

    @mock.patch("rally.benchmark.runners.base._run_scenario_once")
    @mock.patch("rally.benchmark.runners.periodic.time.sleep")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario(self, mock_osclients, mock_sleep,
                          mock_run_scenario_once):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        runner = periodic.PeriodicScenarioRunner(mock.MagicMock(),
                                                 self.fake_endpoints)
        times = 3
        period = 4
        runner.users = ["client"]
        runner._run_scenario(fakes.FakeScenario, "do_it", {},
                             {"times": times, "period": period, "timeout": 5})

        expected = [mock.call((i, fakes.FakeScenario, "do_it",
                               self.fake_endpoints[0], "client", {}))
                    for i in xrange(times)]
        self.assertEqual(mock_run_scenario_once.mock_calls, expected)

        expected = [mock.call(period * 60) for i in xrange(times - 1)]
        mock_sleep.has_calls(expected)

    @mock.patch("rally.benchmark.runners.base.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_get_periodic_runner(self, mock_osclients, mock_base):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner = base.ScenarioRunner.get_runner(mock.MagicMock(),
                                                self.fake_endpoints,
                                                {"execution": "periodic"})
        self.assertTrue(runner is not None)
