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

import errno
import subprocess

import mock

from rally.verification import utils
from tests.unit import test


class SomeException(OSError):
    def __init__(self, errno):
        super(SomeException, self).__init__()
        self.errno = errno


class UtilsTestCase(test.TestCase):
    @mock.patch("rally.verification.utils.os")
    def test_create_dir(self, mock_os):
        utils.create_dir("some")
        mock_os.makedirs.assert_called_once_with("some")

        # directory exists
        mock_os.makedirs.reset_mock()
        mock_os.makedirs.side_effect = SomeException(errno=errno.EEXIST)
        mock_os.path.isdir.return_value = True
        utils.create_dir("some")
        mock_os.makedirs.assert_called_once_with("some")

        # directory doesn't exist
        mock_os.makedirs.reset_mock()
        mock_os.makedirs.side_effect = SomeException(errno=666)
        self.assertRaises(SomeException, utils.create_dir, "some")
        mock_os.makedirs.assert_called_once_with("some")

        mock_os.makedirs.reset_mock()
        mock_os.makedirs.side_effect = SomeException(errno=errno.EEXIST)
        mock_os.path.isdir.return_value = False
        self.assertRaises(SomeException, utils.create_dir, "some")
        mock_os.makedirs.assert_called_once_with("some")

    @mock.patch("rally.verification.utils.encodeutils")
    @mock.patch("rally.verification.utils.LOG")
    @mock.patch("rally.verification.utils.subprocess.check_output")
    def test_check_output(self, mock_check_output, mock_log,
                          mock_encodeutils):

        self.assertEqual(mock_check_output.return_value,
                         utils.check_output())
        self.assertFalse(mock_log.error.called)

        mock_check_output.side_effect = subprocess.CalledProcessError(1, None)
        self.assertRaises(subprocess.CalledProcessError, utils.check_output)
        self.assertEqual(2, mock_log.error.call_count)

        mock_log.error.reset_mock()

        msg = "bla bla bla"
        self.assertRaises(subprocess.CalledProcessError, utils.check_output,
                          msg_on_err=msg)
        self.assertEqual(3, mock_log.error.call_count)
        mock_log.error.assert_any_call(msg)
