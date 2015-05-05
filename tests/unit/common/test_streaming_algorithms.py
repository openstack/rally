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

from rally.common import streaming_algorithms as algo
from rally import exceptions
from tests.unit import test


class MeanStreamingComputationTestCase(test.TestCase):

    def test_empty_stream(self):
        mean_computation = algo.MeanStreamingComputation()
        self.assertRaises(exceptions.RallyException, mean_computation.result)

    def test_one_value(self):
        mean_computation = algo.MeanStreamingComputation()
        mean_computation.add(10.0)
        self.assertEqual(10.0, mean_computation.result())

    def test_stream(self):
        stream = range(10)
        mean_computation = algo.MeanStreamingComputation()
        for value in stream:
            mean_computation.add(value)
        excepted_mean = float(sum(stream)) / len(stream)
        self.assertEqual(excepted_mean, mean_computation.result())


class StdDevStreamingComputationTestCase(test.TestCase):

    def test_empty_stream(self):
        std_computation = algo.StdDevStreamingComputation()
        self.assertRaises(exceptions.RallyException, std_computation.result)

    def test_one_value(self):
        std_computation = algo.StdDevStreamingComputation()
        std_computation.add(10.0)
        self.assertRaises(exceptions.RallyException, std_computation.result)

    def test_two_values(self):
        std_computation = algo.StdDevStreamingComputation()
        std_computation.add(10.0)
        std_computation.add(10.0)
        self.assertEqual(0.0, std_computation.result())

    def test_stream(self):
        stream = range(10)
        std_computation = algo.StdDevStreamingComputation()
        for value in stream:
            std_computation.add(value)
        mean = float(sum(stream)) / len(stream)
        excepted_std = math.sqrt(sum((x - mean) ** 2 for x in stream) /
                                 (len(stream) - 1))
        self.assertEqual(excepted_std, std_computation.result())
