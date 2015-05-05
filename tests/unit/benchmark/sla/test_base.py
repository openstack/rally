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
    """Test SLA."""
    OPTION_NAME = "test_criterion"
    CONFIG_SCHEMA = {"type": "integer"}

    def add_iteration(self, iteration):
        self.success = self.criterion_value == iteration
        return self.success

    def details(self):
        return "detail"


class SLACheckerTestCase(test.TestCase):

    def test_add_iteration_and_results(self):
        sla_checker = base.SLAChecker({"sla": {"test_criterion": 42}})

        iteration = {"key": {"name": "fake", "pos": 0}, "data": 42}
        self.assertTrue(sla_checker.add_iteration(iteration["data"]))
        expected_result = [{"criterion": "test_criterion",
                            "detail": "detail",
                            "success": True}]
        self.assertEqual(expected_result, sla_checker.results())

        iteration["data"] = 43
        self.assertFalse(sla_checker.add_iteration(iteration["data"]))
        expected_result = [{"criterion": "test_criterion",
                            "detail": "detail",
                            "success": False}]
        self.assertEqual(expected_result, sla_checker.results())

    def test_set_unexpected_failure(self):
        exc = "error;("
        sla_checker = base.SLAChecker({"sla": {}})
        self.assertEqual([], sla_checker.results())
        sla_checker.set_unexpected_failure(exc)
        self.assertEqual([{"criterion": "something_went_wrong",
                           "success": False,
                           "detail": "Unexpected error: %s" % exc}],
                         sla_checker.results())

    def test_set_aborted(self):
        sla_checker = base.SLAChecker({"sla": {}})
        self.assertEqual([], sla_checker.results())
        sla_checker.set_aborted()
        self.assertEqual(
            [{"criterion": "aborted_on_sla", "success": False,
              "detail": "Task was aborted due to SLA failure(s)."}],
            sla_checker.results())


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

    def test__format_result(self):
        name = "some_name"
        success = True
        detail = "some details"
        self.assertEqual({"criterion": name,
                          "success": success,
                          "detail": detail},
                         base._format_result(name, success, detail))


class FailureRateDeprecatedTestCase(test.TestCase):

    def test_result(self):
        sla1 = base.FailureRateDeprecated(75.0)
        sla2 = base.FailureRateDeprecated(25.0)
        # 50% failure rate
        for sla in [sla1, sla2]:
            sla.add_iteration({"error": ["error"]})
            sla.add_iteration({"error": []})
        self.assertTrue(sla1.result()["success"])   # 50% < 75.0%
        self.assertFalse(sla2.result()["success"])  # 50% > 25.0%
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla = base.FailureRateDeprecated(10.0)
        self.assertTrue(sla.result()["success"])


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

    def test_result_min(self):
        sla1 = base.FailureRate({"min": 80.0})
        sla2 = base.FailureRate({"min": 60.5})
        # 75% failure rate
        for sla in [sla1, sla2]:
            sla.add_iteration({"error": ["error"]})
            sla.add_iteration({"error": []})
            sla.add_iteration({"error": ["error"]})
            sla.add_iteration({"error": ["error"]})
        self.assertFalse(sla1.result()["success"])  # 80.0% > 75.0%
        self.assertTrue(sla2.result()["success"])   # 60.5% < 75.0%
        self.assertEqual("Failed", sla1.status())
        self.assertEqual("Passed", sla2.status())

    def test_result_max(self):
        sla1 = base.FailureRate({"max": 25.0})
        sla2 = base.FailureRate({"max": 75.0})
        # 50% failure rate
        for sla in [sla1, sla2]:
            sla.add_iteration({"error": ["error"]})
            sla.add_iteration({"error": []})
        self.assertFalse(sla1.result()["success"])  # 25.0% < 50.0%
        self.assertTrue(sla2.result()["success"])   # 75.0% > 50.0%
        self.assertEqual("Failed", sla1.status())
        self.assertEqual("Passed", sla2.status())

    def test_result_min_max(self):
        sla1 = base.FailureRate({"min": 50, "max": 90})
        sla2 = base.FailureRate({"min": 5, "max": 20})
        sla3 = base.FailureRate({"min": 24.9, "max": 25.1})
        # 25% failure rate
        for sla in [sla1, sla2, sla3]:
            sla.add_iteration({"error": ["error"]})
            sla.add_iteration({"error": []})
            sla.add_iteration({"error": []})
            sla.add_iteration({"error": []})
        self.assertFalse(sla1.result()["success"])  # 25.0% < 50.0%
        self.assertFalse(sla2.result()["success"])  # 25.0% > 20.0%
        self.assertTrue(sla3.result()["success"])   # 24.9% < 25.0% < 25.1%
        self.assertEqual("Failed", sla1.status())
        self.assertEqual("Failed", sla2.status())
        self.assertEqual("Passed", sla3.status())

    def test_result_no_iterations(self):
        sla = base.FailureRate({"max": 10.0})
        self.assertTrue(sla.result()["success"])

    def test_add_iteration(self):
        sla = base.FailureRate({"max": 35.0})
        self.assertTrue(sla.add_iteration({"error": []}))
        self.assertTrue(sla.add_iteration({"error": []}))
        self.assertTrue(sla.add_iteration({"error": []}))
        self.assertTrue(sla.add_iteration({"error": ["error"]}))   # 33%
        self.assertFalse(sla.add_iteration({"error": ["error"]}))  # 40%


