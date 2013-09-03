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

"""Tests for benchmarks."""
import mock

from rally.benchmark import benchmark
from rally import test


def test_dummy():
    pass


class BenchmarkTestCase(test.NoDBTestCase):
    def setUp(self):
        super(BenchmarkTestCase, self).setUp()
        self.fc = mock.patch('fuel_health.cleanup.cleanup')
        self.fc.start()

    def tearDown(self):
        self.fc.stop()
        super(BenchmarkTestCase, self).tearDown()

    def test_running_test(self):
        tester = benchmark.Tester('rally/benchmark/test.conf')
        tester.tests['test'] = ['./tests/benchmark/test_benchmark.py',
                                '-k', 'test_dummy']
        for result in tester.run('test', 3).itervalues():
            self.assertEqual(result['status'], 0)
