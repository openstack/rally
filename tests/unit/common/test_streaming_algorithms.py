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

import ddt

import math

from rally.common import streaming_algorithms as algo
from rally import exceptions
from tests.unit import test


class MeanComputationTestCase(test.TestCase):

    def test_empty_stream(self):
        mean_computation = algo.MeanComputation()
        self.assertRaises(exceptions.RallyException, mean_computation.result)

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


class StdDevComputationTestCase(test.TestCase):

    def test_empty_stream(self):
        std_computation = algo.StdDevComputation()
        self.assertRaises(exceptions.RallyException, std_computation.result)

    def test_one_value(self):
        std_computation = algo.StdDevComputation()
        std_computation.add(10.0)
        self.assertRaises(exceptions.RallyException, std_computation.result)

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

    def test_result_raises(self):
        comp = algo.MinComputation()
        self.assertRaises(TypeError, comp.result, 1)
        self.assertRaises(ValueError, comp.result)


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

    def test_result_raises(self):
        comp = algo.MaxComputation()
        self.assertRaises(TypeError, comp.result, 1)
        self.assertRaises(ValueError, comp.result)


@ddt.ddt
class PercentileComputationTestCase(test.TestCase):

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
        {"stream": "mixed16", "percent": 25, "expected": 16.18},
        {"stream": "mixed16", "percent": 50, "expected": 38.94},
        {"stream": "mixed16", "percent": 90, "expected": 92.17},
        {"stream": "mixed50", "percent": 25, "expected": 23.1},
        {"stream": "mixed50", "percent": 50, "expected": 51.89},
        {"stream": "mixed50", "percent": 90, "expected": 85.265},
        {"stream": "mixed5000", "percent": 25, "expected": 25.03},
        {"stream": "mixed5000", "percent": 50, "expected": 51.89},
        {"stream": "mixed5000", "percent": 90, "expected": 85.265},
        {"stream": "range5000", "percent": 25, "expected": 1249.5},
        {"stream": "range5000", "percent": 50, "expected": 2499.5},
        {"stream": "range5000", "percent": 90, "expected": 4499.5})
    @ddt.unpack
    def test_add_and_result(self, percent, stream, expected):
        comp = algo.PercentileComputation(percent=percent)
        [comp.add(i) for i in getattr(self, stream)]
        self.assertEqual(expected, comp.result())

    def test_add_raises(self):
        comp = algo.PercentileComputation(50)
        self.assertRaises(TypeError, comp.add)
        self.assertRaises(TypeError, comp.add, None)
        self.assertRaises(TypeError, comp.add, "str")

    def test_result_raises(self):
        self.assertRaises(TypeError, algo.PercentileComputation)
        comp = algo.PercentileComputation(50)
        self.assertRaises(ValueError, comp.result)


class ProgressComputationTestCase(test.TestCase):

    def test___init__raises(self):
        self.assertRaises(TypeError, algo.ProgressComputation)
        self.assertRaises(TypeError, algo.ProgressComputation, None)
        self.assertRaises(ValueError, algo.ProgressComputation, "str")

    def test_add_and_result(self):
        comp = algo.ProgressComputation(42)
        self.assertEqual(0, comp.result())
        for expected_progress in (2.38, 4.76, 7.14, 9.52, 11.9, 14.29,
                                  16.67, 19.05, 21.43):
            comp.add(42)
            self.assertEqual(expected_progress, round(comp.result(), 2))

    def test_add_raises(self):
        comp = algo.ProgressComputation(42)
        [comp.add(123) for i in range(42)]
        self.assertRaises(RuntimeError, comp.add, None)
        self.assertRaises(RuntimeError, comp.add, 123)


class IncrementComputationTestCase(test.TestCase):

    def test_add_and_result(self):
        comp = algo.IncrementComputation()
        for i in range(1, 100):
            self.assertEqual(i - 1, comp.result())
            comp.add(42)
            self.assertEqual(i, comp.result())
