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
from unittest import mock

import ddt

from rally.plugins.task.runners import serial
from rally.task import runner
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
            "output": {"additive": [], "complete": []},
            "atomic_actions": [],
            "error": mock_format_exc.return_value
        }

        self.assertEqual(expected,
                         runner.format_result_on_timeout(mock_exc, 100))
        mock_format_exc.assert_called_once_with(mock_exc)

    def test_get_scenario_context(self):
        context_obj = {"foo": "bar"}
        result = runner._get_scenario_context(13, context_obj)
        self.assertEqual({"foo": "bar", "iteration": 14}, result)

    def test_run_scenario_once_internal_logic(self):
        context = runner._get_scenario_context(
            12, fakes.FakeContext({}).context)
        scenario_cls = mock.MagicMock()
        event_queue = mock.MagicMock()

        runner._run_scenario_once(
            scenario_cls, "test", context, {}, event_queue)

        expected_calls = [
            mock.call(context),
            mock.call().test(),
            mock.call().idle_duration(),
            mock.call().idle_duration(),
            mock.call().atomic_actions()
        ]
        scenario_cls.assert_has_calls(expected_calls, any_order=True)

        event_queue.put.assert_called_once_with(
            {"type": "iteration", "value": 13})

    @mock.patch(BASE + "rutils.Timer", side_effect=fakes.FakeTimer)
    def test_run_scenario_once_without_scenario_output(self, mock_timer):
        result = runner._run_scenario_once(
            fakes.FakeScenario, "do_it", mock.MagicMock(), {},
            mock.MagicMock())

        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "timestamp": fakes.FakeTimer().timestamp(),
            "idle_duration": 0,
            "error": [],
            "output": {"additive": [], "complete": []},
            "atomic_actions": []
        }
        self.assertEqual(expected_result, result)

    @mock.patch(BASE + "rutils.Timer", side_effect=fakes.FakeTimer)
    def test_run_scenario_once_with_added_scenario_output(self, mock_timer):
        result = runner._run_scenario_once(
            fakes.FakeScenario, "with_add_output", mock.MagicMock(), {},
            mock.MagicMock())

        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "timestamp": fakes.FakeTimer().timestamp(),
            "idle_duration": 0,
            "error": [],
            "output": {"additive": [{"chart_plugin": "FooPlugin",
                                     "description": "Additive description",
                                     "data": [["a", 1]],
                                     "title": "Additive"}],
                       "complete": [{"data": [["a", [[1, 2], [2, 3]]]],
                                     "description": "Complete description",
                                     "title": "Complete",
                                     "chart_plugin": "BarPlugin"}]},
            "atomic_actions": []
        }
        self.assertEqual(expected_result, result)

    @mock.patch(BASE + "rutils.Timer", side_effect=fakes.FakeTimer)
    def test_run_scenario_once_exception(self, mock_timer):
        result = runner._run_scenario_once(
            fakes.FakeScenario, "something_went_wrong", mock.MagicMock(), {},
            mock.MagicMock())
        expected_error = result.pop("error")
        expected_result = {
            "duration": fakes.FakeTimer().duration(),
            "timestamp": fakes.FakeTimer().timestamp(),
            "idle_duration": 0,
            "output": {"additive": [], "complete": []},
            "atomic_actions": []
        }
        self.assertEqual(expected_result, result)
        self.assertEqual(expected_error[:2],
                         ["Exception", "Something went wrong"])


@ddt.ddt
class ScenarioRunnerTestCase(test.TestCase):

    @mock.patch(BASE + "rutils.Timer.duration", return_value=10)
    def test_run(self, mock_timer_duration):
        scenario_class = fakes.FakeClassBasedScenario
        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())
        runner_obj._run_scenario = mock.Mock()
        context_obj = {"task": runner_obj.task,
                       "scenario_name": "classbased.fooscenario",
                       "admin": {"credential": "foo_credentials"},
                       "config": {}}

        result = runner_obj.run("classbased.fooscenario", context_obj,
                                {"foo": 11, "bar": "spam"})

        self.assertIsNone(result)
        self.assertEqual(runner_obj.run_duration,
                         mock_timer_duration.return_value)
        self.assertEqual([], list(runner_obj.result_queue))

        runner_obj._run_scenario.assert_called_once_with(
            scenario_class, "run", context_obj, {"foo": 11, "bar": "spam"})

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
        mock_event_queue = mock.MagicMock(
            empty=mock.MagicMock(return_value=True))

        runner_obj = serial.SerialScenarioRunner(
            mock.MagicMock(),
            mock.MagicMock())

        runner_obj._join_processes(
            process_pool, mock_result_queue, mock_event_queue)

        self.assertEqual(processes, process.join.call_count)
        mock_result_queue.close.assert_called_once_with()

    def _get_runner(self, task="mock_me", config="mock_me", batch_size=0):
        class ScenarioRunner(runner.ScenarioRunner):
            def _run_scenario(self, *args, **kwargs):
                raise NotImplementedError("Do not run me!")

        task = task if task != "mock_me" else mock.Mock()
        config = config if config != "mock_me" else mock.Mock()

        scenario_runner = ScenarioRunner(task, config, batch_size)
        scenario_runner._meta_init()
        scenario_runner._meta_set("name", "FakePlugin_%s" % id(ScenarioRunner))
        return scenario_runner

    def test__send_result(self):
        task = fakes.FakeTask(uuid="foo_uuid")
        task.result_has_valid_schema = mock.MagicMock(return_value=True)
        runner_ = self._get_runner(task=task)
        result = {"timestamp": 42}
        self.assertIsNone(runner_._send_result(result))
        self.assertEqual([], runner_.result_batch)
        self.assertEqual(collections.deque([[result]]), runner_.result_queue)

    @mock.patch("rally.task.runner.LOG")
    def test__send_result_with_invalid_schema(self, mock_log):
        task = fakes.FakeTask(uuid="foo_uuid")
        task.result_has_valid_schema = mock.MagicMock(return_value=False)
        runner_ = self._get_runner(task=task)
        result = {"timestamp": 42}
        self.assertIsNone(runner_._send_result(result))
        runner_.task.result_has_valid_schema.assert_called_once_with(result)
        self.assertTrue(mock_log.warning.called)
        self.assertEqual([], runner_.result_batch)
        self.assertEqual(collections.deque([]), runner_.result_queue)
