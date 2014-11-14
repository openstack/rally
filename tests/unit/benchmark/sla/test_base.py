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

from rally.benchmark.sla import base
from tests.unit import test


class TestCriterion(base.SLA):
    OPTION_NAME = "test_criterion"
    CONFIG_SCHEMA = {"type": "integer"}

    @staticmethod
    def check(criterion_value, result):
        return base.SLAResult(criterion_value == result,
                              msg='detail')


class BaseSLATestCase(test.TestCase):

    def test_get_by_name(self):
        self.assertEqual(base.FailureRate, base.SLA.get_by_name("FailureRate"))

    def test_get_by_name_by_config_option(self):
        self.assertEqual(base.FailureRate,
                         base.SLA.get_by_name("failure_rate"))

    def test_validate(self):
        cnf = {"test_criterion": 42}
        base.SLA.validate(cnf)

    def test_validate_invalid_name(self):
        self.assertRaises(jsonschema.ValidationError,
                          base.SLA.validate, {"nonexistent": 42})

    def test_validate_invalid_type(self):
        self.assertRaises(jsonschema.ValidationError,
                          base.SLA.validate, {"test_criterion": 42.0})

    def test_check_all(self):
        config = {
            "sla": {"test_criterion": 42},
        }
        result = {"key": {"kw": config, "name": "fake", "pos": 0},
                  "data": 42}
        results = list(base.SLA.check_all(config, result["data"]))
        expected = [{'criterion': 'test_criterion',
                     'detail': 'detail',
                     'success': True}]
        self.assertEqual(expected, results)
        result["data"] = 43
        results = list(base.SLA.check_all(config, result["data"]))
        expected = [{'criterion': 'test_criterion',
                     'detail': 'detail',
                     'success': False}]
        self.assertEqual(expected, results)


class FailureRateDeprecatedTestCase(test.TestCase):
    def test_check(self):
        result = [
                {"error": ["error"]},
                {"error": []},
        ]  # one error and one success. 50% success rate
        # 50% < 75.0%
        self.assertTrue(base.FailureRateDeprecated.check(75.0, result).success)
        # 50% > 25%
        self.assertFalse(base.FailureRateDeprecated.check(25, result).success)

    def test_check_with_no_results(self):
        result = []
        self.assertFalse(base.FailureRateDeprecated.check(10, result).success)


class FailureRateTestCase(test.TestCase):

    def test_config_schema(self):
        self.assertRaises(jsonschema.ValidationError,
                          base.IterationTime.validate,
                          {"failure_rate": {"min": -1}})
        self.assertRaises(jsonschema.ValidationError,
                          base.IterationTime.validate,
                          {"failure_rate": {"min": 100.1}})
        self.assertRaises(jsonschema.ValidationError,
                          base.IterationTime.validate,
                          {"failure_rate": {"max": -0.1}})
        self.assertRaises(jsonschema.ValidationError,
                          base.IterationTime.validate,
                          {"failure_rate": {"max": 101}})

    def test_check_min(self):
        result = [{"error": ["error"]}, {"error": []}, {"error": ["error"]},
                  {"error": ["error"]}, ]  # 75% failure rate
        self.assertFalse(base.FailureRate.check({"min": 80}, result).success)
        self.assertTrue(base.FailureRate.check({"min": 60.5}, result).success)

    def test_check_max(self):
        result = [{"error": ["error"]}, {"error": []}]  # 50% failure rate
        self.assertFalse(base.FailureRate.check({"max": 25}, result).success)
        self.assertTrue(base.FailureRate.check({"max": 75.0}, result).success)

    def test_check_min_max(self):
        result = [{"error": ["error"]}, {"error": []}, {"error": []},
                  {"error": []}]  # 25% failure rate
        self.assertFalse(base.FailureRate.check({"min": 50, "max": 90}, result)
                         .success)
        self.assertFalse(base.FailureRate.check({"min": 5, "max": 20}, result)
                         .success)
        self.assertTrue(base.FailureRate.check({"min": 24.9, "max": 25.1},
                                               result).success)

    def test_check_empty_result(self):
        result = []
        self.assertFalse(base.FailureRate.check({"max": 10.0}, result).success)


class IterationTimeTestCase(test.TestCase):
    def test_config_schema(self):
        properties = {
            "max_seconds_per_iteration": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          base.IterationTime.validate, properties)

    def test_check(self):
        result = [
                {"duration": 3.14},
                {"duration": 6.28},
        ]
        self.assertTrue(base.IterationTime.check(42, result).success)
        self.assertFalse(base.IterationTime.check(3.62, result).success)


class MaxAverageDurationTestCase(test.TestCase):
    def test_config_schema(self):
        properties = {
            "max_avg_duration": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          base.MaxAverageDuration.validate, properties)

    def test_check(self):
        result = [
                {"duration": 3.14},
                {"duration": 6.28},
        ]
        self.assertTrue(base.MaxAverageDuration.check(42, result).success)
        self.assertFalse(base.MaxAverageDuration.check(3.62, result).success)