class IterationTimeTestCase(test.TestCase):
    def test_config_schema(self):
        properties = {
            "max_seconds_per_iteration": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          base.IterationTime.validate, properties)

    def test_result(self):
        sla1 = base.IterationTime(42)
        sla2 = base.IterationTime(3.62)
        for sla in [sla1, sla2]:
            sla.add_iteration({"duration": 3.14})
            sla.add_iteration({"duration": 6.28})
        self.assertTrue(sla1.result()["success"])   # 42 > 6.28
        self.assertFalse(sla2.result()["success"])  # 3.62 < 6.28
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla = base.IterationTime(42)
        self.assertTrue(sla.result()["success"])

    def test_add_iteration(self):
        sla = base.IterationTime(4.0)
        self.assertTrue(sla.add_iteration({"duration": 3.14}))
        self.assertTrue(sla.add_iteration({"duration": 2.0}))
        self.assertTrue(sla.add_iteration({"duration": 3.99}))
        self.assertFalse(sla.add_iteration({"duration": 4.5}))
        self.assertFalse(sla.add_iteration({"duration": 3.8}))


class MaxAverageDurationTestCase(test.TestCase):
    def test_config_schema(self):
        properties = {
            "max_avg_duration": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          base.MaxAverageDuration.validate, properties)

    def test_result(self):
        sla1 = base.MaxAverageDuration(42)
        sla2 = base.MaxAverageDuration(3.62)
        for sla in [sla1, sla2]:
            sla.add_iteration({"duration": 3.14})
            sla.add_iteration({"duration": 6.28})
        self.assertTrue(sla1.result()["success"])   # 42 > avg([3.14, 6.28])
        self.assertFalse(sla2.result()["success"])  # 3.62 < avg([3.14, 6.28])
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla = base.MaxAverageDuration(42)
        self.assertTrue(sla.result()["success"])

    def test_add_iteration(self):
        sla = base.MaxAverageDuration(4.0)
        self.assertTrue(sla.add_iteration({"duration": 3.5}))
        self.assertTrue(sla.add_iteration({"duration": 2.5}))
        self.assertTrue(sla.add_iteration({"duration": 5.0}))   # avg = 3.667
        self.assertFalse(sla.add_iteration({"duration": 7.0}))  # avg = 4.5
        self.assertTrue(sla.add_iteration({"duration": 1.0}))   # avg = 3.8


class OutliersTestCase(test.TestCase):

    def test_config_schema(self):
        base.Outliers.validate({"outliers": {"max": 0, "min_iterations": 5,
                                             "sigmas": 2.5}})
        self.assertRaises(jsonschema.ValidationError,
                          base.Outliers.validate,
                          {"outliers": {"max": -1}})
        self.assertRaises(jsonschema.ValidationError,
                          base.Outliers.validate,
                          {"outliers": {"max": 0, "min_iterations": 2}})
        self.assertRaises(jsonschema.ValidationError,
                          base.Outliers.validate,
                          {"outliers": {"max": 0, "sigmas": 0}})

    def test_result(self):
        sla1 = base.Outliers({"max": 1})
        sla2 = base.Outliers({"max": 2})
        iteration_durations = [3.1, 4.2, 3.6, 4.5, 2.8, 3.3, 4.1, 3.8, 4.3,
                               2.9, 10.2, 11.2, 3.4]  # outliers: 10.2, 11.2
        for sla in [sla1, sla2]:
            for d in iteration_durations:
                sla.add_iteration({"duration": d})
        self.assertFalse(sla1.result()["success"])  # 2 outliers >  1
        self.assertTrue(sla2.result()["success"])   # 2 outliers <= 2
        self.assertEqual("Failed", sla1.status())
        self.assertEqual("Passed", sla2.status())

    def test_result_large_sigmas(self):
        sla = base.Outliers({"max": 1, "sigmas": 5})
        iteration_durations = [3.1, 4.2, 3.6, 4.5, 2.8, 3.3, 4.1, 3.8, 4.3,
                               2.9, 10.2, 11.2, 3.4]
        for d in iteration_durations:
            sla.add_iteration({"duration": d})
        # NOTE(msdubov): No outliers registered since sigmas = 5 (not 2)
        self.assertTrue(sla.result()["success"])
        self.assertEqual("Passed", sla.status())

    def test_result_no_iterations(self):
        sla = base.Outliers({"max": 0})
        self.assertTrue(sla.result()["success"])

    def test_result_few_iterations_large_min_iterations(self):
        sla = base.Outliers({"max": 0, "min_iterations": 10})
        iteration_durations = [3.1, 4.2, 4.7, 3.6, 15.14, 2.8]
        for d in iteration_durations:
            sla.add_iteration({"duration": d})
        # NOTE(msdubov): SLA doesn't fail because it hasn't iterations < 10
        self.assertTrue(sla.result()["success"])

    def test_result_few_iterations_small_min_iterations(self):
        sla = base.Outliers({"max": 0, "min_iterations": 5})
        iteration_durations = [3.1, 4.2, 4.7, 3.6, 15.14, 2.8]
        for d in iteration_durations:
            sla.add_iteration({"duration": d})
        # NOTE(msdubov): Now this SLA can fail with >= 5 iterations
        self.assertFalse(sla.result()["success"])

    def test_add_iteration(self):
        sla = base.Outliers({"max": 1})
        # NOTE(msdubov): One outlier in the first 11 iterations
        first_iterations = [3.1, 4.2, 3.6, 4.5, 2.8, 3.3, 4.1, 3.8, 4.3,
                            2.9, 10.2]
        for d in first_iterations:
            self.assertTrue(sla.add_iteration({"duration": d}))
        # NOTE(msdubov): 12th iteration makes the SLA always failed
        self.assertFalse(sla.add_iteration({"duration": 11.2}))
        self.assertFalse(sla.add_iteration({"duration": 3.4}))
