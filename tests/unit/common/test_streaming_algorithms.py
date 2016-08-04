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

import math

import ddt
import six

from rally.common import streaming_algorithms as algo
from tests.unit import test


class MeanComputationTestCase(test.TestCase):

    def test_empty_stream(self):
        mean_computation = algo.MeanComputation()
        self.assertIsNone(mean_computation.result())

    def test_one_value(self):
        mean_computation = algo.MeanComputation()
        mean_computation.add(10.0)
        self.assertEqual(10.0, mean_computation.result())

    def test_stream(self):
        stream = range(10)
        mean_computation = algo.MeanComputation()
        for value in stream:
            mean_computation.add(value)
        excepted_mean = float(sum(stream)) / len(stream)
        self.assertEqual(excepted_mean, mean_computation.result())

    def test_merge(self):
        single_mean = algo.MeanComputation()

        for val in six.moves.range(100):
            single_mean.add(val)

        means = [algo.MeanComputation()
                 for _ in six.moves.range(10)]

        for idx, mean in enumerate(means):
            for val in six.moves.range(idx * 10, (idx + 1) * 10):
                mean.add(val)

        merged_mean = means[0]
        for mean in means[1:]:
            merged_mean.merge(mean)

        self.assertEqual(single_mean.count, merged_mean.count)
        self.assertEqual(single_mean.total, merged_mean.total)
        self.assertEqual(single_mean.result(), merged_mean.result())


class StdDevComputationTestCase(test.TestCase):

    def test_empty_stream(self):
        std_computation = algo.StdDevComputation()
        self.assertIsNone(std_computation.result())

    def test_one_value(self):
        std_computation = algo.StdDevComputation()
        std_computation.add(10.0)
        self.assertIsNone(std_computation.result())

    def test_two_values(self):
        std_computation = algo.StdDevComputation()
        std_computation.add(10.0)
        std_computation.add(10.0)
        self.assertEqual(0.0, std_computation.result())

    def test_stream(self):
        stream = range(10)
        std_computation = algo.StdDevComputation()
        for value in stream:
            std_computation.add(value)
        mean = float(sum(stream)) / len(stream)
        excepted_std = math.sqrt(sum((x - mean) ** 2 for x in stream) /
                                 (len(stream) - 1))
        self.assertEqual(excepted_std, std_computation.result())

    def test_merge(self):
        single_std = algo.StdDevComputation()

        for val in six.moves.range(100):
            single_std.add(val)

        stds = [algo.StdDevComputation()
                for _ in six.moves.range(10)]

        for idx, std in enumerate(stds):
            for val in six.moves.range(idx * 10, (idx + 1) * 10):
                std.add(val)

        merged_std = stds[0]
        for std in stds[1:]:
            merged_std.merge(std)

        self.assertEqual(single_std.count, merged_std.count)
        self.assertEqual(single_std.mean, merged_std.mean)
        self.assertEqual(single_std.dev_sum, merged_std.dev_sum)
        self.assertEqual(single_std.result(), merged_std.result())


class MinComputationTestCase(test.TestCase):

    def test_add_and_result(self):
        comp = algo.MinComputation()
        [comp.add(i) for i in [3, 5.2, 2, -1, 1, 8, 33.4, 0, -3, 42, -2]]
        self.assertEqual(-3, comp.result())

    def test_add_raises(self):
        comp = algo.MinComputation()
        self.assertRaises(TypeError, comp.add)
        self.assertRaises(TypeError, comp.add, None)
        self.assertRaises(TypeError, comp.add, "str")

    def test_result_empty(self):
        comp = algo.MinComputation()
        self.assertRaises(TypeError, comp.result, 1)
        self.assertIsNone(comp.result())

    def test_merge(self):
        single_min_algo = algo.MinComputation()

        for val in six.moves.range(100):
            single_min_algo.add(val)

        algos = [algo.MinComputation()
                 for _ in six.moves.range(10)]

        for idx, min_algo in enumerate(algos):
            for val in six.moves.range(idx * 10, (idx + 1) * 10):
                min_algo.add(val)

        merged_min_algo = algos[0]
        for min_algo in algos[1:]:
            merged_min_algo.merge(min_algo)

        self.assertEqual(single_min_algo._value, merged_min_algo._value)
        self.assertEqual(single_min_algo.result(), merged_min_algo.result())


