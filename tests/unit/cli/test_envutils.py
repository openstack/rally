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

import os
from unittest import mock

from rally import exceptions
from rally.cli import envutils
from tests.unit import test


class EnvUtilsTestCase(test.TestCase):

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch.dict("os.environ", values={}, clear=True)
    def test_load_env_vile(self, mock_exists):
        file_data = "FAKE_ENV=fake_env\n"
        with mock.patch("rally.cli.envutils.open", mock.mock_open(
                read_data=file_data), create=True) as mock_file:
            envutils._load_env_file("path_to_file")
            self.assertIn("FAKE_ENV", os.environ)
            mock_file.return_value.readlines.assert_called_once_with()

    @mock.patch("os.path.exists", return_value=True)
    def test_update_env_file(self, mock_exists):
        file_data = "FAKE_ENV=old_value\nFAKE_ENV2=any\n"
        with mock.patch("rally.cli.envutils.open", mock.mock_open(
                read_data=file_data), create=True) as mock_file:
            envutils._update_env_file("path_to_file", "FAKE_ENV", "new_value")
            calls = [mock.call("FAKE_ENV2=any\n"), mock.call(
                "FAKE_ENV=new_value")]
            mock_file.return_value.readlines.assert_called_once_with()
            mock_file.return_value.write.assert_has_calls(calls)

    @mock.patch.dict("os.environ", values={}, clear=True)
    @mock.patch("rally.cli.envutils._read_env_file")
    def test_load_globals(self, mock__read_env_file):
        mock__read_env_file.return_value = ["RALLY_TASK=t1\n",
                                            "RALLY_DEPLOYMENT=d1\n"]
        envutils.load_globals()
        self.assertEqual("t1", os.environ["RALLY_TASK"])
        self.assertEqual("d1", os.environ["RALLY_DEPLOYMENT"])
        # RALLY_ENV was unset, so it is filled from the legacy RALLY_DEPLOYMENT
        self.assertEqual("d1", os.environ["RALLY_ENV"])

    @mock.patch.dict("os.environ", values={"RALLY_ENV": "real"}, clear=True)
    @mock.patch("rally.cli.envutils._read_env_file")
    def test_load_globals_env_wins_over_file(self, mock__read_env_file):
        mock__read_env_file.return_value = ["RALLY_ENV=from_file\n"]
        envutils.load_globals()
        # A real environment variable takes precedence over the file.
        self.assertEqual("real", os.environ["RALLY_ENV"])

    @mock.patch.dict(os.environ,
                     values={envutils.ENV_DEPLOYMENT: "my_deployment_id"},
                     clear=True)
    def test_get_deployment_id_in_env(self):
        deployment_id = envutils.get_global(envutils.ENV_DEPLOYMENT)
        self.assertEqual("my_deployment_id", deployment_id)

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils._load_env_file")
    def test_get_deployment_id_with_exception(self, mock__load_env_file):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          envutils.get_global, envutils.ENV_DEPLOYMENT, True)
        mock__load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils._load_env_file")
    def test_get_deployment_id_with_none(self, mock__load_env_file):
        self.assertIsNone(envutils.get_global(envutils.ENV_DEPLOYMENT))
        mock__load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ, values={envutils.ENV_TASK: "my_task_id"},
                     clear=True)
    def test_get_task_id_in_env(self):
        self.assertEqual("my_task_id", envutils.get_global(envutils.ENV_TASK))

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils._load_env_file")
    def test_get_task_id_with_exception(self, mock__load_env_file):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          envutils.get_global, envutils.ENV_TASK, True)
        mock__load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils._load_env_file")
    def test_get_task_id_with_none(self, mock__load_env_file):
        self.assertIsNone(envutils.get_global("RALLY_TASK"))
        mock__load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ,
                     values={envutils.ENV_DEPLOYMENT: "test_deployment_id"},
                     clear=True)
    @mock.patch("os.path.exists")
    @mock.patch("rally.cli.envutils._update_env_file",
                return_value=True)
    def test_clear_global(self, mock__update_env_file, mock_path_exists):
        envutils.clear_global(envutils.ENV_DEPLOYMENT)
        mock__update_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"), envutils.ENV_DEPLOYMENT, "\n")
        self.assertEqual({}, os.environ)

    @mock.patch.dict(os.environ,
                     values={envutils.ENV_DEPLOYMENT: "test_deployment_id",
                             envutils.ENV_TASK: "test_task_id"},
                     clear=True)
    @mock.patch("os.path.exists")
    @mock.patch("rally.cli.envutils._update_env_file",
                return_value=True)
    def test_clear_env(self, mock__update_env_file, mock_path_exists):
        envutils.clear_env()
        self.assertEqual({}, os.environ)
