#
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

from rally.common.i18n import _
from rally.common import logging
from tests.unit import test


class LogTestCase(test.TestCase):

    def test_log_task_wrapper(self):
        mock_log = mock.MagicMock()
        msg = "test %(a)s %(b)s"

        class TaskLog(object):

            def __init__(self):
                self.task = {"uuid": "some_uuid"}

            @logging.log_task_wrapper(mock_log, msg, a=10, b=20)
            def some_method(self, x, y):
                return x + y

        t = TaskLog()
        self.assertEqual(t.some_method.__name__, "some_method")
        self.assertEqual(t.some_method(2, 2), 4)
        params = {"msg": msg % {"a": 10, "b": 20}, "uuid": t.task["uuid"]}
        expected = [
            mock.call(_("Task %(uuid)s | Starting:  %(msg)s") % params),
            mock.call(_("Task %(uuid)s | Completed: %(msg)s") % params)
        ]
        self.assertEqual(mock_log.mock_calls, expected)

    def test_log_deprecated(self):
        mock_log = mock.MagicMock()

        @logging.log_deprecated("some alternative", "0.0.1", mock_log)
        def some_method(x, y):
            return x + y

        self.assertEqual(some_method(2, 2), 4)
        mock_log.assert_called_once_with("'some_method' is deprecated in "
                                         "Rally v0.0.1: some alternative")

    def test_log_deprecated_args(self):
        mock_log = mock.MagicMock()

        @logging.log_deprecated_args("Deprecated test", "0.0.1", ("z",),
                                     mock_log, once=True)
        def some_method(x, y, z):
            return x + y + z

        self.assertEqual(some_method(2, 2, z=3), 7)
        mock_log.assert_called_once_with(
            "Deprecated test (args `z' deprecated in Rally v0.0.1)")

        mock_log.reset_mock()
        self.assertEqual(some_method(2, 2, z=3), 7)
        self.assertFalse(mock_log.called)

        @logging.log_deprecated_args("Deprecated test", "0.0.1", ("z",),
                                     mock_log, once=False)
        def some_method(x, y, z):
            return x + y + z

        self.assertEqual(some_method(2, 2, z=3), 7)
        mock_log.assert_called_once_with(
            "Deprecated test (args `z' deprecated in Rally v0.0.1)")

        mock_log.reset_mock()
        self.assertEqual(some_method(2, 2, z=3), 7)
        mock_log.assert_called_once_with(
            "Deprecated test (args `z' deprecated in Rally v0.0.1)")