class MaxComputationTestCase(test.TestCase):

    def test_add_and_result(self):
        comp = algo.MaxComputation()
        [comp.add(i) for i in [3, 5.2, 2, -1, 1, 8, 33.4, 0, -3, 42, -2]]
        self.assertEqual(42, comp.result())

    def test_add_raises(self):
        comp = algo.MaxComputation()
        self.assertRaises(TypeError, comp.add)
        self.assertRaises(TypeError, comp.add, None)
        self.assertRaises(TypeError, comp.add, "str")

    def test_result_empty(self):
        comp = algo.MaxComputation()
        self.assertRaises(TypeError, comp.result, 1)
        self.assertIsNone(comp.result())

    def test_merge(self):
        single_max_algo = algo.MaxComputation()

        for val in six.moves.range(100):
            single_max_algo.add(val)

        algos = [algo.MaxComputation()
                 for _ in six.moves.range(10)]

        for idx, max_algo in enumerate(algos):
            for val in six.moves.range(idx * 10, (idx + 1) * 10):
                max_algo.add(val)

        merged_max_algo = algos[0]
        for max_algo in algos[1:]:
            merged_max_algo.merge(max_algo)

        self.assertEqual(single_max_algo._value, merged_max_algo._value)
        self.assertEqual(single_max_algo.result(), merged_max_algo.result())


@ddt.ddt
class PercentileComputationTestCase(test.TestCase):

    mixed1 = [0]
    mixed6 = [100, 100, 0, 100, 100, 100]
    mixed5 = [0, 0, 100, 0, 0]
    mixed16 = [55.71, 83.05, 24.12, 27, 48.36, 16.36, 96.23, 6, 16.0, 88.11,
               29.52, 99.2, 79.96, 77.84, 85.45, 85.32, 7, 17.1, 3.02, 15.23]
    mixed50 = [51.63, 82.2, 52.52, .05, 66, 94.03, 78.6, 80.9, 51.89, 79, 1.4,
               65.06, 12.46, 51.89, 41, 45.39, 124, 62.2, 32.72, 56.98, 31.19,
               26.27, 97.3, 56.6, 19.75, 69, 25.03, 10.76, 17.71, 29.4, 15.75,
               19.88, 90.16, 82.0, 63.4, 14.84, 49.07, 72.06, 41, 1.48, 82.19,
               48.45, 53, 88.33, 52.31, 62, 15.96, 21.17, 25.33, 53.27]
    mixed5000 = mixed50 * 1000
    range5000 = range(5000)

    @ddt.data(
        {"stream": "mixed1", "percent": 0.95, "expected": 0},
        {"stream": "mixed6", "percent": 0.5, "expected": 100},
        {"stream": "mixed5", "percent": 0.5, "expected": 0},
        {"stream": "mixed5", "percent": 0.999, "expected": 99.6},
        {"stream": "mixed5", "percent": 0.001, "expected": 0},
        {"stream": "mixed16", "percent": 0.25, "expected": 16.27},
        {"stream": "mixed16", "percent": 0.50, "expected": 38.94},
        {"stream": "mixed16", "percent": 0.90, "expected":
            88.92200000000001},
        {"stream": "mixed50", "percent": 0.25, "expected": 25.105},
        {"stream": "mixed50", "percent": 0.50, "expected": 51.89},
        {"stream": "mixed50", "percent": 0.90, "expected":
            82.81300000000002},
        {"stream": "mixed5000", "percent": 0.25, "expected":
            35.54600000000001},
        {"stream": "mixed5000", "percent": 0.50, "expected": 48.351},
        {"stream": "mixed5000", "percent": 0.90, "expected":
            66.05880000000437},
        {"stream": "range5000", "percent": 0.25, "expected": 1249.75},
        {"stream": "range5000", "percent": 0.50, "expected": 2499.5},
        {"stream": "range5000", "percent": 0.90, "expected": 4499.1})
    @ddt.unpack
    def test_add_and_result(self, percent, stream, expected):
        comp = algo.PercentileComputation(percent=percent, length=len(
            getattr(self, stream)))
        [comp.add(i) for i in getattr(self, stream)]
        self.assertEqual(expected, comp.result())

    def test_add_raises(self):
        comp = algo.PercentileComputation(0.50, 100)
        self.assertRaises(TypeError, comp.add)

    def test_result_empty(self):
        self.assertRaises(TypeError, algo.PercentileComputation)
        comp = algo.PercentileComputation(0.50, 100)
        self.assertIsNone(comp.result())


