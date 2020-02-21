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
import os

import ddt

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

        for val in range(100):
            single_mean.add(val)

        means = [algo.MeanComputation()
                 for _ in range(10)]

        for idx, mean in enumerate(means):
            for val in range(idx * 10, (idx + 1) * 10):
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
        excepted_std = math.sqrt(
            sum((x - mean) ** 2 for x in stream) / (len(stream) - 1))
        self.assertEqual(excepted_std, std_computation.result())

    def test_merge(self):
        single_std = algo.StdDevComputation()

        for val in range(100):
            single_std.add(val)

        stds = [algo.StdDevComputation()
                for _ in range(10)]

        for idx, std in enumerate(stds):
            for val in range(idx * 10, (idx + 1) * 10):
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

        for val in range(100):
            single_min_algo.add(val)

        algos = [algo.MinComputation()
                 for _ in range(10)]

        for idx, min_algo in enumerate(algos):
            for val in range(idx * 10, (idx + 1) * 10):
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

        for val in range(100):
            single_max_algo.add(val)

        algos = [algo.MaxComputation()
                 for _ in range(10)]

        for idx, max_algo in enumerate(algos):
            for val in range(idx * 10, (idx + 1) * 10):
                max_algo.add(val)

        merged_max_algo = algos[0]
        for max_algo in algos[1:]:
            merged_max_algo.merge(max_algo)

        self.assertEqual(single_max_algo._value, merged_max_algo._value)
        self.assertEqual(single_max_algo.result(), merged_max_algo.result())


class IncrementComputationTestCase(test.TestCase):

    def test_add_and_result(self):
        comp = algo.IncrementComputation()
        for i in range(1, 100):
            self.assertEqual(i - 1, comp.result())
            comp.add(42)
            self.assertEqual(i, comp.result())

    def test_merge(self):
        single_inc = algo.IncrementComputation()

        for val in range(100):
            single_inc.add(val)

        incs = [algo.IncrementComputation()
                for _ in range(10)]

        for idx, inc in enumerate(incs):
            for val in range(idx * 10, (idx + 1) * 10):
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


class PointsSaverTestCase(test.TestCase):

    def test_add(self):
        points_saver = algo.PointsSaver(chunk_size=5)
        points = [i / 10.0 for i in range(1, 10)]

        for p in points[:4]:
            points_saver.add(p)
        # chunk should not be exceeded yet
        self.assertFalse(os.path.isfile(points_saver._filename))
        self.assertEqual(4, points_saver._current_chunk_size)
        self.assertEqual([0.1, 0.2, 0.3, 0.4], points_saver.result())

        for p in points[4:]:
            points_saver.add(p)

        self.assertEqual([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                         points_saver.result())

        self.assertTrue(os.path.isfile(points_saver._filename))
        with open(points_saver._filename) as f:
            self.assertEqual("  0.1 0.2 0.3 0.4 0.5", f.read())

    def test_merge(self):
        points_saver1 = algo.PointsSaver()
        points_saver1.add(1)
        points_saver2 = algo.PointsSaver()
        points_saver2.add(2)
        points_saver2.merge(points_saver1)

        self.assertEqual([2, 1], points_saver2.result())

    def test_reset(self):
        points_saver = algo.PointsSaver()
        points_saver.add(1)
        points_saver.reset()

        self.assertRaises(TypeError, points_saver.merge, algo.PointsSaver())
        self.assertRaises(TypeError, points_saver.add, 0)
        self.assertRaises(TypeError, points_saver.result)
