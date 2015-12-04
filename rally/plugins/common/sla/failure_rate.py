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

from rally.common.i18n import _
from rally import consts
from rally.task import sla


@sla.configure(name="failure_rate")
class FailureRate(sla.SLA):
    """Failure rate minimum and maximum in percents."""
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "min": {"type": "number", "minimum": 0.0, "maximum": 100.0},
            "max": {"type": "number", "minimum": 0.0, "maximum": 100.0}
        }
    }

    def __init__(self, criterion_value):
        super(FailureRate, self).__init__(criterion_value)
        self.min_percent = self.criterion_value.get("min", 0)
        self.max_percent = self.criterion_value.get("max", 100)
        self.errors = 0
        self.total = 0
        self.error_rate = 0.0

    def add_iteration(self, iteration):
        self.total += 1
        if iteration["error"]:
            self.errors += 1
        self.error_rate = self.errors * 100.0 / self.total
        self.success = self.min_percent <= self.error_rate <= self.max_percent
        return self.success

    def merge(self, other):
        self.total += other.total
        self.errors += other.errors
        if self.total:
            self.error_rate = self.errors * 100.0 / self.total
        self.success = self.min_percent <= self.error_rate <= self.max_percent
        return self.success

    def details(self):
        return (_("Failure rate criteria %.2f%% <= %.2f%% <= %.2f%% - %s") %
                (self.min_percent, self.error_rate, self.max_percent,
                 self.status()))
