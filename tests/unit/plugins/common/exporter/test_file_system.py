# Copyright 2016: Mirantis Inc.
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

import ddt
import mock
import six
import six.moves.builtins as __builtin__

from rally import exceptions
from rally.plugins.common.exporter import file_system
from tests.unit import test

if six.PY3:
    import io
    file = io.BytesIO


@ddt.ddt
class FileExporterTestCase(test.TestCase):

    @mock.patch("rally.plugins.common.exporter.file_system.os.path.exists")
    @mock.patch.object(__builtin__, "open", autospec=True)
    @mock.patch("rally.plugins.common.exporter.file_system.json.dumps")
    @mock.patch("rally.api.Task.get")
    def test_file_exporter_export(self, mock_task_get, mock_dumps, mock_open,
                                  mock_exists):
        mock_task = mock.Mock()
        mock_exists.return_value = True
        mock_task_get.return_value = mock_task
        mock_task.get_results.return_value = [{
            "key": "fake_key",
            "data": {
                "raw": "bar_raw",
                "sla": "baz_sla",
                "hooks": "baz_hooks",
                "load_duration": "foo_load_duration",
                "full_duration": "foo_full_duration",
            }
        }]
        mock_dumps.return_value = "fake_results"
        input_mock = mock.MagicMock(spec=file)
        mock_open.return_value = input_mock

        exporter = file_system.FileExporter("file-exporter:///fake_path.json")
        exporter.export("fake_uuid")

        mock_open().__enter__().write.assert_called_once_with("fake_results")
        mock_task_get.assert_called_once_with("fake_uuid")
        expected_dict = [
            {
                "load_duration": "foo_load_duration",
                "full_duration": "foo_full_duration",
                "result": "bar_raw",
                "key": "fake_key",
                "hooks": "baz_hooks",
                "sla": "baz_sla"
            }
        ]
        mock_dumps.assert_called_once_with(expected_dict, sort_keys=False,
                                           indent=4)

    @mock.patch("rally.api.Task.get")
    def test_file_exporter_export_running_task(self, mock_task_get):
        mock_task = mock.Mock()
        mock_task_get.return_value = mock_task
        mock_task.get_results.return_value = []

        exporter = file_system.FileExporter("file-exporter:///fake_path.json")
        self.assertRaises(exceptions.RallyException, exporter.export,
                          "fake_uuid")

    @ddt.data(
        {"connection": "",
         "raises": exceptions.InvalidConnectionString},
        {"connection": "file-exporter:///fake_path.json",
         "raises": None},
        {"connection": "file-exporter:///fake_path.fake",
         "raises": exceptions.InvalidConnectionString},
    )
    @ddt.unpack
    def test_file_exporter_validate(self, connection, raises):
        print(connection)
        if raises:
            self.assertRaises(raises, file_system.FileExporter, connection)
        else:
            file_system.FileExporter(connection)
