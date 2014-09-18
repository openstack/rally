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

from rally.hacking import checks
from tests import test


class HackingTestCase(test.TestCase):

    def test__parse_assert_mock_str(self):
        pos, method, obj = checks._parse_assert_mock_str(
            "mock_clients.fake().quotas.delete.assert_called_once()")
        self.assertEqual("assert_called_once", method)
        self.assertEqual("mock_clients.fake().quotas.delete", obj)

    def test__parse_assert_mock_str_no_assert(self):
        pos, method, obj = checks._parse_assert_mock_str(
            "mock_clients.fake().quotas.delete.")
        self.assertIsNone(pos)
        self.assertIsNone(method)
        self.assertIsNone(obj)

    def test_correct_usage_of_assert_from_mock(self):
        correct_method_names = ["assert_any_call", "assert_called_once_with",
                                "assert_called_with", "assert_has_calls"]
        for name in correct_method_names:
            self.assertEqual(0, len(
                list(checks.check_assert_methods_from_mock(
                    'some_mock.%s(asd)' % name, 'tests/fake/test'))))

    def test_wrong_usage_of_broad_assert_from_mock(self):
        fake_method = 'rtfm.assert_something()'

        actual_number, actual_msg = next(checks.check_assert_methods_from_mock(
            fake_method, 'tests/fake/test'))
        self.assertEqual(4, actual_number)
        self.assertTrue(actual_msg.startswith('N301'))

    def test_wrong_usage_of_assert_called_from_mock(self):
        fake_method = 'rtfm.assert_called()'

        actual_number, actual_msg = next(checks.check_assert_methods_from_mock(
            fake_method, 'tests/fake/test'))
        self.assertEqual(4, actual_number)
        self.assertTrue(actual_msg.startswith('N302'))

    def test_wrong_usage_of_assert_called_once_from_mock(self):
        fake_method = 'rtfm.assert_called_once()'

        actual_number, actual_msg = next(checks.check_assert_methods_from_mock(
            fake_method, 'tests/fake/test'))
        self.assertEqual(4, actual_number)
        self.assertTrue(actual_msg.startswith('N303'))
