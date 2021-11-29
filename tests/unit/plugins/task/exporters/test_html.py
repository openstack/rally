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

from rally.plugins.task.exporters import html
from tests.unit.plugins.task.exporters import dummy_data
from tests.unit import test

PATH = "rally.plugins.task.exporters.html"


class HTMLExporterTestCase(test.TestCase):

    @mock.patch("%s.plot.plot" % PATH, return_value="html")
    def test_generate(self, mock_plot):
        tasks_results = dummy_data.get_tasks_results()
        tasks_results.extend(dummy_data.get_tasks_results())
        reporter = html.HTMLExporter(tasks_results, None)
        reporter._generate_results = mock.MagicMock()

        self.assertEqual({"print": "html"}, reporter.generate())

        reporter._generate_results.assert_called_once_with()
        mock_plot.assert_called_once_with(
            reporter._generate_results.return_value,
            include_libs=False)

        reporter = html.HTMLExporter(tasks_results, output_destination="path")
        self.assertEqual({"files": {"path": "html"},
                          "open": "file://" + os.path.abspath("path")},
                         reporter.generate())

    def test__generate_results(self):
        tasks_results = [{
            "uuid": "task_id",
            "subtasks": [
                {"uuid": "subtask_id",
                 "workloads": [
                     {
                         "uuid": "workload_id",
                         "name": "scenario_name",
                         "position": 0
                     },
                     {
                         "uuid": "workload_id",
                         "name": "scenario_name",
                         "position": 0
                     },
                 ]}
            ]
        }]

        reporter = html.HTMLExporter(tasks_results, None)

        self.assertEqual(
            [{
                "uuid": "task_id",
                "subtasks": [
                    {"uuid": "subtask_id",
                     "workloads": [
                         {
                             "uuid": "workload_id",
                             "name": "scenario_name",
                             "position": 0
                         },
                         {
                             "uuid": "workload_id",
                             "name": "scenario_name",
                             "position": 1
                         },
                     ]}
                ]
            }],
            reporter._generate_results()
        )
