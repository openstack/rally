# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013: Mirantis Inc.
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

"""Tests for utils."""
import mock

from rally.benchmark import utils
from rally import test


def test_dummy():
    pass


def test_dummy_2():
    pass


class UtilsTestCase(test.NoDBTestCase):
    def setUp(self):
        super(UtilsTestCase, self).setUp()
        self.fc = mock.patch('fuel_health.cleanup.cleanup')
        self.fc.start()

    def tearDown(self):
        self.fc.stop()
        super(UtilsTestCase, self).tearDown()

    def test_running_test(self):
        tester = utils.Tester('rally/benchmark/test.conf')
        test = ['./tests/benchmark/test_utils.py', '-k', 'test_dummy']
        for result in tester.run(test, times=1, concurrent=1).itervalues():
            self.assertEqual(result['status'], 0)
        for result in tester.run(test, times=3, concurrent=2).itervalues():
            self.assertEqual(result['status'], 0)
        for result in tester.run(test, times=2, concurrent=3).itervalues():
            self.assertEqual(result['status'], 0)

    def test_running_multiple_tests(self):
        tester = utils.Tester('rally/benchmark/test.conf')
        tests = [['./tests/benchmark/test_utils.py', '-k', 'test_dummy'],
                 ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_2']]
        for test_results in tester.run_all(tests):
            for result in test_results.itervalues():
                self.assertEqual(result['status'], 0)
