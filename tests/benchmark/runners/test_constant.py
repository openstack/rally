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

from rally.benchmark.runners import base
from rally.benchmark.runners import constant
from tests import fakes
from tests import test


class ConstantScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ConstantScenarioRunnerTestCase, self).setUp()
        times = 4
        concurrency = 2
        timeout = 2
        type = "constant"
        self.config = {"times": times, "concurrency": concurrency,
                       "timeout": timeout, "type": type}
        self.context = fakes.FakeUserContext({"task":
                                             {"uuid": "uuid"}}).context
        self.args = {"a": 1}

    def test_validate(self):
        constant.ConstantScenarioRunner.validate(self.config)

    def test_validate_failed(self):
        self.config["type"] = "constant_for_duration"
        self.assertRaises(jsonschema.ValidationError,
                          constant.ConstantScenarioRunner.validate,
                          self.config)

    def test_run_scenario_constantly_for_times(self):
        runner = constant.ConstantScenarioRunner(
                        None, [self.context["admin"]["endpoint"]], self.config)

        result = runner._run_scenario(fakes.FakeScenario, "do_it",
                                      self.context, self.args)
        self.assertEqual(len(result), self.config["times"])
        self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_run_scenario_constantly_for_times_exception(self):
        runner = constant.ConstantScenarioRunner(
                        None, [self.context["admin"]["endpoint"]], self.config)

        result = runner._run_scenario(fakes.FakeScenario,
                                      "something_went_wrong",
                                      self.context, self.args)
        self.assertEqual(len(result), self.config["times"])
        self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn('error', result[0])

    def test_run_scenario_constantly_for_times_timeout(self):
        runner = constant.ConstantScenarioRunner(
                        None, [self.context["admin"]["endpoint"]], self.config)

        result = runner._run_scenario(fakes.FakeScenario,
                                      "raise_timeout", self.context, self.args)
        self.assertEqual(len(result), self.config["times"])
        self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn('error', result[0])


class ConstantForDurationScenarioRunnerTeestCase(test.TestCase):

    def setUp(self):
        super(ConstantForDurationScenarioRunnerTeestCase, self).setUp()
        duration = 0
        concurrency = 2
        timeout = 2
        type = "constant_for_duration"
        self.config = {"duration": duration, "concurrency": concurrency,
                       "timeout": timeout, "type": type}
        self.context = fakes.FakeUserContext({"task":
                                             {"uuid": "uuid"}}).context
        self.args = {"a": 1}

    def test_validate(self):
        constant.ConstantForDurationScenarioRunner.validate(self.config)

    def test_validate_failed(self):
        self.config["type"] = "constant"
        self.assertRaises(jsonschema.ValidationError, constant.
                          ConstantForDurationScenarioRunner.validate,
                          self.config)

    def test_run_scenario_constantly_for_duration(self):
        runner = constant.ConstantForDurationScenarioRunner(
                        None, [self.context["admin"]["endpoint"]], self.config)

        result = runner._run_scenario(fakes.FakeScenario, "do_it",
                                      self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(result), expected_times)
        self.assertIsNotNone(base.ScenarioRunnerResult(result))

    def test_run_scenario_constantly_for_duration_exception(self):
        runner = constant.ConstantForDurationScenarioRunner(
                        None, [self.context["admin"]["endpoint"]], self.config)

        result = runner._run_scenario(fakes.FakeScenario,
                                      "something_went_wrong",
                                      self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(result), expected_times)
        self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn('error', result[0])

    def test_run_scenario_constantly_for_duration_timeout(self):
        runner = constant.ConstantForDurationScenarioRunner(
                        None, [self.context["admin"]["endpoint"]], self.config)

        result = runner._run_scenario(fakes.FakeScenario,
                                      "raise_timeout", self.context, self.args)
        # NOTE(mmorais): when duration is 0, scenario executes exactly 1 time
        expected_times = 1
        self.assertEqual(len(result), expected_times)
        self.assertIsNotNone(base.ScenarioRunnerResult(result))
        self.assertIn('error', result[0])
