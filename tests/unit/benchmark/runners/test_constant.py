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
from rally.benchmark.runners import constant
from rally import consts
from tests.unit import fakes
from tests.unit import test


RUNNERS = "rally.benchmark.runners."


class ConstantScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ConstantScenarioRunnerTestCase, self).setUp()
        times = 4
        concurrency = 2
        timeout = 2
        type = consts.RunnerType.CONSTANT
        self.config = {"times": times, "concurrency": concurrency,
                       "timeout": timeout, "type": type}
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

    @mock.patch(RUNNERS + "base.scenario_base")
    @mock.patch(RUNNERS + "base.osclients")
    def test_get_constant_runner(self, mock_osclients, mock_base):

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner = base.ScenarioRunner.get_runner(mock.MagicMock(),
                                                {"type":
                                                 consts.RunnerType.CONSTANT})
        self.assertIsNotNone(runner)

    @mock.patch(RUNNERS + "constant.time")
    @mock.patch(RUNNERS + "constant.threading.Thread")
    @mock.patch(RUNNERS + "constant.multiprocessing.Queue")
    @mock.patch(RUNNERS + "constant.base")
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

        constant._worker_process(mock_queue, fake_ram_int, 1, 2, times,
                                 context, "Dummy", "dummy", (), mock_event)

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

    @mock.patch(RUNNERS + "constant.base._run_scenario_once")
    def test__worker_thread(self, mock_run_scenario_once):
        mock_queue = mock.MagicMock()

        args = ("some_args",)

        base._worker_thread(mock_queue, args)

        self.assertEqual(1, mock_queue.put.call_count)

        expected_calls = [mock.call(("some_args",))]
        self.assertEqual(expected_calls, mock_run_scenario_once.mock_calls)

    def test__run_scenario(self):
        runner = constant.ConstantScenarioRunner(self.task, self.config)

        runner._run_scenario(fakes.FakeScenario,
                             "do_it", self.context, self.args)
        self.assertEqual(len(runner.result_queue), self.config["times"])
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test__run_scenario_exception(self):
        runner = constant.ConstantScenarioRunner(self.task, self.config)

        runner._run_scenario(fakes.FakeScenario,
                             "something_went_wrong", self.context, self.args)
        self.assertEqual(len(runner.result_queue), self.config["times"])
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn("error", runner.result_queue[0])

    def test__run_scenario_aborted(self):
        runner = constant.ConstantScenarioRunner(self.task, self.config)

        runner.abort()
        runner._run_scenario(fakes.FakeScenario,
                             "do_it", self.context, self.args)
        self.assertEqual(len(runner.result_queue), 0)

    def test_abort(self):
        runner = constant.ConstantScenarioRunner(self.task, self.config)
        self.assertFalse(runner.aborted.is_set())
        runner.abort()
        self.assertTrue(runner.aborted.is_set())


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
        runner = constant.ConstantForDurationScenarioRunner(
                        None, self.config)

        runner._run_scenario(fakes.FakeScenario, "do_it",
                             self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner.result_queue), expected_times)
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_run_scenario_constantly_for_duration_exception(self):
        runner = constant.ConstantForDurationScenarioRunner(
                        None, self.config)

        runner._run_scenario(fakes.FakeScenario,
                             "something_went_wrong", self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner.result_queue), expected_times)
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn("error", runner.result_queue[0])

    def test_run_scenario_constantly_for_duration_timeout(self):
        runner = constant.ConstantForDurationScenarioRunner(
            None, self.config)

        runner._run_scenario(fakes.FakeScenario,
                             "raise_timeout", self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(runner.result_queue), expected_times)
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn("error", runner.result_queue[0])

    def test__run_scenario_constantly_aborted(self):
        runner = constant.ConstantForDurationScenarioRunner(None, self.config)

        runner.abort()
        runner._run_scenario(fakes.FakeScenario,
                             "do_it", self.context, self.args)
        self.assertEqual(len(runner.result_queue), 0)

    def test_abort(self):
        runner = constant.ConstantForDurationScenarioRunner(None, self.config)
        self.assertFalse(runner.aborted.is_set())
        runner.abort()
        self.assertTrue(runner.aborted.is_set())
