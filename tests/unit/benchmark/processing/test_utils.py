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

from rally.benchmark.processing import utils
from rally import exceptions
from tests.unit import test


class MathTestCase(test.TestCase):

    def test_percentile(self):
        lst = range(1, 101)
        result = utils.percentile(lst, 0.1)
        self.assertEqual(result, 10.9)

    def test_percentile_value_none(self):
        result = utils.percentile(None, 0.1)
        self.assertEqual(result, None)

    def test_percentile_equal(self):
        lst = range(1, 101)
        result = utils.percentile(lst, 1)
        self.assertEqual(result, 100)

    def test_mean(self):
        lst = range(1, 100)
        result = utils.mean(lst)
        self.assertEqual(result, 50.0)

    def test_mean_empty_list(self):
        lst = []
        self.assertRaises(exceptions.InvalidArgumentsException,
                          utils.mean, lst)

    def _compare_items_lists(self, list1, list2):
        """Items lists comparison, compatible with Python 2.6/2.7.

        :param list1: items list [(a1, b1), (a2, b2) ...]
        :param list2: items list [(a1, b1), (a2, b2) ...]
        """
        compare_float = lambda f1, f2: abs(f2 - f2) < 0.1
        for a, b in zip(list1, list2):
            a1, a2, b1, b2 = (a + b)
            self.assertEqual(a1, b1)
            if type(a2) is float:
                # Float representation is defferent in Python 2.6/2.7,
                # so we need to be sure that values are close to each other
                self.assertTrue(compare_float(a2, b2))
            else:
                self.assertEqual(a2, b2)

    def test_compress(self):
        data64 = range(64)
        data4 = [4, 2, 1, 3]
        mixed = [2, "5", None, 0.5]
        alt_normalize = str
        alt_merge = lambda a, b: str(a) + str(b)
        compress = lambda lst: [(k + 1, float(v)) for k, v in enumerate(lst)]

        # Long list
        self.assertEqual(utils.compress(data64), compress(data64))
        self._compare_items_lists(
            utils.compress(data64, limit=4),
            [(17, 15.0), (33, 31.01), (49, 47.0), (64, 62.0)])
        self.assertEqual(
            utils.compress(data64, limit=4,
                           normalize=alt_normalize, merge=alt_merge),
            [(17, '012345678910111213141516'),
             (33, '17181920212223242526272829303132'),
             (49, '33343536373839404142434445464748'),
             (64, '495051525354555657585960616263')])

        # Short list
        self.assertEqual(utils.compress(data4, limit=2),
                         [(3, 2.0), (4, 3.0)])
        self.assertEqual(utils.compress(data4, normalize=alt_normalize),
                         [(1, '4'), (2, '2'), (3, '1'), (4, '3')])

        # List with mixed data types
        self.assertEqual(utils.compress(mixed),
                         [(1, 2.0), (2, 5.0), (3, 0.0), (4, 0.5)])
        self.assertEqual(utils.compress(mixed, normalize=str),
                         [(1, '2'), (2, '5'), (3, 'None'), (4, '0.5')])
        self.assertRaises(TypeError, utils.compress, mixed, normalize=int)
        self.assertEqual(
            utils.compress(mixed, normalize=alt_normalize, merge=alt_merge),
            [(1, '2'), (2, '5'), (3, 'None'), (4, '0.5')])


class AtomicActionsDataTestCase(test.TestCase):

    def test_get_atomic_actions_data(self):
        raw_data = [
            {
                "error": [],
                "duration": 3,
                "atomic_actions": {
                    "action1": 1,
                    "action2": 2
                }
            },
            {
                "error": ["some", "error", "occurred"],
                "duration": 1.9,
                "atomic_actions": {
                    "action1": 0.5,
                    "action2": 1.4
                }
            },
            {
                "error": [],
                "duration": 8,
                "atomic_actions": {
                    "action1": 4,
                    "action2": 4
                }
            }
        ]

        atomic_actions_data = {
            "action1": [1, 0.5, 4],
            "action2": [2, 1.4, 4],
            "total": [3, 8]
        }

        output = utils.get_atomic_actions_data(raw_data)
        self.assertEqual(output, atomic_actions_data)
