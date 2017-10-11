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

from rally.plugins.common.exporters import junit
from tests.unit import test


def get_tasks_results():
    task_id = "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"
    workload = {"created_at": "2017-06-04T05:14:44",
                "updated_at": "2017-06-04T05:15:14",
                "task_uuid": task_id,
                "position": 0,
                "name": "CinderVolumes.list_volumes",
                "description": "List all volumes.",
                "data": {"raw": []},
                "full_duration": 29.969523191452026,
                "sla": {},
                "sla_results": {"sla": []},
                "load_duration": 2.03029203414917,
                "hooks": [],
                "id": 3}
    task = {"subtasks": [
        {"task_uuid": task_id,
         "workloads": [workload]}]}
    return [task]


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

        reporter = junit.JUnitXMLExporter(get_tasks_results(),
                                          output_destination=None)
        self.assertEqual({"print": content}, reporter.generate())

        reporter = junit.JUnitXMLExporter(get_tasks_results(),
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
        reporter = junit.JUnitXMLExporter(tasks_results,
                                          output_destination=None)
        self.assertEqual({"print": content}, reporter.generate())
