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

import mock

from rally.ui import report
from tests.unit import test


class VerificationReportTestCase(test.TestCase):

    def gen_instance(self, runs=None, uuids=None, tests=None):
        ins = report.VerificationReport({})
        ins._runs = runs or {}
        ins._uuids = uuids or list(ins._runs.keys())
        ins._tests = tests or []
        return ins

    def test___init__(self):
        verifications = collections.OrderedDict([
            ("a_uuid", {
                "tests": {"spam": {"status": "fail",
                                   "duration": 4.2,
                                   "details": "Some error",
                                   "tags": ["a-tag", "id-tag", "z-tag"]}}}),
            ("b_uuid", {
                "tests": {"foo": {"status": "success", "duration": 0,
                                  "details": None,
                                  "tags": ["a-tag", "id-tag", "z-tag"]},
                          "bar": {"status": "skip", "duration": 4.2,
                                  "details": None,
                                  "tags": ["a-tag", "id-tag", "z-tag"]}}})])
        ins = report.VerificationReport(verifications)
        self.assertEqual(verifications, ins._runs)
        self.assertEqual(["a_uuid", "b_uuid"], ins._uuids)
        tests = [
            {"has_details": False, "by_verification": {
                "b_uuid": {"duration": 4.2, "status": "skip",
                           "details": None}},
             "name": "bar", "tags": ["id-tag", "a-tag", "z-tag"]},
            {"has_details": False, "by_verification": {
                "b_uuid": {"duration": 0, "status": "success",
                           "details": None}},
             "name": "foo", "tags": ["id-tag", "a-tag", "z-tag"]},
            {"has_details": True, "by_verification": {
                "a_uuid": {"duration": 4.2, "status": "fail",
                           "details": "Some error"}},
             "name": "spam", "tags": ["id-tag", "a-tag", "z-tag"]}]
        self.assertEqual(tests, sorted(ins._tests, key=lambda i: i["name"]))

    @mock.patch("rally.ui.report.utils")
    @mock.patch("rally.ui.report.json.dumps", return_value="json!")
    def test_to_html(self, mock_dumps, mock_utils):
        mock_render = mock.Mock(return_value="HTML")
        mock_utils.get_template.return_value.render = mock_render
        ins = self.gen_instance(runs="runs!", uuids="uuids!", tests="tests!")
        self.assertEqual("HTML", ins.to_html())
        mock_utils.get_template.assert_called_once_with(
            "verification/report.html")
        mock_dumps.assert_called_once_with(
            {"tests": "tests!", "uuids": "uuids!", "verifications": "runs!"})
        mock_render.assert_called_once_with(data="json!", include_libs=False)

    @mock.patch("rally.ui.report.json.dumps", return_value="json!")
    def test_to_json(self, mock_dumps):
        ins = self.gen_instance(tests="tests!")
        self.assertEqual("json!", ins.to_json())
        mock_dumps.assert_called_once_with("tests!", indent=4)

    @mock.patch("rally.ui.report.csv")
    @mock.patch("rally.ui.report.io.BytesIO")
    def test_to_csv(self, mock_bytes_io, mock_csv):
        ins = self.gen_instance(
            uuids=["foo", "bar"],
            tests=[{"name": "test-1", "tags": ["tag1", "tag2"],
                    "has_details": False,
                    "by_verification": {
                        "foo": {"status": "success", "duration": 1.2}}},
                   {"name": "test-2", "tags": ["tag3", "tag4"],
                    "has_details": False,
                    "by_verification": {
                        "bar": {"status": "success", "duration": 3.4}}}])
        mock_stream = mock.Mock()
        mock_stream.getvalue.return_value = "CSV!"
        mock_bytes_io.return_value.__enter__.return_value = mock_stream
        self.assertEqual("CSV!", ins.to_csv())
        mock_csv.writer.assert_called_once_with(mock_stream)

        # Custom kwargs
        mock_csv.writer.reset_mock()
        self.assertEqual("CSV!", ins.to_csv(foo="bar"))
        mock_csv.writer.assert_called_once_with(mock_stream, foo="bar")
