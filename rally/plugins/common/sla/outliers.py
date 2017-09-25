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

from rally.common import streaming_algorithms
from rally import consts
from rally.task import sla


@sla.configure(name="outliers")
class Outliers(sla.SLA):
    """Limit the number of outliers (iterations that take too much time).

    The outliers are detected automatically using the computation of the mean
    and standard deviation (std) of the data.
    """
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "max": {"type": "integer", "minimum": 0},
            "min_iterations": {"type": "integer", "minimum": 3},
            "sigmas": {"type": "number", "minimum": 0.0,
                       "exclusiveMinimum": True}
        },
        "additionalProperties": False,
    }

    def __init__(self, criterion_value):
        super(Outliers, self).__init__(criterion_value)
        self.max_outliers = self.criterion_value.get("max", 0)
        # NOTE(msdubov): Having 3 as default is reasonable (need enough data).
        self.min_iterations = self.criterion_value.get("min_iterations", 3)
        self.sigmas = self.criterion_value.get("sigmas", 3.0)
        self.iterations = 0
        self.outliers = 0
        self.threshold = None
        self.mean_comp = streaming_algorithms.MeanComputation()
        self.std_comp = streaming_algorithms.StdDevComputation()

    def add_iteration(self, iteration):
        # NOTE(ikhudoshyn): This method can not be implemented properly.
        # After adding a new iteration, both mean and standard deviation
        # may change. Hence threshold will change as well. In this case we
        # should again compare durations of all accounted iterations
        # to the threshold. Unfortunately we can not do it since
        # we do not store durations.
        # Implementation provided here only gives rough approximation
        # of outliers number.
        if not iteration.get("error"):
            duration = iteration["duration"]
            self.iterations += 1

            # NOTE(msdubov): First check if the current iteration is an outlier
            if ((self.iterations >= self.min_iterations and self.threshold and
                 duration > self.threshold)):
                self.outliers += 1

            # NOTE(msdubov): Then update the threshold value
            self.mean_comp.add(duration)
            self.std_comp.add(duration)
            if self.iterations >= 2:
                mean = self.mean_comp.result()
                std = self.std_comp.result()
                self.threshold = mean + self.sigmas * std

        self.success = self.outliers <= self.max_outliers
        return self.success

    def merge(self, other):
        # NOTE(ikhudoshyn): This method can not be implemented properly.
        # After merge, both mean and standard deviation may change.
        # Hence threshold will change as well. In this case we
        # should again compare durations of all accounted iterations
        # to the threshold. Unfortunately we can not do it since
        # we do not store durations.
        # Implementation provided here only gives rough approximation
        # of outliers number.
        self.iterations += other.iterations
        self.outliers += other.outliers
        self.mean_comp.merge(other.mean_comp)
        self.std_comp.merge(other.std_comp)

        if self.iterations >= 2:
            mean = self.mean_comp.result()
            std = self.std_comp.result()
            self.threshold = mean + self.sigmas * std

        self.success = self.outliers <= self.max_outliers
        return self.success

    def details(self):
        return ("Maximum number of outliers %i <= %i - %s" %
                (self.outliers, self.max_outliers, self.status()))
