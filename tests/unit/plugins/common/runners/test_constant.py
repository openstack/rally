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

from rally import exceptions
from rally.plugins.common.runners import constant
from rally.task import runner
from tests.unit import fakes
from tests.unit import test


RUNNERS_BASE = "rally.task.runner."
RUNNERS = "rally.plugins.common.runners."


class ConstantScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ConstantScenarioRunnerTestCase, self).setUp()
        self.config = {"times": 4, "concurrency": 2,
                       "timeout": 2, "type": "constant",
                       "max_cpu_count": 2}
        self.context = fakes.FakeContext({"task": {"uuid": "uuid"}}).context
        self.args = {"a": 1}
        self.task = mock.MagicMock()

    def test_validate(self):
        constant.ConstantScenarioRunner.validate(self.config)

    def test_validate_failed_by_additional_key(self):
        self.config["new_key"] = "should fail"
        self.assertRaises(jsonschema.ValidationError,
                          constant.ConstantScenarioRunner.validate,
                          self.config)

    def test_validate_failed_by_wrong_concurrency(self):
        self.config["concurrency"] = self.config["times"] + 1
        self.assertRaises(exceptions.ValidationError,
                          constant.ConstantScenarioRunner.validate,
                          self.config)

    @mock.patch(RUNNERS + "constant.runner")
    def test__run_scenario_once_with_unpack_args(self, mock_runner):
        result = constant._run_scenario_once_with_unpack_args(
            ("FOO", ("BAR", "QUUZ")))

        self.assertEqual(mock_runner._run_scenario_once.return_value, result)
        mock_runner._run_scenario_once.assert_called_once_with(
            "FOO", ("BAR", "QUUZ"))

    @mock.patch(RUNNERS + "constant.time")
    @mock.patch(RUNNERS + "constant.threading.Thread")
    @mock.patch(RUNNERS + "constant.multiprocessing.Queue")
    @mock.patch(RUNNERS + "constant.runner")
    def test__worker_process(self, mock_runner, mock_queue, mock_thread,
                             mock_time):

        mock_thread_instance = mock.MagicMock(
            isAlive=mock.MagicMock(return_value=False))
        mock_thread.return_value = mock_thread_instance

        mock_event = mock.MagicMock(
            is_set=mock.MagicMock(return_value=False))

        mock_event_queue = mock.MagicMock()

        times = 4

        fake_ram_int = iter(range(10))

        context = {"users": [{"tenant_id": "t1", "credential": "c1",
                              "id": "uuid1"}]}
        info = {"processes_to_start": 1, "processes_counter": 1}

        constant._worker_process(mock_queue, fake_ram_int, 1, 2, times,
                                 context, "Dummy", "dummy", (),
                                 mock_event_queue, mock_event, info)

        self.assertEqual(times + 1, mock_thread.call_count)
        self.assertEqual(times + 1, mock_thread_instance.start.call_count)
        self.assertEqual(times + 1, mock_thread_instance.join.call_count)
        # NOTE(rvasilets): `times` + 1 here because `times` the number of
        # scenario repetition and one more need on "initialization" stage
        # of the thread stuff.
        self.assertEqual(times, mock_runner._get_scenario_context.call_count)

        for i in range(times):
            scenario_context = mock_runner._get_scenario_context(i, context)
            call = mock.call(
                args=(mock_queue, "Dummy", "dummy", scenario_context, (),
                      mock_event_queue),
                target=mock_runner._worker_thread,
            )
            self.assertIn(call, mock_thread.mock_calls)

    @mock.patch(RUNNERS_BASE + "_run_scenario_once")
    def test__worker_thread(self, mock__run_scenario_once):
        mock_queue = mock.MagicMock()

        mock_event_queue = mock.MagicMock()

        args = ("fake_cls", "fake_method_name", "fake_context_obj", {},
                mock_event_queue)

        runner._worker_thread(mock_queue, *args)

        self.assertEqual(1, mock_queue.put.call_count)

        expected_calls = [mock.call(*args)]
        self.assertEqual(expected_calls, mock__run_scenario_once.mock_calls)

    def test__run_scenario(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)

        runner_obj._run_scenario(
            fakes.FakeScenario, "do_it", self.context, self.args)
        self.assertEqual(len(runner_obj.result_queue), self.config["times"])
        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)

    def test__run_scenario_exception(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "something_went_wrong",
                                 self.context, self.args)
        self.assertEqual(len(runner_obj.result_queue), self.config["times"])
        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)
        self.assertIn("error", runner_obj.result_queue[0][0])

    def test__run_scenario_aborted(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)

        runner_obj.abort()
        runner_obj._run_scenario(fakes.FakeScenario, "do_it", self.context,
                                 self.args)
        self.assertEqual(len(runner_obj.result_queue), 0)

    @mock.patch(RUNNERS + "constant.multiprocessing.Queue")
    @mock.patch(RUNNERS + "constant.multiprocessing.cpu_count")
    @mock.patch(RUNNERS + "constant.ConstantScenarioRunner._log_debug_info")
    @mock.patch(RUNNERS +
                "constant.ConstantScenarioRunner._create_process_pool")
    @mock.patch(RUNNERS + "constant.ConstantScenarioRunner._join_processes")
    def test_that_cpu_count_is_adjusted_properly(
            self,
            mock__join_processes,
            mock__create_process_pool,
            mock__log_debug_info,
            mock_cpu_count, mock_queue):

        samples = [
            {
                "input": {"times": 20, "concurrency": 20, "type": "constant",
                          "max_cpu_count": 1},
                "real_cpu": 2,
                "expected": {
                    # max_cpu_used equals to min(max_cpu_count, real_cpu)
                    "max_cpu_used": 1,
                    # processes_to_start equals to
                    # min(max_cpu_used, times, concurrency))
                    "processes_to_start": 1,
                    "concurrency_per_worker": 20,
                    "concurrency_overhead": 0,
                }
            },
            {
                "input": {"times": 20, "concurrency": 15, "type": "constant",
                          "max_cpu_count": 3},
                "real_cpu": 2,
                "expected": {
                    "max_cpu_used": 2,
                    "processes_to_start": 2,
                    "concurrency_per_worker": 7,
                    "concurrency_overhead": 1,
                }
            },
            {
                "input": {"times": 20, "concurrency": 1, "type": "constant",
                          "max_cpu_count": 3},
                "real_cpu": 2,
                "expected": {
                    "max_cpu_used": 2,
                    "processes_to_start": 1,
                    "concurrency_per_worker": 1,
                    "concurrency_overhead": 0,
                }
            },
            {
                "input": {"times": 2, "concurrency": 5, "type": "constant",
                          "max_cpu_count": 4},
                "real_cpu": 4,
                "expected": {
                    "max_cpu_used": 4,
                    "processes_to_start": 2,
                    "concurrency_per_worker": 2,
                    "concurrency_overhead": 1,
                }
            }
        ]

        for sample in samples:
            mock__log_debug_info.reset_mock()
            mock_cpu_count.reset_mock()
            mock__create_process_pool.reset_mock()
            mock__join_processes.reset_mock()
            mock_queue.reset_mock()

            mock_cpu_count.return_value = sample["real_cpu"]

            runner_obj = constant.ConstantScenarioRunner(self.task,
                                                         sample["input"])

            runner_obj._run_scenario(fakes.FakeScenario, "do_it", self.context,
                                     self.args)

            mock_cpu_count.assert_called_once_with()
            mock__log_debug_info.assert_called_once_with(
                times=sample["input"]["times"],
                concurrency=sample["input"]["concurrency"],
                timeout=0,
                max_cpu_used=sample["expected"]["max_cpu_used"],
                processes_to_start=sample["expected"]["processes_to_start"],
                concurrency_per_worker=(
                    sample["expected"]["concurrency_per_worker"]),
                concurrency_overhead=(
                    sample["expected"]["concurrency_overhead"]))
            args, kwargs = mock__create_process_pool.call_args
            self.assertIn(sample["expected"]["processes_to_start"], args)
            self.assertIn(constant._worker_process, args)
            mock__join_processes.assert_called_once_with(
                mock__create_process_pool.return_value,
                mock_queue.return_value, mock_queue.return_value)

    def test_abort(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)
        self.assertFalse(runner_obj.aborted.is_set())
        runner_obj.abort()
        self.assertTrue(runner_obj.aborted.is_set())


class ConstantForDurationScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ConstantForDurationScenarioRunnerTestCase, self).setUp()
        self.config = {"duration": 0, "concurrency": 2,
                       "timeout": 2, "type": "constant_for_duration"}
        self.context = fakes.FakeContext({"task": {"uuid": "uuid"}}).context
        self.context["iteration"] = 14
        self.args = {"a": 1}

    def test_validate(self):
        constant.ConstantForDurationScenarioRunner.validate(self.config)

    def test_validate_failed(self):
        self.config["times"] = "gagaga"
        self.assertRaises(jsonschema.ValidationError,
                          runner.ScenarioRunner.validate,
                          self.config)

    def test_run_scenario_constantly_for_duration(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "do_it",
                                 self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner_obj.result_queue), expected_times)
        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)

    def test_run_scenario_constantly_for_duration_exception(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "something_went_wrong",
                                 self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner_obj.result_queue), expected_times)
        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)
        self.assertIn("error", runner_obj.result_queue[0][0])

    def test_run_scenario_constantly_for_duration_timeout(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "raise_timeout",
                                 self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner_obj.result_queue), expected_times)
        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)
        self.assertIn("error", runner_obj.result_queue[0][0])

    def test__run_scenario_constantly_aborted(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(None,
                                                                self.config)

        runner_obj.abort()
        runner_obj._run_scenario(fakes.FakeScenario, "do_it",
                                 self.context, self.args)
        self.assertEqual(len(runner_obj.result_queue), 0)

    def test_abort(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(None,
                                                                self.config)
        self.assertFalse(runner_obj.aborted.is_set())
        runner_obj.abort()
        self.assertTrue(runner_obj.aborted.is_set())
