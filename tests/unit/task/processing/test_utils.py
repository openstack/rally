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

import copy

import ddt

from rally.task.processing import utils
from tests.unit import test


@ddt.ddt
class GraphZipperTestCase(test.TestCase):

    @ddt.data({"data_stream": list(range(1, 11)), "zipped_size": 8,
               "expected": [[1, 1.2], [3, 2.4], [4, 3.6], [5, 4.8], [7, 6.2],
                            [8, 7.4], [9, 8.6], [10, 9.8]]},
              {"data_stream": [.005, .8, 22, .004, .7, 12, .5, .07, .02] * 10,
               "zipped_size": 8, "expected": [
                   [1, 3.769244444444445], [18, 4.706933333333334],
                   [29, 4.339911111111111], [40, 3.2279111111111116],
                   [52, 3.769244444444445], [63, 4.706933333333334],
                   [74, 4.339911111111111], [90, 3.2279111111111116]]},
              {"data_stream": list(range(1, 100)), "zipped_size": 1000,
               "expected": [[i, i] for i in range(1, 100)]},
              {"data_stream": [1, 4, 11, None, 42], "zipped_size": 1000,
               "expected": [[1, 1], [2, 4], [3, 11], [4, 0], [5, 42]]})
    @ddt.unpack
    def test_add_point_and_get_zipped_graph(self, data_stream=None,
                                            zipped_size=None, expected=None):
        merger = utils.GraphZipper(len(data_stream), zipped_size)
        [merger.add_point(value) for value in data_stream]
        self.assertEqual(expected, merger.get_zipped_graph())

    def test_add_point_raises(self):
        merger = utils.GraphZipper(10, 8)
        self.assertRaises(TypeError, merger.add_point)
        [merger.add_point(1) for value in range(10)]
        self.assertRaises(RuntimeError, merger.add_point, 1)


@ddt.ddt
class PercentileTestCase(test.TestCase):

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
    mixed50000 = mixed50 * 1000
    range5000 = list(range(5000))

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
        {"stream": "mixed50000", "percent": 0.25, "expected":
            25.03},
        {"stream": "mixed50000", "percent": 0.50, "expected": 51.89},
        {"stream": "mixed50000", "percent": 0.90, "expected":
            82.81299999999108},
        {"stream": "range5000", "percent": 0.25, "expected": 1249.75},
        {"stream": "range5000", "percent": 0.50, "expected": 2499.5},
        {"stream": "range5000", "percent": 0.90, "expected": 4499.1})
    @ddt.unpack
    def test_add_and_result(self, percent, stream, expected):
        stream = copy.copy(getattr(self, stream))
        self.assertEqual(expected,
                         utils.percentile(percent=percent, points=stream))

    def test_result_empty(self):
        self.assertIsNone(utils.percentile([], percent=0.50,
                                           ignore_sorting=True))
