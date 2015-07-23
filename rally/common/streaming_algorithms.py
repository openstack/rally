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
import heapq
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

    def _cast_to_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            raise TypeError("Non-numerical value: %r" % value)


class MeanComputation(StreamingAlgorithm):
    """Compute mean for a stream of numbers."""

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


class StdDevComputation(StreamingAlgorithm):
    """Compute standard deviation for a stream of numbers."""

    def __init__(self):
        self.count = 0
        # NOTE(msdubov): To compute std, we need the auxiliary variables below.
        self.dev_sum = 0.0
        self.mean_computation = MeanComputation()
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


class MinComputation(StreamingAlgorithm):
    """Compute minimal value from a stream of numbers."""

    def __init__(self):
        self._value = None

    def add(self, value):
        value = self._cast_to_float(value)

        if self._value is None or value < self._value:
            self._value = value

    def result(self):
        if self._value is None:
            raise ValueError("No values have been processed")
        return self._value


class MaxComputation(StreamingAlgorithm):
    """Compute maximal value from a stream of numbers."""

    def __init__(self):
        self._value = None

    def add(self, value):
        value = self._cast_to_float(value)

        if self._value is None or value > self._value:
            self._value = value

    def result(self):
        if self._value is None:
            raise ValueError("No values have been processed")
        return self._value


class PercentileComputation(StreamingAlgorithm):
    """Compute percentile value from a stream of numbers."""

    def __init__(self, percent):
        """Init streaming computation.

        :param percent: numeric percent (from 0.1 to 99.9)
        """
        if not 0 < percent < 100:
            raise ValueError("Unexpected percent: %s" % percent)
        self._percent = percent
        self._count = 0
        self._left = []
        self._right = []
        self._current_percentile = None

    def add(self, value):
        value = self._cast_to_float(value)

        if self._current_percentile and value > self._current_percentile:
            heapq.heappush(self._right, value)
        else:
            heapq.heappush(self._left, -value)

        self._count += 1
        expected_left = int(self._percent * (self._count + 1) / 100)

        if len(self._left) > expected_left:
            heapq.heappush(self._right, -heapq.heappop(self._left))
        elif len(self._left) < expected_left:
            heapq.heappush(self._left, -heapq.heappop(self._right))

        left = -self._left[0] if len(self._left) else 0
        right = self._right[0] if len(self._right) else 0

        self._current_percentile = left + (right - left) / 2.

    def result(self):
        if self._current_percentile is None:
            raise ValueError("No values have been processed")
        return self._current_percentile


class ProgressComputation(StreamingAlgorithm):
    """Compute progress in percent."""

    def __init__(self, base_count):
        """Init streaming computation.

        :param base_count: int number for end progress (100% reached)
        """
        self._base_count = int(base_count) or 1
        self._count = 0

    def add(self, *args):
        if self._count >= self._base_count:
            raise RuntimeError(
                "100%% progress is already reached (count of %d)"
                % self._base_count)
        self._count += 1

    def result(self):
        return self._count / float(self._base_count) * 100


class IncrementComputation(StreamingAlgorithm):
    """Simple incremental counter."""

    def __init__(self):
        self._count = 0

    def add(self, *args):
        self._count += 1

    def result(self):
        return self._count
