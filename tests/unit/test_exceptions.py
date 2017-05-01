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

import mock

from rally import exceptions
from tests.unit import test


class ExceptionTestCase(test.TestCase):

    @mock.patch("rally.exceptions._exception_map")
    def test_find_exception(self, mock__exception_map):
        mock_response = mock.Mock()
        exc_class = mock.Mock()
        mock__exception_map.get.return_value = exc_class
        mock_response.json.return_value = {
            "error": {"args": "args", "msg": "msg"}
        }

        exc_instance = exceptions.find_exception(mock_response)
        self.assertEqual(exc_instance, exc_class.return_value)

        mock__exception_map.reset_mock()
        exc_class.reset_mock()
        mock_response.reset_mock()
        mock_response.json.return_value = {
            "error": {"args": None, "msg": "msg"}
        }
        exc_instance = exceptions.find_exception(mock_response)
        self.assertEqual(exc_instance, exc_class.return_value)

    def test_make_exception(self):
        exc = exceptions.RallyException("exc")
        self.assertEqual(exc, exceptions.make_exception(exc))

        mock_exc = mock.Mock()
        self.assertIsInstance(exceptions.make_exception(mock_exc),
                              exceptions.RallyException)
