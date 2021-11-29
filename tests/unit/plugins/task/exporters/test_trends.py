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

from rally.plugins.task.exporters import trends
from tests.unit import test

PATH = "rally.plugins.task.exporters.html"


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
                "contexts": {},
                "contexts_results": [],
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
        "env_uuid": "env-uuid",
        "env_name": "env-name",
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
             "duration": 29.969523191452026,
             "task_uuid": task_id,
             "workloads": [workload]}
        ]}
    return [task]


class TrendsExporterTestCase(test.TestCase):

    @mock.patch("%s.plot.trends" % PATH, return_value="html")
    def test_generate(self, mock_plot_trends):
        reporter = trends.TrendsExporter("task_results", None)

        self.assertEqual({"print": "html"}, reporter.generate())

        mock_plot_trends.assert_called_once_with(
            "task_results", False)

        reporter = trends.TrendsExporter("task_results",
                                         output_destination="path")
        self.assertEqual({"files": {"path": "html"},
                          "open": "file://" + os.path.abspath("path")},
                         reporter.generate())
