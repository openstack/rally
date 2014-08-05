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

import jsonschema
import mock

from rally.benchmark.runners import base
from rally.benchmark.runners import rps
from rally import consts
from tests import fakes
from tests import test


class RPSScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(RPSScenarioRunnerTestCase, self).setUp()
        admin_keys = ["username", "password", "tenant_name", "auth_url"]
        endpoint_dicts = [dict(zip(admin_keys, admin_keys))]
        endpoint_dicts[0]["permission"] = consts.EndpointPermission.ADMIN
        self.fake_endpoints = endpoint_dicts

    def test_validate(self):
        config = {
            "type": consts.RunnerType.RPS,
            "times": 1,
            "rps": 100,
            "timeout": 1
        }
        rps.RPSScenarioRunner.validate(config)

    def test_validate_failed(self):
        config = {"type": consts.RunnerType.RPS,
                  "a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          rps.RPSScenarioRunner.validate, config)

    def test_run_scenario(self):
        context = fakes.FakeUserContext({}).context
        context['task'] = {'uuid': 'fake_uuid'}
        config = {"times": 3, "rps": 10, "timeout": 5}
        runner = rps.RPSScenarioRunner(
                        None, [context["admin"]["endpoint"]], config)

        runner._run_scenario(fakes.FakeScenario, "do_it", context, {})
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_run_scenario_exception(self):
        context = fakes.FakeUserContext({}).context
        context['task'] = {'uuid': 'fake_uuid'}

        config = {"times": 4, "rps": 10}
        runner = rps.RPSScenarioRunner(
                        None, [context["admin"]["endpoint"]], config)

        runner._run_scenario(fakes.FakeScenario,
                             "something_went_wrong", context, {})
        self.assertEqual(len(runner.result_queue), config["times"])
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    @mock.patch("rally.benchmark.runners.base.scenario_base")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_get_rps_runner(self, mock_osclients, mock_base):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner = base.ScenarioRunner.get_runner(mock.MagicMock(),
                                                self.fake_endpoints,
                                                {"type":
                                                 consts.RunnerType.RPS})
        self.assertIsNotNone(runner)
