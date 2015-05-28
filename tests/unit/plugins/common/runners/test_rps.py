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
from rally.plugins.common.runners import rps
from tests.unit import fakes
from tests.unit import test


RUNNERS_BASE = "rally.benchmark.runner."
RUNNERS = "rally.plugins.common.runners."


class RPSScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(RPSScenarioRunnerTestCase, self).setUp()
        self.task = mock.MagicMock()

    def test_validate(self):
        config = {
            "type": consts.RunnerType.RPS,
            "times": 1,
            "rps": 100,
            "max_concurrency": 50,
            "max_cpu_count": 8,
            "timeout": 1
        }
        rps.RPSScenarioRunner.validate(config)

    def test_rps_parameter_validate(self):
        config = {
            "type": consts.RunnerType.RPS,
            "rps": 0.0000001
        }
        rps.RPSScenarioRunner.validate(config)

    def test_rps_parameter_validate_failed(self):
        config = {
            "type": consts.RunnerType.RPS,
            "rps": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          rps.RPSScenarioRunner.validate, config)

    def test_validate_failed(self):
        config = {"type": consts.RunnerType.RPS,
                  "a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          rps.RPSScenarioRunner.validate, config)

    @mock.patch(RUNNERS_BASE + "scenario_base")
    @mock.patch(RUNNERS_BASE + "osclients")
    def test_get_rps_runner(self, mock_osclients, mock_base):

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner_obj = runner.ScenarioRunner.get_runner(
            mock.MagicMock(), {"type": consts.RunnerType.RPS})
        self.assertIsNotNone(runner_obj)

    @mock.patch(RUNNERS + "rps.LOG")
    @mock.patch(RUNNERS + "rps.time")
    @mock.patch(RUNNERS + "rps.threading.Thread")
    @mock.patch(RUNNERS + "rps.multiprocessing.Queue")
    @mock.patch(RUNNERS + "rps.runner")
    def test__worker_process(self, mock_base, mock_queue, mock_thread,
                             mock_time, mock_log):

        def time_side():
            time_side.last += 0.03
            time_side.count += 1
            return time_side.last
        time_side.last = 0
        time_side.count = 0

        mock_time.time = time_side

        mock_thread_instance = mock.MagicMock(
            isAlive=mock.MagicMock(return_value=False))
        mock_thread.return_value = mock_thread_instance

        mock_event = mock.MagicMock(
            is_set=mock.MagicMock(return_value=False))

        times = 4
        max_concurrent = 3

        fake_ram_int = iter(range(10))

        context = {"users": [{"tenant_id": "t1", "endpoint": "e1",
                              "id": "uuid1"}]}
        info = {"processes_to_start": 1, "processes_counter": 1}

        rps._worker_process(mock_queue, fake_ram_int, 1, 10, times,
                            max_concurrent, context, "Dummy", "dummy",
                            (), mock_event, info)

        self.assertEqual(times, mock_log.debug.call_count)
        self.assertEqual(times, mock_thread.call_count)
        self.assertEqual(times, mock_thread_instance.start.call_count)
        self.assertEqual(times, mock_thread_instance.join.call_count)
        self.assertEqual(times - 1, mock_time.sleep.call_count)
        self.assertEqual(times, mock_thread_instance.isAlive.call_count)
        self.assertEqual(times * 4 - 1, mock_time.time.count)
        self.assertEqual(times, mock_base._get_scenario_context.call_count)

        for i in range(times):
            scenario_context = mock_base._get_scenario_context(context)
            call = mock.call(args=(mock_queue,
                                   (i, "Dummy", "dummy",
                                    scenario_context, ())),
                             target=mock_base._worker_thread)
            self.assertIn(call, mock_thread.mock_calls)

    @mock.patch(RUNNERS + "rps.runner._run_scenario_once")
    def test__worker_thread(self, mock_run_scenario_once):
        mock_queue = mock.MagicMock()

        args = ("some_args",)

        runner._worker_thread(mock_queue, args)

        self.assertEqual(1, mock_queue.put.call_count)

        expected_calls = [mock.call(("some_args",))]
        self.assertEqual(expected_calls, mock_run_scenario_once.mock_calls)

    @mock.patch(RUNNERS + "rps.time.sleep")
    def test__run_scenario(self, mock_sleep):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 20, "rps": 20, "timeout": 5, "max_concurrency": 15}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        runner_obj._run_scenario(fakes.FakeScenario, "do_it", context, {})

        self.assertEqual(len(runner_obj.result_queue), config["times"])

        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))

    @mock.patch(RUNNERS + "rps.time.sleep")
    def test__run_scenario_exception(self, mock_sleep):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 4, "rps": 10}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        runner_obj._run_scenario(fakes.FakeScenario, "something_went_wrong",
                                 context, {})
        self.assertEqual(len(runner_obj.result_queue), config["times"])
        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))

    @mock.patch(RUNNERS + "rps.time.sleep")
    def test__run_scenario_aborted(self, mock_sleep):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 20, "rps": 20, "timeout": 5}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        runner_obj.abort()
        runner_obj._run_scenario(fakes.FakeScenario, "do_it", context, {})

        self.assertEqual(len(runner_obj.result_queue), 0)

        for result in runner_obj.result_queue:
            self.assertIsNotNone(runner.ScenarioRunnerResult(result))

    @mock.patch(RUNNERS + "constant.multiprocessing.Queue")
    @mock.patch(RUNNERS + "rps.multiprocessing.cpu_count")
    @mock.patch(RUNNERS + "rps.RPSScenarioRunner._log_debug_info")
    @mock.patch(RUNNERS +
                "rps.RPSScenarioRunner._create_process_pool")
    @mock.patch(RUNNERS + "rps.RPSScenarioRunner._join_processes")
    def test_that_cpu_count_is_adjusted_properly(self, mock_join_processes,
                                                 mock_create_pool, mock_log,
                                                 mock_cpu_count, mock_queue):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        samples = [
            {
                "input": {"times": 20, "rps": 20, "max_concurrency": 10,
                          "max_cpu_count": 1},
                "real_cpu": 2,
                "expected": {
                    # max_cpu_used equals to min(max_cpu_count, real_cpu)
                    "max_cpu_used": 1,
                    # processes_to_start equals to
                    # min(max_cpu_used, times, max_concurrency))
                    "processes_to_start": 1,
                    "rps_per_worker": 20,
                    "times_per_worker": 20,
                    "times_overhead": 0,
                    "concurrency_per_worker": 10,
                    "concurrency_overhead": 0
                }
            },
            {
                "input": {"times": 20, "rps": 9, "max_concurrency": 5,
                          "max_cpu_count": 3},
                "real_cpu": 4,
                "expected": {
                    "max_cpu_used": 3,
                    "processes_to_start": 3,
                    "rps_per_worker": 3,
                    "times_per_worker": 6,
                    "times_overhead": 2,
                    "concurrency_per_worker": 1,
                    "concurrency_overhead": 2
                }
            },
            {
                "input": {"times": 10, "rps": 20, "max_concurrency": 12,
                          "max_cpu_count": 20},
                "real_cpu": 20,
                "expected": {
                    "max_cpu_used": 20,
                    "processes_to_start": 10,
                    "rps_per_worker": 2,
                    "times_per_worker": 1,
                    "times_overhead": 0,
                    "concurrency_per_worker": 1,
                    "concurrency_overhead": 2
                }
            },
            {
                "input": {"times": 20, "rps": 20, "max_concurrency": 10,
                          "max_cpu_count": 20},
                "real_cpu": 20,
                "expected": {
                    "max_cpu_used": 20,
                    "processes_to_start": 10,
                    "rps_per_worker": 2,
                    "times_per_worker": 2,
                    "times_overhead": 0,
                    "concurrency_per_worker": 1,
                    "concurrency_overhead": 0
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

            runner_obj = rps.RPSScenarioRunner(self.task, sample["input"])

            runner_obj._run_scenario(fakes.FakeScenario, "do_it", context, {})

            mock_cpu_count.assert_called_once_with()
            mock_log.assert_called_once_with(
                times=sample["input"]["times"],
                timeout=0,
                max_cpu_used=sample["expected"]["max_cpu_used"],
                processes_to_start=sample["expected"]["processes_to_start"],
                rps_per_worker=sample["expected"]["rps_per_worker"],
                times_per_worker=sample["expected"]["times_per_worker"],
                times_overhead=sample["expected"]["times_overhead"],
                concurrency_per_worker=(
                    sample["expected"]["concurrency_per_worker"]),
                concurrency_overhead=(
                    sample["expected"]["concurrency_overhead"]))
            args, kwargs = mock_create_pool.call_args
            self.assertIn(sample["expected"]["processes_to_start"], args)
            self.assertIn(rps._worker_process, args)
            mock_join_processes.assert_called_once_with(
                mock_create_pool(),
                mock_queue())

    def test_abort(self):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 4, "rps": 10}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        self.assertFalse(runner_obj.aborted.is_set())
        runner_obj.abort()
        self.assertTrue(runner_obj.aborted.is_set())
