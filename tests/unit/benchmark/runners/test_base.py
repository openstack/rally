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
from rally.benchmark.runners import serial
from rally.benchmark.scenarios import base as scenario_base
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


class ScenarioHelpersTestCase(test.TestCase):

    @mock.patch("rally.benchmark.runners.base.utils.format_exc")
    def test_format_result_on_timeout(self, mock_format_exc):
        mock_exc = mock.MagicMock()

        expected = {
            "duration": 100,
            "idle_duration": 0,
            "scenario_output": {"errors": "", "data": {}},
            "atomic_actions": {},
            "error": mock_format_exc.return_value
        }

        self.assertEqual(base.format_result_on_timeout(mock_exc, 100),
                         expected)
        mock_format_exc.assert_called_once_with(mock_exc)

    @mock.patch("rally.benchmark.runners.base.random.choice",
                side_effect=lambda x: x[1])
    def test_get_scenario_context(self, mock_random):

        users = list()
        tenants = dict()

        for i in range(2):
            tenants[str(i)] = dict(name=str(i))
            for j in range(3):
                users.append({"id": "%s_%s" % (i, j),
                              "tenant_id": str(i), "endpoint": "endpoint"})

        context = {
            "admin": mock.MagicMock(),
            "users": users,
            "tenants": tenants,
            "some_random_key": {
                "nested": mock.MagicMock(),
                "one_more": 10
            }
        }
        chosen_tenant = context["tenants"][context["users"][1]["tenant_id"]]
        expected_context = {
            "admin": context["admin"],
            "user": context["users"][1],
            "tenant": chosen_tenant,
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
            mock.call().idle_duration(),
            mock.call().idle_duration(),
            mock.call().atomic_actions()
        ]
        scenario_cls.assert_has_calls(expected_calls, any_order=True)

    @mock.patch("rally.benchmark.runners.base.rutils.Timer",
                side_effect=fakes.FakeTimer)
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_without_scenario_output(self, mock_clients,
                                                       mock_rtimer):
        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        args = (1, fakes.FakeScenario, "do_it", context, {})
        result = base._run_scenario_once(args)

        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "idle_duration": 0,
            "error": [],
            "scenario_output": {"errors": "", "data": {}},
            "atomic_actions": {}
        }
        self.assertEqual(expected_result, result)

    @mock.patch("rally.benchmark.runners.base.rutils.Timer",
                side_effect=fakes.FakeTimer)
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_with_scenario_output(self, mock_clients,
                                                    mock_rtimer):
        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        args = (1, fakes.FakeScenario, "with_output", context, {})
        result = base._run_scenario_once(args)

        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "idle_duration": 0,
            "error": [],
            "scenario_output": fakes.FakeScenario().with_output(),
            "atomic_actions": {}
        }
        self.assertEqual(expected_result, result)

    @mock.patch("rally.benchmark.runners.base.rutils.Timer",
                side_effect=fakes.FakeTimer)
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_run_scenario_once_exception(self, mock_clients, mock_rtimer):
        context = base._get_scenario_context(fakes.FakeUserContext({}).context)
        args = (1, fakes.FakeScenario, "something_went_wrong", context, {})
        result = base._run_scenario_once(args)
        expected_error = result.pop("error")
        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "idle_duration": 0,
            "scenario_output": {"errors": "", "data": {}},
            "atomic_actions": {}
        }
        self.assertEqual(expected_result, result)
        self.assertEqual(expected_error[:2],
                         ["Exception", "Something went wrong"])


class ScenarioRunnerResultTestCase(test.TestCase):

    def test_validate(self):
        config = [
            {
                "duration": 1.0,
                "idle_duration": 1.0,
                "scenario_output": {
                    "data": {"test": 1.0},
                    "errors": "test error string 1"
                },
                "atomic_actions": {"test1": 1.0},
                "error": []
            },
            {
                "duration": 2.0,
                "idle_duration": 2.0,
                "scenario_output": {
                    "data": {"test": 2.0},
                    "errors": "test error string 2"
                },
                "atomic_actions": {"test2": 2.0},
                "error": ["a", "b", "c"]
            }
        ]

        self.assertEqual(config[0], base.ScenarioRunnerResult(config[0]))
        self.assertEqual(config[1], base.ScenarioRunnerResult(config[1]))

    def test_validate_failed(self):
        config = {"a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          base.ScenarioRunnerResult, config)


class ScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ScenarioRunnerTestCase, self).setUp()

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
        config = {"type": "new_runner", "a": 123}
        runner = base.ScenarioRunner.get_runner(task, config)

        self.assertEqual(runner.task, task)
        self.assertEqual(runner.config, config)
        self.assertIsInstance(runner, NewRunner)

    def test_get_runner_no_such(self):
        self.assertRaises(exceptions.NoSuchRunner,
                          base.ScenarioRunner.get_runner,
                          None, {"type": "NoSuchRunner"})

    @mock.patch("rally.benchmark.runners.base.jsonschema.validate")
    def test_validate_default_runner(self, mock_validate):
        config = {"a": 10}
        base.ScenarioRunner.validate(config)
        mock_validate.assert_called_once_with(
                config,
                serial.SerialScenarioRunner.CONFIG_SCHEMA)

    @mock.patch("rally.benchmark.runners.base.rutils.Timer.duration",
                return_value=10)
    def test_run(self, mock_duration):
        runner = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())

        runner._run_scenario = mock.MagicMock()

        scenario_name = "NovaServers.boot_server_from_volume_and_delete"
        config_kwargs = {"image": {"id": 1}, "flavor": {"id": 1}}

        context_obj = {
            "task": runner.task,
            "scenario_name": scenario_name,
            "admin": {"endpoint": mock.MagicMock()},
            "config": {
                "cleanup": ["nova", "cinder"], "some_ctx": 2, "users": {}
            }
        }

        result = runner.run(scenario_name, context_obj, config_kwargs)

        self.assertEqual(result, mock_duration.return_value)
        self.assertEqual(list(runner.result_queue), [])

        cls_name, method_name = scenario_name.split(".", 1)
        cls = scenario_base.Scenario.get_by_name(cls_name)

        expected_config_kwargs = {"image": 1, "flavor": 1}
        runner._run_scenario.assert_called_once_with(
            cls, method_name, context_obj, expected_config_kwargs)

    def test_runner_send_result_exception(self):
        runner = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())
        self.assertRaises(
            jsonschema.ValidationError,
            lambda: runner._send_result(mock.MagicMock()))
