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

from rally import consts
from rally.task import sla

if t.TYPE_CHECKING:  # pragma: no cover
    from rally.task import runner


@sla.configure(name="max_seconds_per_iteration")
class IterationTime(sla.SLA):
    """Maximum time for one iteration in seconds."""
    CONFIG_SCHEMA = {
        "type": "number",
        "$schema": consts.JSON_SCHEMA7,
        "minimum": 0.0,
        "exclusiveMinimum": 0.0}

    def __init__(self, criterion_value: float) -> None:
        super(IterationTime, self).__init__(criterion_value)
        self.max_iteration_time = 0.0

    def add_iteration(self, iteration: runner.ScenarioRunnerResult) -> bool:
        if iteration["duration"] > self.max_iteration_time:
            self.max_iteration_time = iteration["duration"]
        self.success = self.max_iteration_time <= self.criterion_value
        return self.success

    def merge(self, other: IterationTime) -> bool:
        if other.max_iteration_time > self.max_iteration_time:
            self.max_iteration_time = other.max_iteration_time
        self.success = self.max_iteration_time <= self.criterion_value
        return self.success

    def details(self) -> str:
        return ("Maximum seconds per iteration %.2fs <= %.2fs - %s" %
                (self.max_iteration_time, self.criterion_value, self.status()))
