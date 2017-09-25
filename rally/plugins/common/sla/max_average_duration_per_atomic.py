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


"""
SLA (Service-level agreement) is set of details for determining compliance
with contracted values such as maximum error rate or minimum response time.
"""

import collections

from rally.common import streaming_algorithms
from rally import consts
from rally.task import sla


@sla.configure(name="max_avg_duration_per_atomic")
class MaxAverageDurationPerAtomic(sla.SLA):
    """Maximum average duration of one iterations atomic actions in seconds."""
    CONFIG_SCHEMA = {"type": "object", "$schema": consts.JSON_SCHEMA,
                     "patternProperties": {".*": {
                         "type": "number",
                         "description": "The name of atomic action."}},
                     "minProperties": 1,
                     "additionalProperties": False}

    def __init__(self, criterion_value):
        super(MaxAverageDurationPerAtomic, self).__init__(criterion_value)
        self.avg_by_action = collections.defaultdict(float)
        self.avg_comp_by_action = collections.defaultdict(
            streaming_algorithms.MeanComputation)
        self.criterion_items = self.criterion_value.items()

    def add_iteration(self, iteration):
        if not iteration.get("error"):
            for action in iteration["atomic_actions"]:
                duration = action["finished_at"] - action["started_at"]
                self.avg_comp_by_action[action["name"]].add(duration)
                result = self.avg_comp_by_action[action["name"]].result()
                self.avg_by_action[action["name"]] = result
        self.success = all(self.avg_by_action[atom] <= val
                           for atom, val in self.criterion_items)
        return self.success

    def merge(self, other):
        for atom, comp in self.avg_comp_by_action.items():
            if atom in other.avg_comp_by_action:
                comp.merge(other.avg_comp_by_action[atom])
        self.avg_by_action = {a: comp.result() or 0.0
                              for a, comp in self.avg_comp_by_action.items()}
        self.success = all(self.avg_by_action[atom] <= val
                           for atom, val in self.criterion_items)
        return self.success

    def details(self):
        strs = ["Action: '%s'. %.2fs <= %.2fs" %
                (atom, self.avg_by_action[atom], val)
                for atom, val in self.criterion_items]
        head = "Average duration of one iteration for atomic actions:"
        end = "Status: %s" % self.status()
        return "\n".join([head] + strs + [end])
