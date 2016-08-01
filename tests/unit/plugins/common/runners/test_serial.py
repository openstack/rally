# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

import mock

from rally.plugins.common.runners import serial
from tests.unit import fakes
from tests.unit import test


class SerialScenarioRunnerTestCase(test.TestCase):

    @mock.patch("rally.task.runner._run_scenario_once")
    def test__run_scenario(self, mock__run_scenario_once):
        times = 5
        result = {"duration": 10., "idle_duration": 0., "error": [],
                  "output": {"additive": [], "complete": []},
                  "atomic_actions": {},
                  "timestamp": 1.}
        mock__run_scenario_once.return_value = result
        expected_results = [[result] for i in range(times)]
        runner = serial.SerialScenarioRunner(mock.MagicMock(),
                                             {"times": times})

        runner._run_scenario(fakes.FakeScenario, "do_it",
                             fakes.FakeContext().context, {})

        self.assertEqual(len(runner.result_queue), times)
        results = list(runner.result_queue)
        self.assertEqual(results, expected_results)
        expected_calls = []
        for i in range(times):
            ctxt = fakes.FakeContext().context
            ctxt["iteration"] = i + 1
            ctxt["task"] = mock.ANY
            expected_calls.append(
                mock.call(fakes.FakeScenario, "do_it", ctxt, {})
            )
        mock__run_scenario_once.assert_has_calls(expected_calls)

    def test__run_scenario_aborted(self):
        runner = serial.SerialScenarioRunner(mock.MagicMock(),
                                             {"times": 5})
        runner.abort()
        runner._run_scenario(fakes.FakeScenario, "do_it",
                             fakes.FakeContext().context, {})
        self.assertEqual(len(runner.result_queue), 0)

    def test_abort(self):
        runner = serial.SerialScenarioRunner(mock.MagicMock(),
                                             {"times": 5})
        self.assertFalse(runner.aborted.is_set())
        runner.abort()
        self.assertTrue(runner.aborted.is_set())
