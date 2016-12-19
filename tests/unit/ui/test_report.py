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

from rally.common import utils
from rally.ui import report
from tests.unit import test


class VerificationReportTestCase(test.TestCase):
    def get_verifications(self):
        tests_1 = {
            "some.test.TestCase.test_foo[id=iiiidddd;smoke]":
                {"name": "some.test.TestCase.test_foo",
                 "tags": ["smoke", "id"],
                 "status": "success",
                 "duration": "8"},
            "some.test.TestCase.test_skipped":
                {"name": "some.test.TestCase.test_skipped",
                 "status": "skip",
                 "reason": "Skipped until Bug: 666 is resolved.",
                 "duration": "0"},
            "some.test.TestCase.test_xfail":
                {"name": "some.test.TestCase.test_xfail",
                 "status": "xfail",
                 "reason": "something",
                 "traceback": "HEEELP",
                 "duration": "3"}
        }
        tests_2 = {
            "some.test.TestCase.test_foo[id=iiiidddd;smoke]":
                {"name": "some.test.TestCase.test_foo",
                 "tags": ["smoke", "id"],
                 "status": "success",
                 "duration": "8"},
            "some.test.TestCase.test_failed":
                {"name": "some.test.TestCase.test_failed",
                 "status": "fail",
                 "traceback": "HEEEEEEELP",
                 "duration": "8"},
            "some.test.TestCase.test_skipped":
                {"name": "some.test.TestCase.test_skipped",
                 "status": "skip",
                 "reason": "Skipped until Bug: 666 is resolved.",
                 "duration": "0"},
            "some.test.TestCase.test_xfail":
                {"name": "some.test.TestCase.test_xfail",
                 "status": "xfail",
                 "reason": "something",
                 "traceback": "HEEELP",
                 "duration": "4"}
        }
        tests_3 = {
            "some.test.TestCase.test_foo[id=iiiidddd;smoke]":
                {"name": "some.test.TestCase.test_foo",
                 "tags": ["smoke", "id"],
                 "status": "success",
                 "duration": "8"},
            "some.test.TestCase.test_failed":
                {"name": "some.test.TestCase.test_failed",
                 "status": "fail",
                 "traceback": "HEEEEEEELP",
                 "duration": "7"},
            "some.test.TestCase.test_skipped":
                {"name": "some.test.TestCase.test_skipped",
                 "status": "skip",
                 "reason": "Skipped until Bug: 666 is resolved.",
                 "duration": "0"},
            "some.test.TestCase.test_xfail":
                {"name": "some.test.TestCase.test_xfail",
                 "status": "xfail",
                 "reason": "something",
                 "traceback": "HEEELP",
                 "duration": "3"}
        }

        return [
            utils.Struct(uuid="foo-bar-1",
                         created_at=dt.datetime(2001, 1, 1),
                         updated_at=dt.datetime(2001, 1, 2),
                         status="finished",
                         run_args="set_name=compute",
                         tests_duration=1.111,
                         tests_count=9,
                         skipped=0,
                         success=3,
                         expected_failures=3,
                         unexpected_success=2,
                         failures=1,
                         tests=tests_1),
            utils.Struct(uuid="foo-bar-2",
                         created_at=dt.datetime(2002, 1, 1),
                         updated_at=dt.datetime(2002, 1, 2),
                         status="finished",
                         run_args="set_name=full",
                         tests_duration=22.222,
                         tests_count=99,
                         skipped=0,
                         success=33,
                         expected_failures=33,
                         unexpected_success=22,
                         failures=11,
                         tests=tests_2),
            utils.Struct(uuid="foo-bar-3",
                         created_at=dt.datetime(2003, 1, 1),
                         updated_at=dt.datetime(2003, 1, 2),
                         status="finished",
                         run_args="set_name=full",
                         tests_duration=33.333,
                         tests_count=99,
                         skipped=0,
                         success=33,
                         expected_failures=33,
                         unexpected_success=22,
                         failures=11,
                         tests=tests_3)
        ]

    def test__init__(self):
        vreport = report.VerificationReport(self.get_verifications())

        self.assertEqual(
            collections.OrderedDict(
                [("foo-bar-1", {"status": "finished",
                                "started_at": "2001-01-01 00:00:00",
                                "finished_at": "2001-01-02 00:00:00",
                                "tests_duration": 1.111,
                                "tests_count": 9,
                                "run_args": "set_name=compute",
                                "skipped": 0,
                                "success": 3,
                                "unexpected_success": 2,
                                "expected_failures": 3,
                                "failures": 1}),
                 ("foo-bar-2", {"status": "finished",
                                "started_at": "2002-01-01 00:00:00",
                                "finished_at": "2002-01-02 00:00:00",
                                "tests_duration": 22.222,
                                "tests_count": 99,
                                "run_args": "set_name=full",
                                "skipped": 0,
                                "success": 33,
                                "unexpected_success": 22,
                                "expected_failures": 33,
                                "failures": 11}),
                 ("foo-bar-3", {"status": "finished",
                                "started_at": "2003-01-01 00:00:00",
                                "finished_at": "2003-01-02 00:00:00",
                                "tests_duration": 33.333,
                                "tests_count": 99,
                                "run_args": "set_name=full",
                                "skipped": 0,
                                "success": 33,
                                "unexpected_success": 22,
                                "expected_failures": 33,
                                "failures": 11})]),
            vreport.report["verifications"])

        self.assertEqual({
            "some.test.TestCase.test_foo[id=iiiidddd;smoke]": {
                "by_verification": {"foo-bar-1": {"details": None,
                                                  "duration": "8",
                                                  "status": "success"},
                                    "foo-bar-2": {"details": None,
                                                  "duration": "8",
                                                  "status": "success"},
                                    "foo-bar-3": {"details": None,
                                                  "duration": "8",
                                                  "status": "success"}
                                    },
                "name": "some.test.TestCase.test_foo",
                "tags": ["smoke", "id"]},
            "some.test.TestCase.test_failed": {
                "by_verification": {"foo-bar-2": {"details": "HEEEEEEELP",
                                                  "duration": "8",
                                                  "status": "fail"},
                                    "foo-bar-3": {"details": "HEEEEEEELP",
                                                  "duration": "7",
                                                  "status": "fail"}},
                "name": "some.test.TestCase.test_failed",
                "tags": []},
            "some.test.TestCase.test_skipped": {
                "by_verification": {
                    "foo-bar-1": {
                        "details": "Skipped until Bug: https://launchpad.net/"
                                   "bugs/666 is resolved.",
                        "duration": "0",
                        "status": "skip"},
                    "foo-bar-2": {
                        "details": "Skipped until Bug: https://launchpad.net/"
                                   "bugs/666 is resolved.",
                        "duration": "0",
                        "status": "skip"},
                    "foo-bar-3": {
                        "details": "Skipped until Bug: https://launchpad.net/"
                                   "bugs/666 is resolved.",
                        "duration": "0",
                        "status": "skip"}},
                "name": "some.test.TestCase.test_skipped",
                "tags": []},
            "some.test.TestCase.test_xfail": {
                "by_verification": {
                    "foo-bar-1": {"details": "something\n\nHEEELP",
                                  "duration": "3",
                                  "status": "xfail"},
                    "foo-bar-2": {"details": "something\n\nHEEELP",
                                  "duration": "4",
                                  "status": "xfail"},
                    "foo-bar-3": {"details": "something\n\nHEEELP",
                                  "duration": "3",
                                  "status": "xfail"}},
                "name": "some.test.TestCase.test_xfail",
                "tags": []}},
            vreport.report["tests"])

    @mock.patch("rally.ui.report.utils")
    @mock.patch("rally.ui.report.json.dumps")
    def test_to_html(self, mock_dumps, mock_utils):
        mock_render = mock_utils.get_template.return_value.render

        vreport = report.VerificationReport(self.get_verifications())

        self.assertEqual(mock_render.return_value, vreport.to_html())
        mock_render.assert_called_once_with(data=mock_dumps.return_value,
                                            include_libs=False)
        mock_utils.get_template.assert_called_once_with(
            "verification/report.html")

        self.assertEqual(1, mock_dumps.call_count)
        args, kwargs = mock_dumps.call_args
        self.assertTrue(not kwargs)
        self.assertEqual(1, len(args))
        ctx = args[0]
        self.assertEqual({"uuids", "verifications", "tests",
                          "show_comparison_note"},
                         set(ctx.keys()))
        self.assertEqual(["foo-bar-1", "foo-bar-2", "foo-bar-3"],
                         list(ctx["uuids"]))
        self.assertEqual(vreport.report["verifications"],
                         ctx["verifications"])
        self.assertTrue(ctx["show_comparison_note"])
        self.assertEqual({
            "some.test.TestCase.test_foo[id=iiiidddd;smoke]": {
                "by_verification": {"foo-bar-1": {"details": None,
                                                  "duration": "8",
                                                  "status": "success"},
                                    "foo-bar-2": {"details": None,
                                                  "duration": "8 (+0.0)",
                                                  "status": "success"},
                                    "foo-bar-3": {"details": None,
                                                  "duration": "8 (+0.0)",
                                                  "status": "success"}},
                "has_details": False,
                "name": "some.test.TestCase.test_foo",
                "tags": ["smoke", "id"]},
            "some.test.TestCase.test_failed": {
                "by_verification": {"foo-bar-2": {"details": "HEEEEEEELP",
                                                  "duration": "8",
                                                  "status": "fail"},
                                    "foo-bar-3": {"details": "HEEEEEEELP",
                                                  "duration": "7 (-1.0)",
                                                  "status": "fail"}},
                "has_details": True,
                "name": "some.test.TestCase.test_failed",
                "tags": []},
            "some.test.TestCase.test_skipped": {
                "by_verification": {
                    "foo-bar-1": {"details": "Skipped until Bug: https://laun"
                                             "chpad.net/bugs/666 is resolved.",
                                  "duration": "",
                                  "status": "skip"},
                    "foo-bar-2": {"details": "Skipped until Bug: https://laun"
                                             "chpad.net/bugs/666 is resolved.",
                                  "duration": "",
                                  "status": "skip"},
                    "foo-bar-3": {"details": "Skipped until Bug: https://laun"
                                             "chpad.net/bugs/666 is resolved.",
                                  "duration": "",
                                  "status": "skip"}},
                "has_details": True,
                "name": "some.test.TestCase.test_skipped",
                "tags": []},
            "some.test.TestCase.test_xfail": {
                "by_verification": {
                    "foo-bar-1": {"details": "something\n\nHEEELP",
                                  "duration": "3",
                                  "status": "xfail"},
                    "foo-bar-2": {"details": "something\n\nHEEELP",
                                  "duration": "4 (+1.0)",
                                  "status": "xfail"},
                    "foo-bar-3": {"details": "something\n\nHEEELP",
                                  "duration": "3 (+0.0)",
                                  "status": "xfail"}},
                "has_details": True,
                "name": "some.test.TestCase.test_xfail",
                "tags": []}},
            ctx["tests"])

    @mock.patch("rally.ui.report.json.dumps")
    def test_to_json(self, mock_dumps):
        obj = mock.MagicMock()
        indent = 777

        vreport = report.VerificationReport([])
        vreport.report = obj

        self.assertEqual(mock_dumps.return_value, vreport.to_json(indent))

        mock_dumps.assert_called_once_with(obj, indent=indent)
