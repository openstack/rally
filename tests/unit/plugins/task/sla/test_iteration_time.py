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

from rally.plugins.task.sla import iteration_time
from rally.task import sla
from tests.unit import test


@ddt.ddt
class IterationTimeTestCase(test.TestCase):

    @ddt.data((1, True), (1000, True), (0, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        results = sla.SLA.validate(
            "max_seconds_per_iteration", None, None, config)
        if valid:
            self.assertEqual([], results)
        else:
            self.assertEqual(1, len(results))

    def test_result(self):
        sla1 = iteration_time.IterationTime(42)
        sla2 = iteration_time.IterationTime(3.62)
        for sla_inst in [sla1, sla2]:
            sla_inst.add_iteration({"duration": 3.14})
            sla_inst.add_iteration({"duration": 6.28})
        self.assertTrue(sla1.result()["success"])   # 42 > 6.28
        self.assertFalse(sla2.result()["success"])  # 3.62 < 6.28
        self.assertEqual("Passed", sla1.status())
        self.assertEqual("Failed", sla2.status())

    def test_result_no_iterations(self):
        sla_inst = iteration_time.IterationTime(42)
        self.assertTrue(sla_inst.result()["success"])

    def test_add_iteration(self):
        sla_inst = iteration_time.IterationTime(4.0)
        self.assertTrue(sla_inst.add_iteration({"duration": 3.14}))
        self.assertTrue(sla_inst.add_iteration({"duration": 2.0}))
        self.assertTrue(sla_inst.add_iteration({"duration": 3.99}))
        self.assertFalse(sla_inst.add_iteration({"duration": 4.5}))
        self.assertFalse(sla_inst.add_iteration({"duration": 3.8}))

    @ddt.data([[1.0, 2.0, 1.5, 4.3],
               [2.1, 3.4, 1.2, 6.3, 7.2, 7.0, 1.],
               [1.1, 1.1, 2.2, 2.2, 3.3, 4.3]])
    def test_merge(self, durations):

        single_sla = iteration_time.IterationTime(4.0)

        for dd in durations:
            for d in dd:
                single_sla.add_iteration({"duration": d})

        slas = [iteration_time.IterationTime(4.0) for _ in durations]

        for idx, sla_inst in enumerate(slas):
            for duration in durations[idx]:
                sla_inst.add_iteration({"duration": duration})

        merged_sla = slas[0]
        for sla_inst in slas[1:]:
            merged_sla.merge(sla_inst)

        self.assertEqual(single_sla.success, merged_sla.success)
        self.assertEqual(single_sla.max_iteration_time,
                         merged_sla.max_iteration_time)
