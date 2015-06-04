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
#

import mock

from rally.common import costilius
from rally import exceptions
from tests.unit import test


PATH = "rally.common.costilius"


class SPCheckCallTestCase(test.TestCase):

    @mock.patch("%s.subprocess" % PATH)
    @mock.patch("%s.is_py26" % PATH, return_value=True)
    def test_simulation_of_py26_env(self, mock_is_py26, mock_subprocess):
        output = "output"
        process = mock.MagicMock()
        process.communicate.return_value = (output, "unused_err")
        process.poll.return_value = None

        mock_subprocess.Popen.return_value = process
        some_args = (1, 2)
        some_kwargs = {"a": 2}

        self.assertEqual(output, costilius.sp_check_output(*some_args,
                                                           **some_kwargs))

        mock_subprocess.Popen.assert_called_once_with(
            stdout=mock_subprocess.PIPE, *some_args, **some_kwargs)
        self.assertFalse(mock_subprocess.check_output.called)

    @mock.patch("%s.subprocess" % PATH)
    @mock.patch("%s.is_py26" % PATH, return_value=False)
    def test_simulation_of_any_not_py26_env(self, mock_is_py26,
                                            mock_subprocess):
        output = "output"
        mock_subprocess.check_output.return_value = output

        some_args = (1, 2)
        some_kwargs = {"a": 2}

        self.assertEqual(output, costilius.sp_check_output(*some_args,
                                                           **some_kwargs))

        mock_subprocess.check_output.assert_called_once_with(
            *some_args, **some_kwargs)
        self.assertFalse(mock_subprocess.Popen.called)


class GetInterpreterTestCase(test.TestCase):
    def test_wrong_format(self):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          costilius.get_interpreter, "something_bad")

    @mock.patch("%s.spawn" % PATH)
    @mock.patch("%s.sp_check_output" % PATH)
    @mock.patch("%s.os.path.isfile" % PATH)
    @mock.patch("%s.os.environ" % PATH)
    def test_found_correct_python_interpreter_with_distutils(
            self, mock_environ, mock_isfile, mock_sp_check_output, mock_spawn):
        vers = (2, 7)
        interpreter = "something"
        mock_spawn.find_executable.return_value = interpreter

        self.assertEqual(interpreter, costilius.get_interpreter(vers))
        self.assertFalse(mock_environ.called)
        self.assertFalse(mock_isfile.called)
        self.assertFalse(mock_sp_check_output.called)

    @mock.patch("%s.spawn" % PATH)
    @mock.patch("%s.sp_check_output" % PATH)
    @mock.patch("%s.os.path.isfile" % PATH, return_value=True)
    @mock.patch("%s.os.environ" % PATH)
    def test_found_correct_python_interpreter_without_distutils(
            self, mock_environ, mock_isfile, mock_sp_check_output, mock_spawn):
        vers = (2, 7)
        paths = ["one_path", "second_path"]
        mock_environ.get.return_value = ":".join(paths)
        mock_sp_check_output.return_value = "%s\n" % str(vers)
        mock_spawn.find_executable.return_value = None

        found_interpreter = costilius.get_interpreter(vers)

        self.assertEqual(1, mock_sp_check_output.call_count)
        self.assertIn(
            found_interpreter, ["%s/%s" % (f, "python2.7") for f in paths])
