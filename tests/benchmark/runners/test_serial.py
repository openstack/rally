# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

from rally.benchmark.runners import serial
from rally import consts
from tests import fakes
from tests import test


class SerialScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(SerialScenarioRunnerTestCase, self).setUp()
        admin_keys = ["username", "password", "tenant_name", "auth_url"]
        endpoint_dicts = [dict(zip(admin_keys, admin_keys))]
        endpoint_dicts[0]["permission"] = consts.EndpointPermission.ADMIN
        self.fake_endpoints = endpoint_dicts

    @mock.patch("rally.benchmark.runners.base._run_scenario_once")
    def test_run_scenario(self, mock_run_once):
        times = 5
        result = {"duration": 10, "idle_duration": 0, "error": [],
                  "scenario_output": {}, "atomic_actions": []}
        mock_run_once.return_value = result
        expected_results = [result for i in range(times)]

        runner = serial.SerialScenarioRunner(mock.MagicMock(),
                                             self.fake_endpoints,
                                             {"times": times})
        results = runner._run_scenario(fakes.FakeScenario, "do_it",
                                       fakes.FakeUserContext({}).context, {})
        self.assertEqual(mock_run_once.call_count, times)
        self.assertEqual(results, expected_results)
