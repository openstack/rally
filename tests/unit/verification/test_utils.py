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

import subprocess

import mock
from six.moves import configparser

from rally.verification import utils
from tests.unit import test


class UtilsTestCase(test.TestCase):

    @mock.patch("rally.verification.utils.os.makedirs")
    @mock.patch("rally.verification.utils.os.path.isdir",
                side_effect=[False, True])
    def test_create_dir(self, mock_isdir, mock_makedirs):
        utils.create_dir("some")
        mock_makedirs.assert_called_once_with("some")

        mock_makedirs.reset_mock()
        utils.create_dir("some")
        mock_makedirs.assert_not_called()

    @mock.patch("rally.verification.utils.encodeutils")
    @mock.patch("rally.verification.utils.LOG")
    @mock.patch("rally.verification.utils.subprocess.check_output")
    def test_check_output(self, mock_check_output, mock_log,
                          mock_encodeutils):

        self.assertEqual(mock_encodeutils.safe_decode.return_value,
                         utils.check_output())
        self.assertFalse(mock_log.error.called)
        mock_encodeutils.safe_decode.assert_called_once_with(
            mock_check_output.return_value)

        mock_check_output.side_effect = subprocess.CalledProcessError(1, None)
        self.assertRaises(subprocess.CalledProcessError, utils.check_output)
        self.assertEqual(2, mock_log.error.call_count)

        mock_log.error.reset_mock()

        msg = "bla bla bla"
        self.assertRaises(subprocess.CalledProcessError, utils.check_output,
                          msg_on_err=msg)
        self.assertEqual(3, mock_log.error.call_count)
        mock_log.error.assert_any_call(msg)

    @mock.patch("rally.verification.utils.six.StringIO")
    @mock.patch("rally.verification.utils.add_extra_options")
    @mock.patch("rally.verification.utils.configparser.ConfigParser")
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    def test_extend_configfile(self, mock_open, mock_config_parser,
                               mock_add_extra_options, mock_string_io):
        extra_options = mock.Mock()
        conf_path = "/path/to/fake/conf"

        utils.extend_configfile(extra_options, conf_path)

        conf = mock_config_parser.return_value
        conf.read.assert_called_once_with(conf_path)

        mock_add_extra_options.assert_called_once_with(extra_options, conf)
        conf = mock_add_extra_options.return_value
        conf.write.assert_has_calls([mock.call(mock_open.side_effect()),
                                     mock.call(mock_string_io.return_value)])
        mock_string_io.return_value.getvalue.assert_called_once_with()

    def test_add_extra_options(self):
        conf = configparser.ConfigParser()
        extra_options = {"section": {"foo": "bar"},
                         "section2": {"option": "value"}}

        conf = utils.add_extra_options(extra_options, conf)

        expected = {"section": ("foo", "bar"), "section2": ("option", "value")}
        for section, option in expected.items():
            result = conf.items(section)
            self.assertIn(option, result)
