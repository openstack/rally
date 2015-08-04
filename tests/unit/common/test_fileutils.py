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

import mock

from rally.common import fileutils
from tests.unit import test


class FileUtilsTestCase(test.TestCase):

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch.dict("os.environ", values={}, clear=True)
    def test_load_env_vile(self, mock_exists):
        file_data = ["FAKE_ENV=fake_env\n"]
        with mock.patch("rally.common.fileutils.open", mock.mock_open(
                read_data=file_data), create=True) as mock_file:
            mock_file.return_value.readlines.return_value = file_data
            fileutils.load_env_file("path_to_file")
            self.assertIn("FAKE_ENV", os.environ)
            mock_file.return_value.readlines.assert_called_once_with()

    @mock.patch("os.path.exists", return_value=True)
    def test_update_env_file(self, mock_exists):
        file_data = ["FAKE_ENV=old_value\n", "FAKE_ENV2=any\n"]
        with mock.patch("rally.common.fileutils.open", mock.mock_open(
                read_data=file_data), create=True) as mock_file:
            mock_file.return_value.readlines.return_value = file_data
            fileutils.update_env_file("path_to_file", "FAKE_ENV", "new_value")
            calls = [mock.call("FAKE_ENV2=any\n"), mock.call(
                "FAKE_ENV=new_value")]
            mock_file.return_value.readlines.assert_called_once_with()
            mock_file.return_value.write.assert_has_calls(calls)


class PackDirTestCase(test.TestCase):

    @mock.patch("os.walk")
    @mock.patch("zipfile.ZipFile")
    def test_pack_dir(self, mock_zip_file, mock_walk):
        mock_walk.side_effect = [
            [("foo_root", [], ["file1", "file2", "file3"])]]
        fileutils.pack_dir("rally-jobs/extra/murano/HelloReporter",
                           "fake_dir/package.zip")
        mock_zip_file.assert_called_once_with("fake_dir/package.zip",
                                              mode="w")
        mock_walk.assert_called_once_with(
            "rally-jobs/extra/murano/HelloReporter")
        mock_zip_file.return_value.assert_has_calls(
            [mock.call.write("foo_root/file1", "../../../../foo_root/file1"),
             mock.call.write("foo_root/file2", "../../../../foo_root/file2"),
             mock.call.write("foo_root/file3", "../../../../foo_root/file3"),
             mock.call.close()])
