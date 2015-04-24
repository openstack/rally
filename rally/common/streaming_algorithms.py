# Copyright 2015: Mirantis Inc.
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

import abc
import math

import six

from rally.common.i18n import _
from rally import exceptions


@six.add_metaclass(abc.ABCMeta)
class StreamingAlgorithm(object):
    """Base class for streaming computations that scale."""

    @abc.abstractmethod
    def add(self, value):
        """Process a single value from the input stream."""

    @abc.abstractmethod
    def result(self):
        """Return the result based on the values processed so far."""


class MeanStreamingComputation(StreamingAlgorithm):
    """Computes mean for a stream of numbers."""

    def __init__(self):
        self.total = 0.0
        self.count = 0

    def add(self, value):
        self.count += 1
        self.total += value

    def result(self):
        if self.count == 0:
            message = _("Unable to calculate the mean: "
                        "no values processed so far.")
            raise exceptions.RallyException(message)
        return self.total / self.count


class StdDevStreamingComputation(StreamingAlgorithm):
    """Computes the standard deviation for a stream of numbers."""

    def __init__(self):
        self.count = 0
        # NOTE(msdubov): To compute std, we need the auxiliary variables below.
        self.dev_sum = 0.0
        self.mean_computation = MeanStreamingComputation()
        self.mean = 0.0

    def add(self, value):
        # NOTE(msdubov): This streaming method for std computation appears
        #                in "The Art of Computer Programming" by D. Knuth,
        #                Vol 2, p. 232, 3rd edition.
        self.count += 1
        mean_prev = self.mean
        self.mean_computation.add(value)
        self.mean = self.mean_computation.result()
        self.dev_sum = self.dev_sum + (value - mean_prev) * (value - self.mean)

    def result(self):
        if self.count < 2:
            message = _("Unable to calculate the standard deviation: "
                        "need at least two values to be processed.")
            raise exceptions.RallyException(message)
        return math.sqrt(self.dev_sum / (self.count - 1))
