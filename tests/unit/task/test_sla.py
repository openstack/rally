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
import mock

from rally.common.plugin import plugin
from rally.task import sla
from tests.unit import test


@plugin.configure(name="test_criterion")
class TestCriterion(sla.SLA):
    CONFIG_SCHEMA = {"type": "integer"}

    def add_iteration(self, iteration):
        self.success = self.criterion_value == iteration
        return self.success

    def merge(self, other):
        raise NotImplementedError()

    def details(self):
        return "detail"


@ddt.ddt
class SLACheckerTestCase(test.TestCase):

    def test_add_iteration_and_results(self):
        sla_checker = sla.SLAChecker({"sla": {"test_criterion": 42}})

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
        sla_checker = sla.SLAChecker({"sla": {}})
        self.assertEqual([], sla_checker.results())
        sla_checker.set_unexpected_failure(exc)
        self.assertEqual([{"criterion": "something_went_wrong",
                           "success": False,
                           "detail": "Unexpected error: %s" % exc}],
                         sla_checker.results())

    def test_set_aborted_on_sla(self):
        sla_checker = sla.SLAChecker({"sla": {}})
        self.assertEqual([], sla_checker.results())
        sla_checker.set_aborted_on_sla()
        self.assertEqual(
            [{"criterion": "aborted_on_sla", "success": False,
              "detail": "Task was aborted due to SLA failure(s)."}],
            sla_checker.results())

    def test_set_aborted_manually(self):
        sla_checker = sla.SLAChecker({"sla": {}})
        self.assertEqual([], sla_checker.results())
        sla_checker.set_aborted_manually()
        self.assertEqual(
            [{"criterion": "aborted_manually", "success": False,
              "detail": "Task was aborted due to abort signal."}],
            sla_checker.results())

    def test__format_result(self):
        name = "some_name"
        success = True
        detail = "some details"
        self.assertEqual({"criterion": name,
                          "success": success,
                          "detail": detail},
                         sla._format_result(name, success, detail))

    def test__validate_config_positive(self):
        sla_checker = sla.SLAChecker({"sla": {}})
        another_sla_checker = sla.SLAChecker({"sla": {}})
        sla_checker._validate_config(another_sla_checker)

    def test__validate_config_negative(self):
        sla_checker = sla.SLAChecker({"sla": {}})
        another_sla_checker = sla.SLAChecker({"sla": {"test_criterion": 42}})
        self.assertRaises(TypeError, sla_checker._validate_config,
                          another_sla_checker)

    def test__validate_sla_types(self):
        sla_checker = sla.SLAChecker({"sla": {}})
        mock_sla1 = mock.MagicMock()
        mock_sla2 = mock.MagicMock()
        sla_checker.sla_criteria = [mock_sla1, mock_sla2]

        another_sla_checker = sla.SLAChecker({"sla": {}})
        mock_sla3 = mock.MagicMock()
        mock_sla4 = mock.MagicMock()
        another_sla_checker.sla_criteria = [mock_sla3, mock_sla4]

        sla_checker._validate_sla_types(another_sla_checker)

        mock_sla1.assert_has_calls([
            mock.call.validate_type(mock_sla3)
        ])

        mock_sla1.validate_type.assert_called_once_with(mock_sla3)
        mock_sla2.validate_type.assert_called_once_with(mock_sla4)

    @ddt.data({"merge_result1": True, "merge_result2": True,
               "result": True},
              {"merge_result1": True, "merge_result2": False,
               "result": False},
              {"merge_result1": False, "merge_result2": False,
               "result": False})
    @ddt.unpack
    def test_merge(self, merge_result1, merge_result2, result):
        sla_checker = sla.SLAChecker({"sla": {}})
        mock_sla1 = mock.MagicMock()
        mock_sla2 = mock.MagicMock()
        sla_checker.sla_criteria = [mock_sla1, mock_sla2]

        mock_sla1.merge.return_value = merge_result1
        mock_sla2.merge.return_value = merge_result2

        another_sla_checker = sla.SLAChecker({"sla": {}})
        mock_sla3 = mock.MagicMock()
        mock_sla4 = mock.MagicMock()
        another_sla_checker.sla_criteria = [mock_sla3, mock_sla4]

        sla_checker._validate_config = mock.MagicMock()
        sla_checker._validate_sla_types = mock.MagicMock()

        self.assertEqual(result, sla_checker.merge(another_sla_checker))
        mock_sla1.merge.assert_called_once_with(mock_sla3)
        mock_sla2.merge.assert_called_once_with(mock_sla4)


class SLATestCase(test.TestCase):
    def test_validate_type_positive(self):
        sla1 = TestCriterion(0)
        sla2 = TestCriterion(0)
        sla1.validate_type(sla2)

    def test_validate_type_negative(self):
        sla1 = TestCriterion(0)

        class AnotherTestCriterion(TestCriterion):
            pass

        sla2 = AnotherTestCriterion(0)
        self.assertRaises(TypeError, sla1.validate_type, sla2)
