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

import datetime as dt
import os
from unittest import mock

from rally.plugins.task.exporters import junit
from tests.unit import test


def get_tasks_results():
    task_id = "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"
    return [{
        "uuid": "task-uu-ii-dd",
        "created_at": "2017-06-04T05:14:00",
        "updated_at": "2017-06-04T05:15:15",
        "subtasks": [
            {"task_uuid": task_id,
             "workloads": [
                 {
                     "uuid": "workload-1-uuid",
                     "created_at": "2017-06-04T05:14:44",
                     "updated_at": "2017-06-04T05:15:14",
                     "task_uuid": task_id,
                     "position": 0,
                     "name": "CinderVolumes.list_volumes",
                     "full_duration": 29.969523191452026,
                     "sla_results": {"sla": []},
                     "pass_sla": True
                 },
                 {
                     "uuid": "workload-2-uuid",
                     "created_at": "2017-06-04T05:15:15",
                     "updated_at": "2017-06-04T05:16:14",
                     "task_uuid": task_id,
                     "position": 1,
                     "name": "NovaServers.list_keypairs",
                     "full_duration": 5,
                     "sla_results": {"sla": [
                         {"criterion": "Failing",
                          "success": False,
                          "detail": "ooops"},
                         {"criterion": "Ok",
                          "success": True,
                          "detail": None},
                     ]},
                     "pass_sla": False
                 },
             ]}]}]


class JUnitXMLExporterTestCase(test.TestCase):
    def setUp(self):
        super(JUnitXMLExporterTestCase, self).setUp()
        self.datetime = dt.datetime

        patcher = mock.patch("rally.common.io.junit.dt")
        self.dt = patcher.start()
        self.dt.datetime.utcnow.return_value.isoformat.return_value = "$TIME"
        self.addCleanup(patcher.stop)

    @mock.patch("rally.common.version.version_string")
    def test_generate(self, mock_version_string):
        mock_version_string.return_value = "$VERSION"

        with open(os.path.join(os.path.dirname(__file__),
                               "junit_report.xml")) as f:
            expected_report = f.read()

        reporter = junit.JUnitXMLExporter(get_tasks_results(),
                                          output_destination=None)
        self.assertEqual({"print": expected_report}, reporter.generate())

        reporter = junit.JUnitXMLExporter(get_tasks_results(),
                                          output_destination="path")
        self.assertEqual({"files": {"path": expected_report},
                          "open": "file://" + os.path.abspath("path")},
                         reporter.generate())
