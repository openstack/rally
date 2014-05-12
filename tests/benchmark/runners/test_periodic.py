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

    def test_validate(self):
        config = {
            "type": consts.RunnerType.PERIODIC,
            "times": 1,
            "period": 0.000001,
            "timeout": 1
        }
        periodic.PeriodicScenarioRunner.validate(config)

    def test_validate_failed(self):
        config = {"type": consts.RunnerType.PERIODIC,
                  "a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          periodic.PeriodicScenarioRunner.validate, config)

    def test_run_scenario(self):
        context = fakes.FakeUserContext({}).context
        context['task'] = {'uuid': 'fake_uuid'}
        config = {"times": 3, "period": 0, "timeout": 5}
        runner = periodic.PeriodicScenarioRunner(
                        None, [context["admin"]["endpoint"]], config)

        result = runner._run_scenario(fakes.FakeScenario, "do_it", context, {})
        self.assertEqual(len(result), config["times"])
        self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_run_scenario_exception(self):
        context = fakes.FakeUserContext({}).context
        context['task'] = {'uuid': 'fake_uuid'}

        config = {"times": 4, "period": 0}
        runner = periodic.PeriodicScenarioRunner(
                        None, [context["admin"]["endpoint"]], config)

        result = runner._run_scenario(fakes.FakeScenario,
                                      "something_went_wrong", context, {})
        self.assertEqual(len(result), config["times"])
        self.assertIsNotNone(base.ScenarioRunnerResult(result))

    @mock.patch("rally.benchmark.runners.periodic.base.ScenarioRunnerResult")
    @mock.patch("rally.benchmark.runners.periodic.multiprocessing")
    @mock.patch("rally.benchmark.runners.periodic.time.sleep")
    def test_run_scenario_internal_logic(self, mock_time, mock_mp,
                                         mock_result):
        context = fakes.FakeUserContext({}).context
        config = {"times": 4, "period": 0, "timeout": 5}
        runner = periodic.PeriodicScenarioRunner(
                        None, [context["admin"]["endpoint"]], config)

        mock_pool_inst = mock.MagicMock()
        mock_mp.Pool.return_value = mock_pool_inst

        runner._run_scenario(fakes.FakeScenario, "do_it", context, {})

        exptected_pool_inst_call = []
        for i in range(config["times"]):
            args = (
                base._run_scenario_once,
                ((i, fakes.FakeScenario, "do_it",
                  base._get_scenario_context(context), {}),)
            )
            exptected_pool_inst_call.append(mock.call.apply_async(*args))
            call = mock.call.close()
            exptected_pool_inst_call.append(call)

        for i in range(config["times"]):
            call = mock.call.apply_async().get(timeout=5)
            exptected_pool_inst_call.append(call)

        mock_mp.assert_has_calls([mock.call.Pool(1)])
        mock_pool_inst.assert_has_calls(exptected_pool_inst_call)
        mock_time.assert_has_calls([])

    @mock.patch("rally.benchmark.runners.base.base")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_get_periodic_runner(self, mock_osclients, mock_base):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner = base.ScenarioRunner.get_runner(mock.MagicMock(),
                                                self.fake_endpoints,
                                                {"type":
                                                 consts.RunnerType.PERIODIC})
        self.assertTrue(runner is not None)
