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
from rally.benchmark.runners import continuous
from tests import fakes
from tests import test


class ContinuousScenarioRunnerTestCase(test.TestCase):

    def test_validate(self):
        config = {
            "type": "continuous",
            "active_users": 1,
            "times": 1,
            "duration": 1.0,
            "timeout": 1
        }
        continuous.ContinuousScenarioRunner.validate(config)

    def test_validate_failed(self):
        config = {"type": "continuous", "a": 10}
        self.assertRaises(jsonschema.ValidationError,
                          continuous.ContinuousScenarioRunner.validate, config)

    def test_run_scenario_continuously_for_times(self):
        context = fakes.FakeUserContext({"task": None}).context
        runner = continuous.ContinuousScenarioRunner(
                        None, [context["admin"]["endpoint"]])
        times = 4
        concurrent = 2
        timeout = 2

        result = runner._run_scenario_continuously_for_times(
                            fakes.FakeScenario, "do_it", context, {},
                            times, concurrent, timeout)
        self.assertEqual(len(result), times)
        self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_run_scenario_continuously_for_times_exception(self):
        context = fakes.FakeUserContext({"task": None}).context
        runner = continuous.ContinuousScenarioRunner(
                        None, [context["admin"]["endpoint"]])
        times = 4
        concurrent = 2
        timeout = 2

        result = runner._run_scenario_continuously_for_times(
                            fakes.FakeScenario, "something_went_wrong",
                            context, {}, times, concurrent, timeout)
        self.assertEqual(len(result), times)
        self.assertIsNotNone(base.ScenarioRunnerResult(result))

    @mock.patch("rally.benchmark.runners.continuous.base._run_scenario_once")
    def test_run_scenario_continuously_for_duration(self, mock_run_once):
        self.skipTest("This test produce a lot of races so we should fix it "
                      "before running inside in gates")
        runner = continuous.ContinuousScenarioRunner(mock.MagicMock(),
                                                     [mock.MagicMock()])
        duration = 0
        active_users = 4
        timeout = 5
        runner._run_scenario_continuously_for_duration(fakes.FakeScenario,
                                                       "do_it", {}, duration,
                                                       active_users, timeout)
