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

import collections
import multiprocessing

import jsonschema
import mock

from rally.plugins.common.runners import serial
from rally.task import runner
from rally.task import scenario
from tests.unit import fakes
from tests.unit import test


BASE = "rally.task.runner."


class ScenarioRunnerHelpersTestCase(test.TestCase):

    @mock.patch(BASE + "utils.format_exc")
    def test_format_result_on_timeout(self, mock_format_exc):
        mock_exc = mock.MagicMock()

        expected = {
            "duration": 100,
            "idle_duration": 0,
            "scenario_output": {"errors": "", "data": {}},
            "atomic_actions": {},
            "error": mock_format_exc.return_value
        }

        self.assertEqual(runner.format_result_on_timeout(mock_exc, 100),
                         expected)
        mock_format_exc.assert_called_once_with(mock_exc)

    @mock.patch(BASE + "context.ContextManager")
    def test_get_scenario_context(self, mock_context_manager):
        mock_context_obj = mock.MagicMock()
        mock_map_for_scenario = (
            mock_context_manager.return_value.map_for_scenario)

        self.assertEqual(mock_map_for_scenario.return_value,
                         runner._get_scenario_context(mock_context_obj))

        mock_context_manager.assert_called_once_with(mock_context_obj)
        mock_map_for_scenario.assert_called_once_with()

    def test_run_scenario_once_internal_logic(self):
        context = runner._get_scenario_context(
            fakes.FakeContext({}).context)
        scenario_cls = mock.MagicMock()
        args = (2, scenario_cls, "test", context, {})
        runner._run_scenario_once(args)

        expected_calls = [
            mock.call(context),
            mock.call().test(),
            mock.call().idle_duration(),
            mock.call().idle_duration(),
            mock.call().atomic_actions()
        ]
        scenario_cls.assert_has_calls(expected_calls, any_order=True)

    @mock.patch(BASE + "rutils.Timer", side_effect=fakes.FakeTimer)
    def test_run_scenario_once_without_scenario_output(self, mock_timer):
        args = (1, fakes.FakeScenario, "do_it", mock.MagicMock(), {})
        result = runner._run_scenario_once(args)

        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "timestamp": fakes.FakeTimer().timestamp(),
            "idle_duration": 0,
            "error": [],
            "scenario_output": {"errors": "", "data": {}},
            "atomic_actions": {}
        }
        self.assertEqual(expected_result, result)

    @mock.patch(BASE + "rutils.Timer", side_effect=fakes.FakeTimer)
    def test_run_scenario_once_with_scenario_output(self, mock_timer):
        args = (1, fakes.FakeScenario, "with_output", mock.MagicMock(), {})
        result = runner._run_scenario_once(args)

        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "timestamp": fakes.FakeTimer().timestamp(),
            "idle_duration": 0,
            "error": [],
            "scenario_output": fakes.FakeScenario(
                test.get_test_context()).with_output(),
            "atomic_actions": {}
        }
        self.assertEqual(expected_result, result)

    @mock.patch(BASE + "rutils.Timer", side_effect=fakes.FakeTimer)
    def test_run_scenario_once_exception(self, mock_timer):
        args = (1, fakes.FakeScenario, "something_went_wrong",
                mock.MagicMock(), {})
        result = runner._run_scenario_once(args)
        expected_error = result.pop("error")
        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "timestamp": fakes.FakeTimer().timestamp(),
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

        self.assertEqual(config[0], runner.ScenarioRunnerResult(config[0]))
        self.assertEqual(config[1], runner.ScenarioRunnerResult(config[1]))

    def test_validate_failed(self):
        config = {"a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          runner.ScenarioRunnerResult, config)


class ScenarioRunnerTestCase(test.TestCase):

    @mock.patch(BASE + "rutils.Timer.duration", return_value=10)
    def test_run(self, mock_timer_duration):
        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())

        runner_obj._run_scenario = mock.MagicMock()

        scenario_name = "NovaServers.boot_server_from_volume_and_delete"
        config_kwargs = {"image": {"id": 1}, "flavor": {"id": 1}}

        context_obj = {
            "task": runner_obj.task,
            "scenario_name": scenario_name,
            "admin": {"endpoint": mock.MagicMock()},
            "config": {
                "cleanup": ["nova", "cinder"], "some_ctx": 2, "users": {}
            }
        }

        result = runner_obj.run(scenario_name, context_obj, config_kwargs)

        self.assertEqual(result, mock_timer_duration.return_value)
        self.assertEqual(list(runner_obj.result_queue), [])

        cls_name, method_name = scenario_name.split(".", 1)
        cls = scenario.Scenario.get(scenario_name)._meta_get("cls_ref")

        expected_config_kwargs = {"image": 1, "flavor": 1}
        runner_obj._run_scenario.assert_called_once_with(
            cls, method_name, context_obj, expected_config_kwargs)

    def test_runner_send_result_exception(self):
        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())
        self.assertRaises(
            jsonschema.ValidationError,
            lambda: runner_obj._send_result(mock.MagicMock()))

    def test_abort(self):
        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())
        self.assertFalse(runner_obj.aborted.is_set())
        runner_obj.abort()
        self.assertTrue(runner_obj.aborted.is_set())

    def test__create_process_pool(self):
        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())

        processes_to_start = 10

        def worker_process(i):
            pass

        counter = ((i,) for i in range(100))

        process_pool = runner_obj._create_process_pool(
            processes_to_start, worker_process, counter)
        self.assertEqual(processes_to_start, len(process_pool))
        for process in process_pool:
            self.assertIsInstance(process, multiprocessing.Process)

    @mock.patch(BASE + "ScenarioRunner._send_result")
    def test__join_processes(self, mock_scenario_runner__send_result):
        process = mock.MagicMock(is_alive=mock.MagicMock(return_value=False))
        processes = 10
        process_pool = collections.deque([process] * processes)
        mock_result_queue = mock.MagicMock(
            empty=mock.MagicMock(return_value=True))

        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())

        runner_obj._join_processes(process_pool, mock_result_queue)

        self.assertEqual(processes, process.join.call_count)
        mock_result_queue.close.assert_called_once_with()
