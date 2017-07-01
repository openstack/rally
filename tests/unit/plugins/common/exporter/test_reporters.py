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

from rally.plugins.common.exporter import reporters
from tests.unit import test

PATH = "rally.plugins.common.exporter.reporters"


def get_tasks_results():
    task_id = "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"
    workload = {"uuid": "uuid",
                "name": "CinderVolumes.list_volumes",
                "description": "List all volumes.",
                "created_at": "2017-06-04T05:14:44",
                "updated_at": "2017-06-04T05:15:14",
                "task_uuid": task_id,
                "position": 0,
                "data": {"raw": []},
                "full_duration": 29.969523191452026,
                "load_duration": 2.03029203414917,
                "hooks": [],
                "runner": {},
                "runner_type": "runner_type",
                "args": {},
                "context": {},
                "min_duration": 0.0,
                "max_duration": 1.0,
                "start_time": 0,
                "statistics": {},
                "failed_iteration_count": 0,
                "total_iteration_count": 10,
                "sla": {},
                "sla_results": {"sla": []},
                "pass_sla": True
                }
    task = {
        "uuid": task_id,
        "title": "task",
        "description": "description",
        "status": "finished",
        "tags": [],
        "created_at": "2017-06-04T05:14:44",
        "updated_at": "2017-06-04T05:15:14",
        "pass_sla": True,
        "task_duration": 2.0,
        "subtasks": [
            {"uuid": "subtask_uuid",
             "title": "subtask",
             "description": "description",
             "status": "finished",
             "run_in_parallel": True,
             "created_at": "2017-06-04T05:14:44",
             "updated_at": "2017-06-04T05:15:14",
             "sla": {},
             "context": {},
             "duration": 29.969523191452026,
             "task_uuid": task_id,
             "workloads": [workload]}
        ]}
    return [task]


class HTMLExporterTestCase(test.TestCase):

    @mock.patch("%s.plot.plot" % PATH, return_value="html")
    def test_generate(self, mock_plot):
        tasks_results = get_tasks_results()
        tasks_results.extend(get_tasks_results())
        reporter = reporters.HTMLExporter(tasks_results, None)
        reporter._generate_results = mock.MagicMock()

        self.assertEqual({"print": "html"}, reporter.generate())

        reporter._generate_results.assert_called_once_with()
        mock_plot.assert_called_once_with(
            reporter._generate_results.return_value,
            include_libs=False)

        reporter = reporters.HTMLExporter(tasks_results,
                                          output_destination="path")
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

        reporter = reporters.HTMLExporter(tasks_results, None)

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


class JUnitXMLExporterTestCase(test.TestCase):

    def test_generate(self):
        content = ("<testsuite errors=\"0\""
                   " failures=\"0\""
                   " name=\"Rally test suite\""
                   " tests=\"1\""
                   " time=\"29.97\">"
                   "<testcase classname=\"CinderVolumes\""
                   " name=\"list_volumes\""
                   " time=\"29.97\" />"
                   "</testsuite>")

        reporter = reporters.JUnitXMLExporter(get_tasks_results(),
                                              output_destination=None)
        self.assertEqual({"print": content}, reporter.generate())

        reporter = reporters.JUnitXMLExporter(get_tasks_results(),
                                              output_destination="path")
        self.assertEqual({"files": {"path": content},
                          "open": "file://" + os.path.abspath("path")},
                         reporter.generate())

    def test_generate_fail(self):
        tasks_results = get_tasks_results()
        tasks_results[0]["subtasks"][0]["workloads"][0]["sla_results"] = {
            "sla": [{"success": False, "detail": "error"}]}
        content = ("<testsuite errors=\"0\""
                   " failures=\"1\""
                   " name=\"Rally test suite\""
                   " tests=\"1\""
                   " time=\"29.97\">"
                   "<testcase classname=\"CinderVolumes\""
                   " name=\"list_volumes\""
                   " time=\"29.97\">"
                   "<failure message=\"error\" /></testcase>"
                   "</testsuite>")
        reporter = reporters.JUnitXMLExporter(tasks_results,
                                              output_destination=None)
        self.assertEqual({"print": content}, reporter.generate())
