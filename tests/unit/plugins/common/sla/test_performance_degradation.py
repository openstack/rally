# Copyright 2016: Mirantis Inc.
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

from rally.plugins.common.sla import performance_degradation as perfdegr
from tests.unit import test


@ddt.ddt
class PerformanceDegradationTestCase(test.TestCase):

    def setUp(self):
        super(PerformanceDegradationTestCase, self).setUp()
        self.sla = perfdegr.PerformanceDegradation({"max_degradation": 50})

    def test_config_schema(self):
        properties = {
            "performance_degradation": {}
        }
        self.assertRaises(
            jsonschema.ValidationError,
            perfdegr.PerformanceDegradation.validate,
            properties)
        properties["performance_degradation"]["max_degradation"] = -1
        self.assertRaises(
            jsonschema.ValidationError,
            perfdegr.PerformanceDegradation.validate,
            properties)
        properties["performance_degradation"]["max_degradation"] = 1000.0
        perfdegr.PerformanceDegradation.validate(properties)

    @ddt.data(([39.0, 30.0, 32.0, 49.0, 47.0, 43.0], False, "Failed"),
              ([31.0, 30.0, 32.0, 39.0, 45.0, 43.0], True, "Passed"),
              ([], True, "Passed"))
    @ddt.unpack
    def test_iterations(self, durations, result, status):
        for duration in durations:
            self.sla.add_iteration({"duration": duration})
        self.assertIs(self.sla.success, result)
        self.assertIs(self.sla.result()["success"], result)
        self.assertEqual(status, self.sla.status())

    @ddt.data(([39.0, 30.0, 32.0], [49.0, 40.0, 51.0], False, "Failed"),
              ([31.0, 30.0, 32.0], [39.0, 45.0, 43.0], True, "Passed"),
              ([31.0, 30.0, 32.0], [32.0, 49.0, 30.0], False, "Failed"),
              ([], [31.0, 30.0, 32.0], True, "Passed"),
              ([31.0, 30.0, 32.0], [], True, "Passed"),
              ([], [], True, "Passed"),
              ([35.0, 30.0, 49.0], [], False, "Failed"),
              ([], [35.0, 30.0, 49.0], False, "Failed"))
    @ddt.unpack
    def test_merge(self, durations1, durations2, result, status):
        for duration in durations1:
            self.sla.add_iteration({"duration": duration})

        sla2 = perfdegr.PerformanceDegradation({"max_degradation": 50})
        for duration in durations2:
            sla2.add_iteration({"duration": duration})

        self.sla.merge(sla2)
        self.assertIs(self.sla.success, result)
        self.assertIs(self.sla.result()["success"], result)
        self.assertEqual(status, self.sla.status())

    def test_details(self):
        self.assertEqual("Current degradation: 0.0% - Passed",
                         self.sla.details())

        for duration in [39.0, 30.0, 32.0]:
            self.sla.add_iteration({"duration": duration})

        self.assertEqual("Current degradation: 30.0% - Passed",
                         self.sla.details())

        self.sla.add_iteration({"duration": 75.0})

        self.assertEqual("Current degradation: 150.0% - Failed",
                         self.sla.details())
