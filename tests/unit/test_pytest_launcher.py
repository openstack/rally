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

import os

import mock

from tests.ci import pytest_launcher
from tests.unit import test


PATH = "tests.ci.pytest_launcher"


class ExitError(Exception):
    pass


class PyTestLauncherTestCase(test.TestCase):
    def setUp(self):
        super(PyTestLauncherTestCase, self).setUp()

        sp_patcher = mock.patch("%s.subprocess" % PATH)
        self.sp = sp_patcher.start()
        self.addCleanup(sp_patcher.stop)

        exit_patcher = mock.patch("%s.exit" % PATH, side_effect=ExitError)
        self.exit = exit_patcher.start()
        self.addCleanup(exit_patcher.stop)

        os_patcher = mock.patch("%s.os" % PATH)
        self.os = os_patcher.start()
        self.addCleanup(os_patcher.stop)
        # emulate local run by default
        self.os.environ = {}
        self.os.path.join.side_effect = os.path.join
        self.os.path.abspath.side_effect = os.path.abspath
        self.os.path.expanduser.side_effect = os.path.expanduser

    def test_wrong_posargs(self):
        self.assertRaises(ExitError, pytest_launcher.main,
                          ["script name", "test_path",
                           "--posargs='posargs with spaces'"])

        self.assertFalse(self.sp.called)
        self.assertFalse(self.os.called)

    def test_parsing_path(self):
        def os_path_exists(path):
            dpath = "some/path/to/some/test"
            return dpath.startswith(path) or path == "%s/module.py" % dpath

        self.os.path.exists.side_effect = os_path_exists

        pytest_launcher.main(
            ["script_name", "some/path",
             "--posargs=some.path.to.some.test.module.TestCase.test"])

        expected_path = os.path.abspath(
            "some/path/to/some/test/module.py::TestCase::test")

        self.assertEqual(1, self.sp.check_call.call_count)
        call_args_obj = self.sp.check_call.call_args_list[0]
        call_args = call_args_obj[0]
        self.assertEqual(expected_path, call_args[0][-1])