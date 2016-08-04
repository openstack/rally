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

from __future__ import division

import abc
import math

import six

from rally.task.processing import utils


@six.add_metaclass(abc.ABCMeta)
class StreamingAlgorithm(object):
    """Base class for streaming computations that scale."""

    @abc.abstractmethod
    def add(self, value):
        """Process a single value from the input stream."""

    @abc.abstractmethod
    def merge(self, other):
        """Merge results processed by another instance."""

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

    def merge(self, other):
        self.count += other.count
        self.total += other.total

    def result(self):
        if self.count:
            return self.total / self.count
        return None


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

    def merge(self, other):
        if not other.mean_computation.count:
            return
        dev_sum1 = self.dev_sum
        count1 = self.count
        mean1 = self.mean

        dev_sum2 = other.dev_sum
        count2 = other.count
        mean2 = other.mean

        self.mean_computation.merge(other.mean_computation)
        self.mean = self.mean_computation.result()
        self.count += other.count

        self.dev_sum = (dev_sum1 + count1 * mean1 ** 2 +
                        dev_sum2 + count2 * mean2 ** 2 -
                        self.count * self.mean ** 2)

    def result(self):
        # NOTE(amaretskiy): Need at least two values to be processed
        if self.count < 2:
            return None
        return math.sqrt(self.dev_sum / (self.count - 1))


class MinComputation(StreamingAlgorithm):
    """Compute minimal value from a stream of numbers."""

    def __init__(self):
        self._value = None

    def add(self, value):
        value = self._cast_to_float(value)

        if self._value is None or value < self._value:
            self._value = value

    def merge(self, other):
        if other._value is not None:
            self.add(other._value)

    def result(self):
        return self._value


class MaxComputation(StreamingAlgorithm):
    """Compute maximal value from a stream of numbers."""

    def __init__(self):
        self._value = None

    def add(self, value):
        value = self._cast_to_float(value)

        if self._value is None or value > self._value:
            self._value = value

    def merge(self, other):
        if other._value is not None:
            self.add(other._value)

    def result(self):
        return self._value


class PercentileComputation(StreamingAlgorithm):
    """Compute percentile value from a stream of numbers."""

    def __init__(self, percent, length):
        """Init streaming computation.

        :param percent: numeric percent (from 0.00..1 to 0.999..)
        :param length: count of the measurements
        """
        if not 0 < percent < 1:
            raise ValueError("Unexpected percent: %s" % percent)
        self._percent = percent

        self._graph_zipper = utils.GraphZipper(length, 10000)

    def add(self, value):
        self._graph_zipper.add_point(value)

    def merge(self, other):
        # TODO(ikhudoshyn): Implement me
        raise NotImplementedError()

    def result(self):
        results = list(
            map(lambda x: x[1], self._graph_zipper.get_zipped_graph()))
        if results:
            # NOTE(amaretskiy): Calculate percentile of a list of values
            results.sort()
            k = (len(results) - 1) * self._percent
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return results[int(k)]
            d0 = results[int(f)] * (c - k)
            d1 = results[int(c)] * (k - f)
            return (d0 + d1)
        return None


class IncrementComputation(StreamingAlgorithm):
    """Simple incremental counter."""

    def __init__(self):
        self._count = 0

    def add(self, *args):
        self._count += 1

    def merge(self, other):
        self._count += other._count

    def result(self):
        return self._count


class DegradationComputation(StreamingAlgorithm):
    """Calculates degradation from a stream of numbers

    Finds min and max values from a stream and then calculates
    ratio between them in percentage. Works only with positive numbers.
    """

    def __init__(self):
        self.min_value = MinComputation()
        self.max_value = MaxComputation()

    def add(self, value):
        if value <= 0.0:
            raise ValueError("Unexpected value: %s" % value)
        self.min_value.add(value)
        self.max_value.add(value)

    def merge(self, other):
        min_result = other.min_value.result()
        if min_result is not None:
            self.min_value.add(min_result)
        max_result = other.max_value.result()
        if max_result is not None:
            self.max_value.add(max_result)

    def result(self):
        min_result = self.min_value.result()
        max_result = self.max_value.result()
        if min_result is None or max_result is None:
            return 0.0
        return (max_result / min_result - 1) * 100.0
