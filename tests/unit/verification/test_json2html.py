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

import mock

from rally.verification.tempest import json2html
from tests.unit import test

BASE = "rally.verification.tempest"


class HtmlOutputTestCase(test.TestCase):

    @mock.patch(BASE + ".json2html.ui_utils.get_template")
    def test_generate_report(self, mock_get_template):
        results = {
            "time": 22.75,
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

        expected_report = {
            "failures": 1,
            "success": 1,
            "skipped": 1,
            "expected_failures": 0,
            "unexpected_success": 0,
            "total": 4,
            "time": "{0} ({1} s)".format(
                dt.timedelta(seconds=23), 22.75),
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
                       "output": "Reason:\n  ts_skip",
                       "status": "skip",
                       "time": 4}]}

        json2html.generate_report(results)

        mock_get_template.assert_called_once_with("verification/report.mako")
        mock_get_template.return_value.render.assert_called_once_with(
            report=expected_report)

    @mock.patch(BASE + ".json2html.ui_utils.get_template")
    def test_convert_bug_id_in_reason_into_bug_link(self, mock_get_template):
        results = {
            "failures": 0,
            "success": 0,
            "skipped": 1,
            "expected_failures": 0,
            "unexpected_success": 0,
            "tests": 1,
            "time": 0,
            "test_cases": {"one_test": {
                "status": "skip",
                "name": "one_test",
                "reason": "Skipped until Bug: 666666 is resolved.",
                "time": "time"}}}

        expected_report = {
            "failures": 0,
            "success": 0,
            "skipped": 1,
            "expected_failures": 0,
            "unexpected_success": 0,
            "total": 1,
            "time": "{0} ({1} s)".format(dt.timedelta(seconds=0), 0),
            "tests": [{
                "id": 0,
                "status": "skip",
                "name": "one_test",
                "output": "Reason:\n  Skipped until Bug: <a href='https://"
                          "launchpad.net/bugs/666666'>666666</a> is resolved.",
                "time": "time"}]}

        json2html.generate_report(results)
        mock_get_template.assert_called_once_with("verification/report.mako")
        mock_get_template.return_value.render.assert_called_once_with(
            report=expected_report)
