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

import mock

from rally.verification.tempest import json2html
from tests.unit import test

BASE = "rally.verification.tempest"


class HtmlOutputTestCase(test.TestCase):

    results = {
        "time": 22,
        "tests": 4,
        "errors": 1,
        "success": 1,
        "skipped": 1,
        "failures": 1,
        "test_cases": {
            "tp": {"name": "tp",
                   "status": "OK",
                   "output": "tp_ok",
                   "time": 2},
            "ts": {"name": "ts",
                   "status": "SKIP",
                   "output": "ts_skip",
                   "time": 4},
            "tf": {"name": "tf",
                   "status": "FAIL",
                   "output": "tf_fail",
                   "time": 6,
                   "failure": {"type": "tf", "log": "fail_log"}},
            "te": {"name": "te",
                   "time": 2,
                   "status": "ERROR",
                   "output": "te_error",
                   "failure": {"type": "te", "log": "error+log"}}}}

    def test__init(self):
        obj = json2html.HtmlOutput(self.results)
        self.assertEqual(obj.num_passed, self.results["success"])
        self.assertEqual(obj.num_failed, self.results["failures"])
        self.assertEqual(obj.num_skipped, self.results["skipped"])
        self.assertEqual(obj.num_errors, self.results["errors"])
        self.assertEqual(obj.num_total, self.results["tests"])
        self.assertEqual(obj.results, self.results["test_cases"])

    def test__generate_report(self):

        obj = json2html.HtmlOutput(self.results)
        expected_report = {
            "errors": 1,
            "failed": 1,
            "passed": 1,
            "skipped": 1,
            "total": 4,
            "tests": [{"desc": "te",
                       "id": 0,
                       "output": "te_errorerror+log",
                       "status": "error",
                       "time": 2},
                      {"desc": "tf",
                       "id": 1,
                       "output": "tf_failfail_log",
                       "status": "fail",
                       "time": 6},
                      {"desc": "tp",
                       "id": 2,
                       "output": "tp_ok",
                       "status": "pass",
                       "time": 2},
                      {"desc": "ts",
                       "id": 3,
                       "output": "ts_skip",
                       "status": "skip",
                       "time": 4}]}

        report = obj._generate_report()
        self.assertEqual(report, expected_report)

    @mock.patch(BASE + ".json2html.ui_utils.get_template")
    @mock.patch(BASE + ".json2html.HtmlOutput._generate_report",
                return_value="report_data")
    def test_create_report(
            self, mock_html_output__generate_report, mock_get_template):
        obj = json2html.HtmlOutput(self.results)
        mock_get_template.return_value.render.return_value = "html_report"

        html_report = obj.create_report()
        self.assertEqual(html_report, "html_report")
        mock_get_template.assert_called_once_with("verification/report.mako")
        mock_get_template.return_value.render.assert_called_once_with(
            report="report_data")
