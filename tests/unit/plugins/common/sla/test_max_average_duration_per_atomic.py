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

from rally.plugins.common.sla import max_average_duration_per_atomic as madpa
from rally.task import sla
from tests.unit import test


@ddt.ddt
class MaxAverageDurationPerAtomicTestCase(test.TestCase):

    @ddt.data(({"a": 10, "b": 20}, True),
              ({"a": "foo"}, False),
              ({}, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        results = sla.SLA.validate(
            "max_avg_duration_per_atomic", None, None, config)
        if valid:
            self.assertEqual([], results)
        else:
            self.assertEqual(1, len(results))

    def test_result(self):
        cls = madpa.MaxAverageDurationPerAtomic
        sla1 = cls({"a1": 42, "a2": 42})
        sla2 = cls({"a1": 42, "a2": 2})
        for sla_inst in [sla1, sla2]:
            sla_inst.add_iteration(
                {"atomic_actions": [
                    {"name": "a1",
                     "started_at": 0.0,
                     "finished_at": 3.14},
                    {"name": "a2",
                     "started_at": 10,
                     "finished_at": 17.77}]})
            sla_inst.add_iteration(
                {"atomic_actions": [
                    {"name": "a1",
                     "started_at": 12.0,
                     "finished_at": 15.14},
                    {"name": "a2",
                     "started_at": 13,
                     "finished_at": 27.33}]})
        self.assertTrue(sla1.result()["success"])
        self.assertFalse(sla2.result()["success"])
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla_inst = madpa.MaxAverageDurationPerAtomic({"a1": 8.14, "a2": 9.77})
        self.assertTrue(sla_inst.result()["success"])

    def test_add_iteration(self):
        sla_inst = madpa.MaxAverageDurationPerAtomic({"a1": 5, "a2": 10})
        add = sla_inst.add_iteration
        self.assertTrue(add({"atomic_actions": [
            {"name": "a1", "started_at": 0, "finished_at": 2.5},
            {"name": "a2", "started_at": 0, "finished_at": 5.0}]}))
        self.assertTrue(add({"atomic_actions": [
            {"name": "a1", "started_at": 0, "finished_at": 5.0},
            {"name": "a2", "started_at": 0, "finished_at": 10.0}]}))
        # the following pushes a2 over the limit
        self.assertFalse(add({"atomic_actions": [
            {"name": "a1", "started_at": 0, "finished_at": 5.0},
            {"name": "a2", "started_at": 0, "finished_at": 20.0}]}))
        # bring a2 back
        self.assertTrue(add({"atomic_actions": [
            {"name": "a1", "started_at": 0, "finished_at": 5.0},
            {"name": "a2", "started_at": 0, "finished_at": 2.0}]}))
        # push a1 over
        self.assertFalse(add({"atomic_actions": [
            {"name": "a1", "started_at": 0, "finished_at": 10.0},
            {"name": "a2", "started_at": 0, "finished_at": 2.0}]}))
        # bring it back
        self.assertTrue(add({"atomic_actions": [
            {"name": "a1", "started_at": 0, "finished_at": 1.0},
            {"name": "a2", "started_at": 0, "finished_at": 2.0}]}))

    def test_merge(self):
        durations = [[1.0, 2.0, 1.5, 4.3],
                     [2.1, 3.4, 1.2, 6.3, 7.2, 7.0, 1.],
                     [1.1, 1.1, 2.2, 2.2, 3.3, 4.3]]
        init = {"a1": 8.14, "a2": 9.77}
        single_sla = madpa.MaxAverageDurationPerAtomic(init)

        for dd in durations:
            for d in dd:
                single_sla.add_iteration(
                    {"atomic_actions": [{"name": "a1",
                                         "started_at": 0,
                                         "finished_at": d},
                                        {"name": "a2",
                                         "started_at": d,
                                         "finished_at": d * 3}
                                        ]})

        slas = [madpa.MaxAverageDurationPerAtomic(init) for _ in durations]

        for idx, sla_inst in enumerate(slas):
            for d in durations[idx]:
                sla_inst.add_iteration(
                    {"atomic_actions": [{"name": "a1",
                                         "started_at": 0,
                                         "finished_at": d},
                                        {"name": "a2",
                                         "started_at": d,
                                         "finished_at": d * 3}
                                        ]})

        merged_sla = slas[0]
        for sla_inst in slas[1:]:
            merged_sla.merge(sla_inst)

        self.assertEqual(single_sla.success, merged_sla.success)
        self.assertEqual(single_sla.avg_by_action, merged_sla.avg_by_action)