class IncrementComputationTestCase(test.TestCase):

    def test_add_and_result(self):
        comp = algo.IncrementComputation()
        for i in range(1, 100):
            self.assertEqual(i - 1, comp.result())
            comp.add(42)
            self.assertEqual(i, comp.result())

    def test_merge(self):
        single_inc = algo.IncrementComputation()

        for val in six.moves.range(100):
            single_inc.add(val)

        incs = [algo.IncrementComputation()
                for _ in six.moves.range(10)]

        for idx, inc in enumerate(incs):
            for val in six.moves.range(idx * 10, (idx + 1) * 10):
                inc.add(val)

        merged_inc = incs[0]
        for inc in incs[1:]:
            merged_inc.merge(inc)

        self.assertEqual(single_inc._count, merged_inc._count)
        self.assertEqual(single_inc.result(), merged_inc.result())


@ddt.ddt
class DegradationComputationTestCase(test.TestCase):

    @ddt.data(
        ([], None, None, 0.0),
        ([30.0, 30.0, 30.0, 30.0], 30.0, 30.0, 0.0),
        ([45.0, 45.0, 45.0, 30.0], 30.0, 45.0, 50.0),
        ([15.0, 10.0, 20.0, 19.0], 10.0, 20.0, 100.0),
        ([30.0, 56.0, 90.0, 73.0], 30.0, 90.0, 200.0))
    @ddt.unpack
    def test_add(self, stream, min_value, max_value, result):
        comp = algo.DegradationComputation()
        for value in stream:
            comp.add(value)
        self.assertEqual(min_value, comp.min_value.result())
        self.assertEqual(max_value, comp.max_value.result())
        self.assertEqual(result, comp.result())

    @ddt.data(-10.0, -1.0, -1, 0.0, 0)
    def test_add_raise(self, value):
        comp = algo.DegradationComputation()
        self.assertRaises(ValueError, comp.add, value)

    @ddt.data(([39.0, 30.0, 32.0], [49.0, 40.0, 51.0], 30.0, 51.0, 70.0),
              ([31.0, 30.0, 32.0], [39.0, 45.0, 43.0], 30.0, 45.0, 50.0),
              ([], [31.0, 30.0, 45.0], 30.0, 45.0, 50.0),
              ([31.0, 30.0, 45.0], [], 30.0, 45.0, 50.0),
              ([], [], None, None, 0.0))
    @ddt.unpack
    def test_merge(self, stream1, stream2, min_value, max_value, result):
        comp1 = algo.DegradationComputation()
        for value in stream1:
            comp1.add(value)

        comp2 = algo.DegradationComputation()
        for value in stream2:
            comp2.add(value)

        comp1.merge(comp2)
        self.assertEqual(min_value, comp1.min_value.result())
        self.assertEqual(max_value, comp1.max_value.result())
        self.assertEqual(result, comp1.result())
