# Copyright 2013: Mirantis Inc.
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

"""Test for Rally search utils."""

from rally.benchmark.scenarios.dummy import dummy
from rally import searchutils
from tests import test


class FindBenchmarkScenarioGroupTestCase(test.TestCase):

    def test_find_success(self):
        scenario_group = searchutils.find_benchmark_scenario_group("Dummy")
        self.assertEqual(scenario_group, dummy.Dummy)

    def test_find_failure(self):
        scenario_group = searchutils.find_benchmark_scenario_group("Dumy")
        self.assertEqual(scenario_group, None)


class FindBenchmarkScenarioTestCase(test.TestCase):

    def test_find_success_full_path(self):
        scenario_method = searchutils.find_benchmark_scenario("Dummy.dummy")
        self.assertEqual(scenario_method, dummy.Dummy.dummy)

    def test_find_success_shortened_path(self):
        scenario_method = searchutils.find_benchmark_scenario("dummy")
        self.assertEqual(scenario_method, dummy.Dummy.dummy)

    def test_find_failure_bad_shortening(self):
        scenario_method = searchutils.find_benchmark_scenario("dumy")
        self.assertEqual(scenario_method, None)

    def test_find_failure_bad_group_name(self):
        scenario_method = searchutils.find_benchmark_scenario("Dumy.dummy")
        self.assertEqual(scenario_method, None)

    def test_find_failure_bad_scenario_name(self):
        scenario_method = searchutils.find_benchmark_scenario("Dummy.dumy")
        self.assertEqual(scenario_method, None)
