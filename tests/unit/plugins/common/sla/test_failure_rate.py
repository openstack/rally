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

from rally.plugins.common.sla import failure_rate
from tests.unit import test


class SLAPluginTestCase(test.TestCase):

    def test_validate(self):
        cnf = {"test_criterion": 42}
        failure_rate.sla.SLA.validate(cnf)

    def test_validate_invalid_name(self):
        self.assertRaises(jsonschema.ValidationError,
                          failure_rate.FailureRate.validate,
                          {"nonexistent": 42})

    def test_validate_invalid_type(self):
        self.assertRaises(jsonschema.ValidationError,
                          failure_rate.FailureRate.validate,
                          {"test_criterion": 42.0})


@ddt.ddt
class FailureRateTestCase(test.TestCase):

    def test_config_schema(self):
        self.assertRaises(jsonschema.ValidationError,
                          failure_rate.FailureRate.validate,
                          {"failure_rate": {"min": -1}})
        self.assertRaises(jsonschema.ValidationError,
                          failure_rate.FailureRate.validate,
                          {"failure_rate": {"min": 100.1}})
        self.assertRaises(jsonschema.ValidationError,
                          failure_rate.FailureRate.validate,
                          {"failure_rate": {"max": -0.1}})
        self.assertRaises(jsonschema.ValidationError,
                          failure_rate.FailureRate.validate,
                          {"failure_rate": {"max": 101}})

    def test_result_min(self):
        sla1 = failure_rate.FailureRate({"min": 80.0})
        sla2 = failure_rate.FailureRate({"min": 60.5})
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
        sla1 = failure_rate.FailureRate({"max": 25.0})
        sla2 = failure_rate.FailureRate({"max": 75.0})
        # 50% failure rate
        for sla in [sla1, sla2]:
            sla.add_iteration({"error": ["error"]})
            sla.add_iteration({"error": []})
        self.assertFalse(sla1.result()["success"])  # 25.0% < 50.0%
        self.assertTrue(sla2.result()["success"])   # 75.0% > 50.0%
        self.assertEqual("Failed", sla1.status())
        self.assertEqual("Passed", sla2.status())

    def test_result_min_max(self):
        sla1 = failure_rate.FailureRate({"min": 50, "max": 90})
        sla2 = failure_rate.FailureRate({"min": 5, "max": 20})
        sla3 = failure_rate.FailureRate({"min": 24.9, "max": 25.1})
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
        sla = failure_rate.FailureRate({"max": 10.0})
        self.assertTrue(sla.result()["success"])

    def test_add_iteration(self):
        sla = failure_rate.FailureRate({"max": 35.0})
        self.assertTrue(sla.add_iteration({"error": []}))
        self.assertTrue(sla.add_iteration({"error": []}))
        self.assertTrue(sla.add_iteration({"error": []}))
        self.assertTrue(sla.add_iteration({"error": ["error"]}))   # 33%
        self.assertFalse(sla.add_iteration({"error": ["error"]}))  # 40%

    @ddt.data([[0, 1, 0, 0],
               [0, 1, 1, 1, 0, 0, 0, 0],
               [0, 0, 1, 0, 0, 1]])
    def test_merge(self, errors):

        single_sla = failure_rate.FailureRate({"max": 25})

        for ee in errors:
            for e in ee:
                single_sla.add_iteration({"error": ["error"] if e else []})

        slas = [failure_rate.FailureRate({"max": 25}) for _ in errors]

        for idx, sla in enumerate(slas):
            for e in errors[idx]:
                sla.add_iteration({"error": ["error"] if e else []})

        merged_sla = slas[0]
        for sla in slas[1:]:
            merged_sla.merge(sla)

        self.assertEqual(single_sla.success, merged_sla.success)
        self.assertEqual(single_sla.errors, merged_sla.errors)
        self.assertEqual(single_sla.total, merged_sla.total)
