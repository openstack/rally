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

import collections
import datetime as dt

import mock

from rally.common import version as rally_version
from rally.plugins.common.exporters import json_exporter
from tests.unit.plugins.common.exporters import test_html
from tests.unit import test

PATH = "rally.plugins.common.exporters.json_exporter"


class JSONExporterTestCase(test.TestCase):

    def test__generate_tasks(self):
        tasks_results = test_html.get_tasks_results()
        reporter = json_exporter.JSONExporter(tasks_results, None)

        self.assertEqual([
            collections.OrderedDict([
                ("uuid", "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"),
                ("title", "task"),
                ("description", "description"),
                ("status", "finished"),
                ("tags", []),
                ("env_uuid", "env-uuid"),
                ("env_name", "env-name"),
                ("created_at", "2017-06-04T05:14:44"),
                ("updated_at", "2017-06-04T05:15:14"),
                ("pass_sla", True),
                ("subtasks", [
                    collections.OrderedDict([
                        ("uuid", "subtask_uuid"),
                        ("title", "subtask"),
                        ("description", "description"),
                        ("status", "finished"),
                        ("created_at", "2017-06-04T05:14:44"),
                        ("updated_at", "2017-06-04T05:15:14"),
                        ("sla", {}),
                        ("workloads", [
                            collections.OrderedDict([
                                ("uuid", "uuid"),
                                ("description", "List all volumes."),
                                ("runner", {"runner_type": {}}),
                                ("hooks", []),
                                ("scenario", {
                                    "CinderVolumes.list_volumes": {}}),
                                ("min_duration", 0.0),
                                ("max_duration", 1.0),
                                ("start_time", 0),
                                ("load_duration", 2.03029203414917),
                                ("full_duration", 29.969523191452026),
                                ("statistics", {}),
                                ("data", {"raw": []}),
                                ("failed_iteration_count", 0),
                                ("total_iteration_count", 10),
                                ("created_at", "2017-06-04T05:14:44"),
                                ("updated_at", "2017-06-04T05:15:14"),
                                ("contexts", {}),
                                ("contexts_results", []),
                                ("position", 0),
                                ("pass_sla", True),
                                ("sla_results", {"sla": []}),
                                ("sla", {})
                            ])
                        ])
                    ])
                ])
            ])], reporter._generate_tasks())

    @mock.patch("%s.json.dumps" % PATH, return_value="json")
    @mock.patch("%s.dt" % PATH)
    def test_generate(self, mock_dt, mock_json_dumps):
        mock_dt.datetime.utcnow.return_value = dt.datetime.utcnow()
        tasks_results = test_html.get_tasks_results()

        # print
        reporter = json_exporter.JSONExporter(tasks_results, None)
        reporter._generate_tasks = mock.MagicMock()
        self.assertEqual({"print": "json"}, reporter.generate())
        results = {
            "info": {"rally_version": rally_version.version_string(),
                     "generated_at": mock_dt.datetime.strftime.return_value,
                     "format_version": "1.2"},
            "tasks": reporter._generate_tasks.return_value
        }
        mock_dt.datetime.strftime.assert_called_once_with(
            mock_dt.datetime.utcnow.return_value,
            json_exporter.TIMEFORMAT)
        reporter._generate_tasks.assert_called_once_with()
        mock_json_dumps.assert_called_once_with(results,
                                                sort_keys=False,
                                                indent=4)

        # export to file
        reporter = json_exporter.JSONExporter(tasks_results,
                                              output_destination="path")
        self.assertEqual({"files": {"path": "json"},
                          "open": "file://path"}, reporter.generate())
