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

import ddt
import jsonschema
import mock

from rally import exceptions
from rally.plugins.common.runners import rps
from rally.task import runner
from tests.unit import fakes
from tests.unit import test


RUNNERS_BASE = "rally.task.runner."
RUNNERS = "rally.plugins.common.runners."


@ddt.ddt
class RPSScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(RPSScenarioRunnerTestCase, self).setUp()
        self.task = mock.MagicMock()

    @ddt.data(
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 3,
                    "step": 1,
                },
                "times": 6
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 10,
                    "step": 1,
                },
                "times": 55
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 2,
                    "step": 1,
                },
                "times": 1
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 2,
                    "end": 1,
                    "step": 1,
                },
                "times": 2
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 2,
                    "end": 1,
                    "step": 3,
                },
                "times": 2
            }
        },
        {
            "config": {
                "type": "rps",
                "times": 1,
                "rps": 100,
                "max_concurrency": 50,
                "max_cpu_count": 8,
                "timeout": 1
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": 0.000001
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 10,
                    "step": 1,
                },
                "times": 55
            }
        },
    )
    @ddt.unpack
    def test_validate(self, config):
        if "times" not in config:
            self.assertRaises(
                jsonschema.exceptions.ValidationError,
                rps.RPSScenarioRunner.validate, config)
        elif config["times"] == 2:
            self.assertRaises(
                exceptions.InvalidTaskException,
                rps.RPSScenarioRunner.validate, config)
        else:
            rps.RPSScenarioRunner.validate(config)

    def test_rps_parameter_validate_failed(self):
        config = {
            "type": "rps",
            "rps": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          rps.RPSScenarioRunner.validate, config)

    def test_validate_failed(self):
        config = {"type": "rps", "a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          rps.RPSScenarioRunner.validate, config)

    @mock.patch(RUNNERS + "rps.LOG")
    @mock.patch(RUNNERS + "rps.time")
    @mock.patch(RUNNERS + "rps.threading.Thread")
    @mock.patch(RUNNERS + "rps.multiprocessing.Queue")
    @mock.patch(RUNNERS + "rps.runner")
    def test__worker_process(self, mock_runner, mock_queue, mock_thread,
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

        mock_event_queue = mock.MagicMock()

        times = 4
        max_concurrent = 3

        fake_ram_int = iter(range(10))

        context = {"users": [{"tenant_id": "t1", "credential": "c1",
                              "id": "uuid1"}]}
        info = {"processes_to_start": 1, "processes_counter": 1}
        mock_runs_per_second = mock.MagicMock(return_value=10)

        rps._worker_process(mock_queue, fake_ram_int, 1, times,
                            max_concurrent, context, "Dummy", "dummy",
                            (), mock_event_queue, mock_event,
                            mock_runs_per_second, 10, 1,
                            info)

        self.assertEqual(times, mock_log.debug.call_count)
        self.assertEqual(times + 1, mock_thread.call_count)
        self.assertEqual(times + 1, mock_thread_instance.start.call_count)
        self.assertEqual(times + 1, mock_thread_instance.join.call_count)
        # NOTE(rvasilets): `times` + 1 here because `times` the number of
        # scenario repetition and one more need on "initialization" stage
        # of the thread stuff.

        self.assertEqual(1, mock_time.sleep.call_count)
        self.assertEqual(2, mock_thread_instance.isAlive.call_count)
        self.assertEqual(times * 4 - 1, mock_time.time.count)

        self.assertEqual(times, mock_runner._get_scenario_context.call_count)

        for i in range(times):
            scenario_context = mock_runner._get_scenario_context(i, context)
            call = mock.call(
                args=(mock_queue, "Dummy", "dummy", scenario_context, (),
                      mock_event_queue),
                target=mock_runner._worker_thread,
            )
            self.assertIn(call, mock_thread.mock_calls)

    @mock.patch(RUNNERS + "rps.runner._run_scenario_once")
    def test__worker_thread(self, mock__run_scenario_once):
        mock_queue = mock.MagicMock()
        mock_event_queue = mock.MagicMock()
        args = ("fake_cls", "fake_method_name", "fake_context_obj", {},
                mock_event_queue)

        runner._worker_thread(mock_queue, *args)

        self.assertEqual(1, mock_queue.put.call_count)

        expected_calls = [mock.call(*args)]
        self.assertEqual(expected_calls, mock__run_scenario_once.mock_calls)

    @ddt.data(
        {
            "config": {
                "times": 20,
                "rps": 20,
                "timeout": 5,
                "max_concurrency": 15
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 10,
                    "step": 1,
                },
                "times": 55
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 10,
                    "step": 1,
                },
                "times": 50
            }
        },
        {
            "config": {
                "type": "rps",
                "rps": {
                    "start": 1,
                    "end": 10,
                    "step": 1,
                },
                "times": 75
            }
        },
    )
    @ddt.unpack
    @mock.patch(RUNNERS + "rps.time.sleep")
    def test__run_scenario(self, mock_sleep, config):
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        runner_obj._run_scenario(fakes.FakeScenario, "do_it",
                                 fakes.FakeContext({}).context, {})

        self.assertEqual(config["times"], len(runner_obj.result_queue))

        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)

    @mock.patch(RUNNERS + "rps.time.sleep")
    def test__run_scenario_exception(self, mock_sleep):
        config = {"times": 4, "rps": 10}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        runner_obj._run_scenario(fakes.FakeScenario, "something_went_wrong",
                                 fakes.FakeContext({}).context, {})
        self.assertEqual(len(runner_obj.result_queue), config["times"])
        for result_batch in runner_obj.result_queue:
            for result in result_batch:
                self.assertIsNotNone(result)

    @mock.patch(RUNNERS + "rps.time.sleep")
    def test__run_scenario_aborted(self, mock_sleep):
        config = {"times": 20, "rps": 20, "timeout": 5}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        runner_obj.abort()
        runner_obj._run_scenario(fakes.FakeScenario, "do_it",
                                 fakes.FakeUser().context, {})

        self.assertEqual(len(runner_obj.result_queue), 0)

        for result in runner_obj.result_queue:
            self.assertIsNotNone(result)

    @mock.patch(RUNNERS + "constant.multiprocessing.Queue")
    @mock.patch(RUNNERS + "rps.multiprocessing.cpu_count")
    @mock.patch(RUNNERS + "rps.RPSScenarioRunner._log_debug_info")
    @mock.patch(RUNNERS +
                "rps.RPSScenarioRunner._create_process_pool")
    @mock.patch(RUNNERS + "rps.RPSScenarioRunner._join_processes")
    def test_that_cpu_count_is_adjusted_properly(
            self, mock__join_processes, mock__create_process_pool,
            mock__log_debug_info, mock_cpu_count, mock_queue):

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
            mock__log_debug_info.reset_mock()
            mock_cpu_count.reset_mock()
            mock__create_process_pool.reset_mock()
            mock__join_processes.reset_mock()
            mock_queue.reset_mock()

            mock_cpu_count.return_value = sample["real_cpu"]

            runner_obj = rps.RPSScenarioRunner(self.task, sample["input"])

            runner_obj._run_scenario(fakes.FakeScenario, "do_it",
                                     fakes.FakeUser().context, {})

            mock_cpu_count.assert_called_once_with()
            mock__log_debug_info.assert_called_once_with(
                times=sample["input"]["times"],
                timeout=0,
                max_cpu_used=sample["expected"]["max_cpu_used"],
                processes_to_start=sample["expected"]["processes_to_start"],
                times_per_worker=sample["expected"]["times_per_worker"],
                times_overhead=sample["expected"]["times_overhead"],
                concurrency_per_worker=(
                    sample["expected"]["concurrency_per_worker"]),
                concurrency_overhead=(
                    sample["expected"]["concurrency_overhead"]))
            args, kwargs = mock__create_process_pool.call_args
            self.assertIn(sample["expected"]["processes_to_start"], args)
            self.assertIn(rps._worker_process, args)
            mock__join_processes.assert_called_once_with(
                mock__create_process_pool.return_value,
                mock_queue.return_value, mock_queue.return_value)

    def test_abort(self):
        config = {"times": 4, "rps": 10}
        runner_obj = rps.RPSScenarioRunner(self.task, config)

        self.assertFalse(runner_obj.aborted.is_set())
        runner_obj.abort()
        self.assertTrue(runner_obj.aborted.is_set())
