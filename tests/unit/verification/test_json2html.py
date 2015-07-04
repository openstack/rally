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
        "success": 1,
        "skipped": 1,
        "failures": 1,
        "expected_failures": 0,
        "unexpected_success": 0,
        "test_cases": {
            "tp": {"name": "tp",
                   "status": "success",
                   "time": 2},
            "ts": {"name": "ts",
                   "status": "skip",
                   "reason": "ts_skip",
                   "time": 4},
            "tf": {"name": "tf",
                   "status": "fail",
                   "time": 6,
                   "traceback": "fail_log"}}}

    def test__generate_report(self):

        obj = json2html.HtmlOutput(self.results)
        expected_report = {
            "failures": 1,
            "success": 1,
            "skipped": 1,
            "expected_failures": 0,
            "unexpected_success": 0,
            "total": 4,
            "time": 22,
            "tests": [{"name": "tf",
                       "id": 0,
                       "output": "fail_log",
                       "status": "fail",
                       "time": 6},
                      {"name": "tp",
                       "id": 1,
                       "output": "",
                       "status": "success",
                       "time": 2},
                      {"name": "ts",
                       "id": 2,
                       "output": "ts_skip",
                       "status": "skip",
                       "time": 4}]}

        report = obj._generate_report()
        self.assertEqual(expected_report, report)

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
