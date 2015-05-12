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

from rally.plugins.common.sla import iteraion_time
from tests.unit import test


class IterationTimeTestCase(test.TestCase):
    def test_config_schema(self):
        properties = {
            "max_seconds_per_iteration": 0
        }
        self.assertRaises(jsonschema.ValidationError,
                          iteraion_time.IterationTime.validate, properties)

    def test_result(self):
        sla1 = iteraion_time.IterationTime(42)
        sla2 = iteraion_time.IterationTime(3.62)
        for sla in [sla1, sla2]:
            sla.add_iteration({"duration": 3.14})
            sla.add_iteration({"duration": 6.28})
        self.assertTrue(sla1.result()["success"])   # 42 > 6.28
        self.assertFalse(sla2.result()["success"])  # 3.62 < 6.28
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla = iteraion_time.IterationTime(42)
        self.assertTrue(sla.result()["success"])

    def test_add_iteration(self):
        sla = iteraion_time.IterationTime(4.0)
        self.assertTrue(sla.add_iteration({"duration": 3.14}))
        self.assertTrue(sla.add_iteration({"duration": 2.0}))
        self.assertTrue(sla.add_iteration({"duration": 3.99}))
        self.assertFalse(sla.add_iteration({"duration": 4.5}))
        self.assertFalse(sla.add_iteration({"duration": 3.8}))
