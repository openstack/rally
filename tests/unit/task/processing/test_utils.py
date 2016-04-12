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
