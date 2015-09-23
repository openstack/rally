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


from rally.common.plugin import plugin
from rally.task import sla
from tests.unit import test


@plugin.configure(name="test_criterion")
class TestCriterion(sla.SLA):
    CONFIG_SCHEMA = {"type": "integer"}

    def add_iteration(self, iteration):
        self.success = self.criterion_value == iteration
        return self.success

    def details(self):
        return "detail"


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
