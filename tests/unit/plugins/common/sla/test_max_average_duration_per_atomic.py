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

from rally.plugins.common.sla import max_average_duration_per_atomic as madpa
from tests.unit import test


@ddt.ddt
class MaxAverageDurationPerAtomicTestCase(test.TestCase):
    def test_config_schema(self):
        properties = {
            "max_avg_duration_per_atomic": {"neutron.list_ports": "elf",
                                            "neutron.create_port": 1.0}
        }
        self.assertRaises(
            jsonschema.ValidationError,
            madpa.MaxAverageDurationPerAtomic.validate,
            properties)
        properties["max_avg_duration_per_atomic"]["neutron.list_ports"] = 1.0
        madpa.MaxAverageDurationPerAtomic.validate(properties)

    def test_result(self):
        cls = madpa.MaxAverageDurationPerAtomic
        sla1 = cls({"a1": 42, "a2": 42})
        sla2 = cls({"a1": 42, "a2": 2})
        for sla in [sla1, sla2]:
            sla.add_iteration({"atomic_actions": {"a1": 3.14, "a2": 7.77}})
            sla.add_iteration({"atomic_actions": {"a1": 8.14, "a2": 9.77}})
        self.assertTrue(sla1.result()["success"])
        self.assertFalse(sla2.result()["success"])
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla = madpa.MaxAverageDurationPerAtomic({"a1": 8.14, "a2": 9.77})
        self.assertTrue(sla.result()["success"])

    def test_add_iteration(self):
        sla = madpa.MaxAverageDurationPerAtomic({"a1": 5, "a2": 10})
        add = sla.add_iteration
        self.assertTrue(add({"atomic_actions": {"a1": 2.5, "a2": 5.0}}))
        self.assertTrue(add({"atomic_actions": {"a1": 5.0, "a2": 10.0}}))
        # the following pushes a2 over the limit
        self.assertFalse(add({"atomic_actions": {"a1": 5.0, "a2": 20.0}}))
        # bring a2 back
        self.assertTrue(add({"atomic_actions": {"a1": 5.0, "a2": 2.0}}))
        # push a1 over
        self.assertFalse(add({"atomic_actions": {"a1": 10.0, "a2": 2.0}}))
        # bring it back
        self.assertTrue(add({"atomic_actions": {"a1": 1.0, "a2": 2.0}}))

    @ddt.data([[1.0, 2.0, 1.5, 4.3],
               [2.1, 3.4, 1.2, 6.3, 7.2, 7.0, 1.],
               [1.1, 1.1, 2.2, 2.2, 3.3, 4.3]])
    def test_merge(self, durations):
        init = {"a1": 8.14, "a2": 9.77}
        single_sla = madpa.MaxAverageDurationPerAtomic(init)

        for dd in durations:
            for d in dd:
                single_sla.add_iteration(
                    {"atomic_actions": {"a1": d, "a2": d * 2}})

        slas = [madpa.MaxAverageDurationPerAtomic(init) for _ in durations]

        for idx, sla in enumerate(slas):
            for d in durations[idx]:
                sla.add_iteration({"atomic_actions": {"a1": d, "a2": d * 2}})

        merged_sla = slas[0]
        for sla in slas[1:]:
            merged_sla.merge(sla)

        self.assertEqual(single_sla.success, merged_sla.success)
        self.assertEqual(single_sla.avg_by_action, merged_sla.avg_by_action)
