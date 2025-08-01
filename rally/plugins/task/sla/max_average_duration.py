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


"""
SLA (Service-level agreement) is set of details for determining compliance
with contracted values such as maximum error rate or minimum response time.
"""

from __future__ import annotations

import typing as t

from rally.common import streaming_algorithms
from rally import consts
from rally.task import sla

if t.TYPE_CHECKING:  # pragma: no cover
    from rally.task import runner


@sla.configure(name="max_avg_duration")
class MaxAverageDuration(sla.SLA):
    """Maximum average duration of one iteration in seconds."""
    CONFIG_SCHEMA = {
        "type": "number",
        "$schema": consts.JSON_SCHEMA7,
        "exclusiveMinimum": 0.0
    }

    def __init__(self, criterion_value: float) -> None:
        super(MaxAverageDuration, self).__init__(criterion_value)
        self.avg = 0.0
        self.avg_comp = streaming_algorithms.MeanComputation()

    def add_iteration(self, iteration: runner.ScenarioRunnerResult) -> bool:
        if not iteration.get("error"):
            self.avg_comp.add(iteration["duration"])
            self.avg = self.avg_comp.result()
        self.success = self.avg <= self.criterion_value
        return self.success

    def merge(self, other: MaxAverageDuration) -> bool:
        self.avg_comp.merge(other.avg_comp)
        self.avg = self.avg_comp.result() or 0.0
        self.success = self.avg <= self.criterion_value
        return self.success

    def details(self) -> str:
        return ("Average duration of one iteration %.2fs <= %.2fs - %s" %
                (self.avg, self.criterion_value, self.status()))
