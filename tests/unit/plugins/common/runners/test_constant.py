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

from rally.benchmark import runner
from rally import consts
from rally.plugins.common.runners import constant
from tests.unit import fakes
from tests.unit import test


RUNNERS_BASE = "rally.benchmark.runner."
RUNNERS = "rally.plugins.common.runners."


class ConstantScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ConstantScenarioRunnerTestCase, self).setUp()
        times = 4
        concurrency = 2
        timeout = 2
        max_cpu_count = 2
        type = consts.RunnerType.CONSTANT
        self.config = {"times": times, "concurrency": concurrency,
                       "timeout": timeout, "type": type,
                       "max_cpu_count": max_cpu_count}
        self.context = fakes.FakeUserContext({"task":
                                             {"uuid": "uuid"}}).context
        self.args = {"a": 1}
        self.task = mock.MagicMock()

    def test_validate(self):
        constant.ConstantScenarioRunner.validate(self.config)

    def test_validate_failed(self):
        self.config["type"] = consts.RunnerType.CONSTANT_FOR_DURATION
        self.assertRaises(jsonschema.ValidationError,
                          constant.ConstantScenarioRunner.validate,
                          self.config)

    @mock.patch(RUNNERS_BASE + "scenario_base")
    @mock.patch(RUNNERS_BASE + "osclients")
    def test_get_constant_runner(self, mock_osclients, mock_base):

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner_obj = runner.ScenarioRunner.get_runner(
            mock.MagicMock(), {"type": consts.RunnerType.CONSTANT})
        self.assertIsNotNone(runner_obj)

    @mock.patch(RUNNERS + "constant.time")
    @mock.patch(RUNNERS + "constant.threading.Thread")
    @mock.patch(RUNNERS + "constant.multiprocessing.Queue")
    @mock.patch(RUNNERS + "constant.runner")
    def test__worker_process(self, mock_base, mock_queue, mock_thread,
                             mock_time):

        mock_thread_instance = mock.MagicMock(
            isAlive=mock.MagicMock(return_value=False))
        mock_thread.return_value = mock_thread_instance

        mock_event = mock.MagicMock(
            is_set=mock.MagicMock(return_value=False))

        times = 4

        fake_ram_int = iter(range(10))

        context = {"users": [{"tenant_id": "t1", "endpoint": "e1",
                              "id": "uuid1"}]}
        info = {"processes_to_start": 1, "processes_counter": 1}

        constant._worker_process(mock_queue, fake_ram_int, 1, 2, times,
                                 context, "Dummy", "dummy", (), mock_event,
                                 info)

        self.assertEqual(times, mock_thread.call_count)
        self.assertEqual(times, mock_thread_instance.start.call_count)
        self.assertEqual(times, mock_thread_instance.join.call_count)
        self.assertEqual(times, mock_base._get_scenario_context.call_count)

        for i in range(times):
            scenario_context = mock_base._get_scenario_context(context)
            call = mock.call(args=(mock_queue,
                                   (i, "Dummy", "dummy",
                                    scenario_context, ())),
                             target=mock_base._worker_thread)
            self.assertIn(call, mock_thread.mock_calls)

    @mock.patch(RUNNERS_BASE + "_run_scenario_once")
    def test__worker_thread(self, mock_run_scenario_once):
        mock_queue = mock.MagicMock()

        args = ("some_args",)

        runner._worker_thread(mock_queue, args)

        self.assertEqual(1, mock_queue.put.call_count)

        expected_calls = [mock.call(("some_args",))]
        self.assertEqual(expected_calls, mock_run_scenario_once.mock_calls)

    def test__run_scenario(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)

        runner_obj._run_scenario(
            fakes.FakeScenario, "do_it", self.context, self.args)
        self.assertEqual(len(runner_obj.result_queue), self.config["times"])
        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))

    def test__run_scenario_exception(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "something_went_wrong",
                                 self.context, self.args)
        self.assertEqual(len(runner_obj.result_queue), self.config["times"])
        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))
        self.assertIn("error", runner_obj.result_queue[0])

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
    def test_that_cpu_count_is_adjusted_properly(self, mock_join_processes,
                                                 mock_create_pool, mock_log,
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
            mock_log.reset_mock()
            mock_cpu_count.reset_mock()
            mock_create_pool.reset_mock()
            mock_join_processes.reset_mock()
            mock_queue.reset_mock()

            mock_cpu_count.return_value = sample["real_cpu"]

            runner_obj = constant.ConstantScenarioRunner(self.task,
                                                         sample["input"])

            runner_obj._run_scenario(fakes.FakeScenario, "do_it", self.context,
                                     self.args)

            mock_cpu_count.assert_called_once_with()
            mock_log.assert_called_once_with(
                times=sample["input"]["times"],
                concurrency=sample["input"]["concurrency"],
                timeout=0,
                max_cpu_used=sample["expected"]["max_cpu_used"],
                processes_to_start=sample["expected"]["processes_to_start"],
                concurrency_per_worker=(
                    sample["expected"]["concurrency_per_worker"]),
                concurrency_overhead=(
                    sample["expected"]["concurrency_overhead"]))
            args, kwargs = mock_create_pool.call_args
            self.assertIn(sample["expected"]["processes_to_start"], args)
            self.assertIn(constant._worker_process, args)
            mock_join_processes.assert_called_once_with(
                mock_create_pool(),
                mock_queue())

    def test_abort(self):
        runner_obj = constant.ConstantScenarioRunner(self.task, self.config)
        self.assertFalse(runner_obj.aborted.is_set())
        runner_obj.abort()
        self.assertTrue(runner_obj.aborted.is_set())


class ConstantForDurationScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ConstantForDurationScenarioRunnerTestCase, self).setUp()
        duration = 0
        concurrency = 2
        timeout = 2
        type = consts.RunnerType.CONSTANT_FOR_DURATION
        self.config = {"duration": duration, "concurrency": concurrency,
                       "timeout": timeout, "type": type}
        self.context = fakes.FakeUserContext({"task":
                                             {"uuid": "uuid"}}).context
        self.args = {"a": 1}

    def test_validate(self):
        constant.ConstantForDurationScenarioRunner.validate(self.config)

    def test_validate_failed(self):
        self.config["type"] = consts.RunnerType.CONSTANT
        self.assertRaises(jsonschema.ValidationError, constant.
                          ConstantForDurationScenarioRunner.validate,
                          self.config)

    def test_run_scenario_constantly_for_duration(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "do_it",
                                 self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner_obj.result_queue), expected_times)
        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))

    def test_run_scenario_constantly_for_duration_exception(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "something_went_wrong",
                                 self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner_obj.result_queue), expected_times)
        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))
        self.assertIn("error", runner_obj.result_queue[0])

    def test_run_scenario_constantly_for_duration_timeout(self):
        runner_obj = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner_obj._run_scenario(fakes.FakeScenario, "raise_timeout",
                                 self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner_obj.result_queue), expected_times)
        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))
        self.assertIn("error", runner_obj.result_queue[0])

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
