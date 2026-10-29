# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

from unittest import mock

import requests

from rally import exceptions
from rally.plugins.task import types
from tests.unit import test


class PathOrUrlTestCase(test.TestCase):

    @mock.patch("os.path.isfile")
    @mock.patch("requests.head")
    def test_preprocess_file(self, mock_requests_head, mock_isfile):
        mock_isfile.return_value = True
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        path = rt.pre_process(
            resource_spec="fake_path", config={}, output_type=None)
        self.assertEqual("fake_path", path)

    @mock.patch("os.path.isfile")
    @mock.patch("requests.head")
    def test_preprocess_bogus(self, mock_requests_head, mock_isfile):
        mock_isfile.return_value = False
        mock_requests_head.return_value = mock.Mock(status_code=500)
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        self.assertRaises(
            exceptions.InvalidScenarioArgument, rt.pre_process,
            resource_spec="fake_path", config={}, output_type=None)
        mock_requests_head.assert_called_once_with(
            "fake_path", verify=False, allow_redirects=True)

    @mock.patch("requests.get")
    @mock.patch("os.path.isfile")
    @mock.patch("requests.head")
    def test_preprocess_url(self, mock_requests_head, mock_isfile, mock_get):
        mock_isfile.return_value = False
        mock_requests_head.return_value = mock.Mock(status_code=200)
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        path = rt.pre_process(
            resource_spec="fake_url", config={}, output_type=None)
        self.assertEqual("fake_url", path)
        mock_requests_head.assert_called_once_with(
            "fake_url", verify=False, allow_redirects=True)
        mock_requests_head.return_value.close.assert_called_once_with()
        mock_get.assert_not_called()

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("requests.get")
    @mock.patch("requests.head")
    def test_preprocess_head_rejected(self, mock_head, mock_get, mock_isfile):
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        for status in (403, 405):
            with self.subTest(status=status):
                mock_head.reset_mock()
                mock_get.reset_mock()
                mock_head.return_value.status_code = status
                mock_get.return_value.status_code = 200
                self.assertEqual("fake_url", rt.pre_process(
                    resource_spec="fake_url", config={}, output_type=None))
                mock_head.assert_called_once_with(
                    "fake_url", verify=False, allow_redirects=True)
                mock_get.assert_called_once_with(
                    "fake_url", verify=False, allow_redirects=True,
                    stream=True)
                mock_head.return_value.close.assert_called_once_with()
                mock_get.return_value.close.assert_called_once_with()

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("requests.get")
    @mock.patch("requests.head")
    def test_preprocess_get_rejected(self, mock_head, mock_get, mock_isfile):
        mock_head.return_value.status_code = 403
        mock_get.return_value.status_code = 401
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        error = self.assertRaises(
            exceptions.InvalidScenarioArgument, rt.pre_process,
            resource_spec="fake_url", config={}, output_type=None)
        self.assertIn("code 401", str(error))
        mock_get.assert_called_once_with(
            "fake_url", verify=False, allow_redirects=True, stream=True)
        mock_head.return_value.close.assert_called_once_with()
        mock_get.return_value.close.assert_called_once_with()

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("requests.get", side_effect=requests.Timeout("timed out"))
    @mock.patch("requests.head")
    def test_preprocess_get_exception(self, mock_head, mock_get, mock_isfile):
        mock_head.return_value.status_code = 403
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        error = self.assertRaises(
            exceptions.InvalidScenarioArgument, rt.pre_process,
            resource_spec="fake_url", config={}, output_type=None)
        self.assertIn("timed out", str(error))
        mock_head.return_value.close.assert_called_once_with()
        mock_get.assert_called_once()

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("requests.get")
    @mock.patch("requests.head")
    def test_preprocess_server_error_does_not_retry(
            self, mock_head, mock_get, mock_isfile):
        mock_head.return_value.status_code = 500
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        self.assertRaises(
            exceptions.InvalidScenarioArgument, rt.pre_process,
            resource_spec="fake_url", config={}, output_type=None)
        mock_head.return_value.close.assert_called_once_with()
        mock_get.assert_not_called()

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("requests.get")
    @mock.patch("requests.head", side_effect=requests.Timeout("timed out"))
    def test_preprocess_head_exception(self, mock_head, mock_get, mock_isfile):
        rt = types.PathOrUrl(context={}, cache={}, scenario_cls=mock.Mock())
        error = self.assertRaises(
            exceptions.InvalidScenarioArgument, rt.pre_process,
            resource_spec="fake_url", config={}, output_type=None)
        self.assertIn("timed out", str(error))
        mock_get.assert_not_called()


class FileTypeTestCase(test.TestCase):

    @mock.patch("builtins.open",
                side_effect=mock.mock_open(read_data="file_context"),
                create=True)
    def test_preprocess_by_path(self, mock_open):
        rt = types.FileType(context={}, cache={}, scenario_cls=mock.Mock())
        file_context = rt.pre_process(
            resource_spec="file.yaml", config={}, output_type=None)
        self.assertEqual("file_context", file_context)

    @mock.patch("builtins.open", side_effect=IOError, create=True)
    def test_preprocess_by_path_no_match(self, mock_open):
        rt = types.FileType(context={}, cache={}, scenario_cls=mock.Mock())
        self.assertRaises(
            IOError, rt.pre_process,
            resource_spec="nonexistant.yaml", config={}, output_type=None)


class FileTypeDictTestCase(test.TestCase):

    @mock.patch("builtins.open",
                side_effect=mock.mock_open(read_data="file_context"),
                create=True)
    def test_preprocess_by_path(self, mock_open):
        rt = types.FileTypeDict(context={}, cache={}, scenario_cls=mock.Mock())
        file_context = rt.pre_process(
            resource_spec=["file.yaml"], config={}, output_type=None)
        self.assertEqual({"file.yaml": "file_context"}, file_context)

    @mock.patch("builtins.open", side_effect=IOError, create=True)
    def test_preprocess_by_path_no_match(self, mock_open):
        rt = types.FileTypeDict(context={}, cache={}, scenario_cls=mock.Mock())
        self.assertRaises(
            IOError, rt.pre_process,
            resource_spec=["nonexistant.yaml"], config={}, output_type=None)
