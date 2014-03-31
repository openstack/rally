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

import jsonschema
import mock

from rally.benchmark.runners import base
from rally.benchmark.runners import continuous
from rally import consts
from rally import exceptions
from tests import fakes
from tests import test


class ScenarioHelpersTestCase(test.TestCase):

    @mock.patch("rally.benchmark.runners.base.random")
    def test_get_scenario_context(self, mock_random):
        mock_random.choice = lambda x: x[1]

        context = {
            "admin": mock.MagicMock(),
            "users": [mock.MagicMock(), mock.MagicMock(), mock.MagicMock()],
            "some_random_key": {
                "nested": mock.MagicMock(),
                "one_more": 10
            }
        }
        expected_context = {
            "admin": context["admin"],
            "user": context["users"][1],
            "some_random_key": context["some_random_key"]
        }

        self.assertEqual(expected_context, base._get_scenario_context(context))

    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_internal_logic(self, mock_clients):
        mock_clients.Clients.return_value = "cl"

        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        scenario_cls = mock.MagicMock()
        args = (2, scenario_cls, "test", context, {})
        base._run_scenario_once(args)

        expected_calls = [
            mock.call(context=context, admin_clients="cl", clients="cl"),
            mock.call().test(),
            mock.call().idle_time(),
            mock.call().idle_time(),
            mock.call().atomic_actions_time()
        ]
        scenario_cls.assert_has_calls(expected_calls, any_order=True)

    @mock.patch("rally.benchmark.runners.base.rutils")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_without_scenario_output(self, mock_clients,
                                                       mock_rutils):
        mock_rutils.Timer = fakes.FakeTimer
        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        args = (1, fakes.FakeScenario, "do_it", context, {})
        result = base._run_scenario_once(args)

        expected_reuslt = {
            "time": fakes.FakeTimer().duration(),
            "idle_time": 0,
            "error": [],
            "scenario_output": {},
            "atomic_actions_time": []
        }
        self.assertEqual(expected_reuslt, result)

    @mock.patch("rally.benchmark.runners.base.rutils")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_with_scenario_output(self, mock_clients,
                                                    mock_rutils):
        mock_rutils.Timer = fakes.FakeTimer
        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        args = (1, fakes.FakeScenario, "with_output", context, {})
        result = base._run_scenario_once(args)

        expected_reuslt = {
            "time": fakes.FakeTimer().duration(),
            "idle_time": 0,
            "error": [],
            "scenario_output": fakes.FakeScenario().with_output(),
            "atomic_actions_time": []
        }
        self.assertEqual(expected_reuslt, result)

    @mock.patch("rally.benchmark.runners.base.rutils")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_exception(self, mock_clients, mock_rutils):
        mock_rutils.Timer = fakes.FakeTimer
        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        args = (1, fakes.FakeScenario, "something_went_wrong", context, {})
        result = base._run_scenario_once(args)
        expected_error = result.pop("error")
        expected_reuslt = {
            "time": fakes.FakeTimer().duration(),
            "idle_time": 0,
            "scenario_output": {},
            "atomic_actions_time": []
        }
        self.assertEqual(expected_reuslt, result)
        self.assertEqual(expected_error[:2],
                         [str(Exception), "Something went wrong"])


class ScenarioRunnerResultTestCase(test.TestCase):

    def test_validate(self):
        config = [
            {
                "time": 1.0,
                "idle_time": 1.0,
                "scenario_output": {
                    "data": {"test": 1.0},
                    "errors": "test error string 1"
                },
                "atomic_actions_time": [{"action": "test1", "duration": 1.0}],
                "error": []
            },
            {
                "time": 2.0,
                "idle_time": 2.0,
                "scenario_output": {
                    "data": {"test": 2.0},
                    "errors": "test error string 2"
                },
                "atomic_actions_time": [{"action": "test2", "duration": 2.0}],
                "error": ["a", "b", "c"]
            }
        ]

        self.assertEqual(config, base.ScenarioRunnerResult(config))

    def test_validate_failed(self):
        config = [{"a": 10}]
        self.assertRaises(jsonschema.ValidationError,
                          base.ScenarioRunnerResult, config)


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

    def test_get_runner(self):

        class NewRunner(base.ScenarioRunner):
            __execution_type__ = "new_runner"

        task = mock.MagicMock()
        endpoints = [mock.MagicMock(), mock.MagicMock()]
        runner = base.ScenarioRunner.get_runner(task, endpoints, "new_runner")

        self.assertEqual(runner.task, task)
        self.assertEqual(runner.endpoints, endpoints)
        self.assertEqual(runner.admin_user, endpoints[0])
        self.assertIsInstance(runner, NewRunner)

    def test_get_runner_no_such(self):
        self.assertRaises(exceptions.NoSuchRunner,
                          base.ScenarioRunner.get_runner,
                          None, None, "NoSuchRunner")

    @mock.patch("rally.benchmark.runners.base.jsonschema.validate")
    def test_validate_default_runner(self, mock_validate):
        config = {"a": 10}
        base.ScenarioRunner.validate(config)
        mock_validate.assert_called_once_with(
                config,
                continuous.ContinuousScenarioRunner.CONFIG_SCHEMA)

    @mock.patch("rally.benchmark.runners.base.ScenarioRunner._run_as_admin")
    def test_run_scenario_runner_results_exception(self, mock_run_method):
        runner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                     self.fake_endpoints)
        self.assertRaises(exceptions.InvalidRunnerResult,
                          runner.run, "NovaServers.boot_server_from_volume_"
                                      "and_delete", mock.MagicMock())
