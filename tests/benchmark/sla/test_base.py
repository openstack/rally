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

from rally.benchmark.sla import base
from tests import test


class TestCriterion(base.SLA):
    OPTION_NAME = "test_criterion"
    CONFIG_SCHEMA = {"type": "integer"}

    @staticmethod
    def check(criterion_value, result):
        return criterion_value == result["data"]


class BaseSLATestCase(test.TestCase):

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
        task = mock.Mock()
        config = {
            "sla": {"test_criterion": 42},
        }
        task.results = [{"key": {"kw": config, "name": "fake", "pos": 0},
                        "data": 42}]
        results = list(base.SLA.check_all(task))
        expected = [{'benchmark': 'fake',
                     'criterion': 'test_criterion',
                     'pos': 0,
                     'success': True}]
        self.assertEqual(expected, results)
        task.results[0]["data"] = 43
        results = list(base.SLA.check_all(task))
        expected = [{'benchmark': 'fake',
                     'criterion': 'test_criterion',
                     'pos': 0,
                     'success': False}]
        self.assertEqual(expected, results)


class FailureRateTestCase(test.TestCase):
    def test_check(self):
        raw = [
                {"error": ["error"]},
                {"error": []},
        ]  # one error and one success. 50% success rate
        result = {"data": {"raw": raw}}
        self.assertTrue(base.FailureRate.check(75.0, result))  # 50% < 75.0%
        self.assertFalse(base.FailureRate.check(25, result))  # 50% > 25%


class IterationTimeTestCase(test.TestCase):
    def test_check(self):
        raw = [
                {"duration": 3.14},
                {"duration": 6.28},
        ]
        result = {"data": {"raw": raw}}
        self.assertTrue(base.IterationTime.check(42, result))
        self.assertFalse(base.IterationTime.check(3.62, result))
