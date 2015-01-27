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


import mock

from rally.benchmark.scenarios.dummy import dummy
from tests.unit import test


class DummyTestCase(test.TestCase):

    @mock.patch("rally.benchmark.scenarios.dummy.dummy.time")
    def test_dummy(self, mock_sleep):
        scenario = dummy.Dummy()
        scenario.sleep_between = mock.MagicMock()
        scenario.dummy()
        self.assertFalse(mock_sleep.sleep.called)

        scenario.dummy(sleep=10)
        mock_sleep.sleep.assert_called_once_with(10)

    def test_dummy_exception(self):
        scenario = dummy.Dummy()

        size_of_message = 5
        self.assertRaises(dummy.DummyScenarioException,
                          scenario.dummy_exception, size_of_message)

    def test_dummy_exception_probability(self):
        scenario = dummy.Dummy()

        # should not raise an exception as probability is 0
        for i in range(100):
            scenario.dummy_exception_probability(exception_probability=0)

        # should always raise an exception as probability is 1
        for i in range(100):
            self.assertRaises(dummy.DummyScenarioException,
                              scenario.dummy_exception_probability,
                              exception_probability=1)

    def test_dummy_dummy_with_scenario_output(self):
        scenario = dummy.Dummy()
        result = scenario.dummy_with_scenario_output()
        self.assertEqual(result['errors'], "")
        # Since the data is generated in random,
        # checking for not None
        self.assertNotEqual(result['data'], None)

    def test_dummy_random_fail_in_atomic(self):
        scenario = dummy.Dummy()

        for i in range(10):
            scenario.dummy_random_fail_in_atomic(exception_probability=0)

        for i in range(10):
            self.assertRaises(KeyError,
                              scenario.dummy_random_fail_in_atomic,
                              exception_probability=1)
