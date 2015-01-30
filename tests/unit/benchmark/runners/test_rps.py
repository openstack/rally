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
from rally.benchmark.runners import rps
from rally import consts
from tests.unit import fakes
from tests.unit import test


class RPSScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(RPSScenarioRunnerTestCase, self).setUp()

    def test_validate(self):
        config = {
            "type": consts.RunnerType.RPS,
            "times": 1,
            "rps": 100,
            "timeout": 1
        }
        rps.RPSScenarioRunner.validate(config)

    def test_validate_failed(self):
        config = {"type": consts.RunnerType.RPS,
                  "a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          rps.RPSScenarioRunner.validate, config)

    @mock.patch("rally.benchmark.runners.base.scenario_base")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_get_rps_runner(self, mock_osclients, mock_base):

        mock_osclients.Clients.return_value = fakes.FakeClients()

        runner = base.ScenarioRunner.get_runner(mock.MagicMock(),
                                                {"type":
                                                 consts.RunnerType.RPS})
        self.assertIsNotNone(runner)

    @mock.patch("rally.benchmark.runners.rps.LOG")
    @mock.patch("rally.benchmark.runners.rps.time")
    @mock.patch("rally.benchmark.runners.rps.threading.Thread")
    @mock.patch("rally.benchmark.runners.rps.multiprocessing.Queue")
    @mock.patch("rally.benchmark.runners.rps.base")
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

        context = {"users": [{"tenant_id": "t1", "endpoint": "e1",
                              "id": "uuid1"}]}

        rps._worker_process(10, times, mock_queue, context, 600, 1, 1,
                            "Dummy", "dummy", (), mock_event)

        self.assertEqual(times, mock_log.debug.call_count)
        self.assertEqual(times, mock_thread.call_count)

        self.assertEqual(times, mock_thread_instance.start.call_count)
        self.assertEqual(times, mock_thread_instance.join.call_count)
        self.assertEqual(times - 1, mock_time.sleep.call_count)
        self.assertEqual(times, mock_thread_instance.isAlive.call_count)
        self.assertEqual(times * 4 - 1, mock_time.time.count)
        self.assertEqual(times, mock_base._get_scenario_context.call_count)

        for i in range(1, times + 1):
            scenario_context = mock_base._get_scenario_context(context)
            call = mock.call(args=(mock_queue,
                                   (i, "Dummy", "dummy",
                                    scenario_context, ())),
                             target=rps._worker_thread)
            self.assertIn(call, mock_thread.mock_calls)

    @mock.patch("rally.benchmark.runners.rps.base",
                _run_scenario_once=mock.MagicMock())
    def test__worker_thread(self, mock_base):
        mock_queue = mock.MagicMock()

        args = ("some_args",)

        rps._worker_thread(mock_queue, args)

        self.assertEqual(1, mock_queue.put.call_count)

        expected_calls = [mock.call(("some_args",))]
        self.assertEqual(expected_calls,
                         mock_base._run_scenario_once.mock_calls)

    @mock.patch("rally.benchmark.runners.rps.time.sleep")
    def test__run_scenario(self, mock_sleep):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 20, "rps": 20, "timeout": 5}
        runner = rps.RPSScenarioRunner(None, config)

        runner._run_scenario(fakes.FakeScenario, "do_it", context, {})

        self.assertEqual(len(runner.result_queue), config["times"])

        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    @mock.patch("rally.benchmark.runners.rps.time.sleep")
    def test__run_scenario_exception(self, mock_sleep):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 4, "rps": 10}
        runner = rps.RPSScenarioRunner(None, config)

        runner._run_scenario(fakes.FakeScenario,
                             "something_went_wrong", context, {})
        self.assertEqual(len(runner.result_queue), config["times"])
        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    @mock.patch("rally.benchmark.runners.rps.time.sleep")
    def test__run_scenario_aborted(self, mock_sleep):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 20, "rps": 20, "timeout": 5}
        runner = rps.RPSScenarioRunner(None, config)

        runner.abort()
        runner._run_scenario(fakes.FakeScenario, "do_it", context, {})

        self.assertEqual(len(runner.result_queue), 0)

        for result in runner.result_queue:
            self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_abort(self):
        context = fakes.FakeUserContext({}).context
        context["task"] = {"uuid": "fake_uuid"}

        config = {"times": 4, "rps": 10}
        runner = rps.RPSScenarioRunner(None, config)

        self.assertFalse(runner.aborted.is_set())
        runner.abort()
        self.assertTrue(runner.aborted.is_set())
