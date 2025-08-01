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

from __future__ import annotations

import typing as t

from rally.common import streaming_algorithms
from rally import consts
from rally.task import sla
from rally.utils import strutils

if t.TYPE_CHECKING:  # pragma: no cover
    from rally.task import runner


@sla.configure(name="performance_degradation")
class PerformanceDegradation(sla.SLA):
    """Calculates performance degradation based on iteration time

    This SLA plugin finds minimum and maximum duration of
    iterations completed without errors during Rally task execution.
    Assuming that minimum duration is 100%, it calculates
    performance degradation against maximum duration.
    """
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA7,
        "properties": {
            "max_degradation": {
                "type": "number",
                "minimum": 0.0,
            },
        },
        "required": [
            "max_degradation",
        ],
        "additionalProperties": False,
    }

    def __init__(self, criterion_value: dict[str, float]) -> None:
        super(PerformanceDegradation, self).__init__(criterion_value)
        self.max_degradation = self.criterion_value["max_degradation"]
        self.degradation = streaming_algorithms.DegradationComputation()

    def add_iteration(self, iteration: runner.ScenarioRunnerResult) -> bool:
        if not iteration.get("error"):
            self.degradation.add(iteration["duration"])
        self.success = self.degradation.result() <= self.max_degradation
        return self.success

    def merge(self, other: PerformanceDegradation) -> bool:
        self.degradation.merge(other.degradation)
        self.success = self.degradation.result() <= self.max_degradation
        return self.success

    def details(self) -> str:
        res = strutils.format_float_to_str(self.degradation.result() or 0.0)
        return "Current degradation: %s%% - %s" % (res, self.status())
