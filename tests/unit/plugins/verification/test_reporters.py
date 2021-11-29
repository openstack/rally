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
import os
from unittest import mock

import ddt

from rally.common import utils
from rally.plugins.verification import reporters
from tests.unit import test


PATH = "rally.plugins.verification.reporters"


def get_verifications():
    tests_1 = {
        "some.test.TestCase.test_foo[id=iiiidddd;smoke]":
            {"name": "some.test.TestCase.test_foo",
             "tags": ["smoke", "id"],
             "status": "success",
             "timestamp": "2001-01-01T00:01:00",
             "duration": "8"},
        "some.test.TestCase.test_skipped":
            {"name": "some.test.TestCase.test_skipped",
             "status": "skip",
             "timestamp": "2001-01-01T00:02:00",
             "reason": "Skipped until Bug: 666 is resolved.",
             "duration": "0"},
        "some.test.TestCase.test_xfail":
            {"name": "some.test.TestCase.test_xfail",
             "status": "xfail",
             "timestamp": "2001-01-01T00:03:00",
             "reason": "something",
             "traceback": "HEEELP",
             "duration": "3"},
        "some.test.TestCase.test_uxsuccess":
            {"name": "some.test.TestCase.test_uxsuccess",
             "status": "uxsuccess",
             "timestamp": "2001-01-01T00:04:00",
             "reason": "It should fail since I expect it",
             "duration": "3"}

    }
    tests_2 = {
        "some.test.TestCase.test_foo[id=iiiidddd;smoke]":
            {"name": "some.test.TestCase.test_foo",
             "tags": ["smoke", "id"],
             "status": "success",
             "timestamp": "2001-02-01T00:01:00",
             "duration": "8"},
        "some.test.TestCase.test_failed":
            {"name": "some.test.TestCase.test_failed",
             "status": "fail",
             "timestamp": "2001-02-01T00:02:00",
             "traceback": "HEEEEEEELP",
             "duration": "8"},
        "some.test.TestCase.test_skipped":
            {"name": "some.test.TestCase.test_skipped",
             "status": "skip",
             "timestamp": "2001-02-01T00:03:00",
             "reason": "Skipped until Bug: 666 is resolved.",
             "duration": "0"},
        "some.test.TestCase.test_xfail":
            {"name": "some.test.TestCase.test_xfail",
             "status": "xfail",
             "timestamp": "2001-02-01T00:04:00",
             "reason": "something",
             "traceback": "HEEELP",
             "duration": "4"}
    }
    tests_3 = {
        "some.test.TestCase.test_foo[id=iiiidddd;smoke]":
            {"name": "some.test.TestCase.test_foo",
             "tags": ["smoke", "id"],
             "status": "success",
             "timestamp": "2001-03-01T00:01:00",
             "duration": "8"},
        "some.test.TestCase.test_failed":
            {"name": "some.test.TestCase.test_failed",
             "status": "fail",
             "timestamp": "2001-03-01T00:02:00",
             "traceback": "HEEEEEEELP",
             "duration": "7"},
        "some.test.TestCase.test_skipped":
            {"name": "some.test.TestCase.test_skipped",
             "status": "skip",
             "timestamp": "2001-03-01T00:03:00",
             "reason": "Skipped until Bug: 666 is resolved.",
             "duration": "0"},
        "some.test.TestCase.test_xfail":
            {"name": "some.test.TestCase.test_xfail",
             "status": "xfail",
             "timestamp": "2001-03-01T00:04:00",
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


class JSONReporterTestCase(test.TestCase):
    def test_validate(self):
        # nothing should fail
        reporters.JSONReporter.validate(mock.Mock())
        reporters.JSONReporter.validate("")
        reporters.JSONReporter.validate(None)

    def test__generate(self):
        reporter = reporters.JSONReporter(get_verifications(), None)
        report = reporter._generate()

        self.assertEqual(
            collections.OrderedDict(
                [("foo-bar-1", {"status": "finished",
                                "started_at": "2001-01-01T00:00:00",
                                "finished_at": "2001-01-02T00:00:00",
                                "tests_duration": 1.111,
                                "tests_count": 9,
                                "run_args": "set_name=compute",
                                "skipped": 0,
                                "success": 3,
                                "unexpected_success": 2,
                                "expected_failures": 3,
                                "failures": 1}),
                 ("foo-bar-2", {"status": "finished",
                                "started_at": "2002-01-01T00:00:00",
                                "finished_at": "2002-01-02T00:00:00",
                                "tests_duration": 22.222,
                                "tests_count": 99,
                                "run_args": "set_name=full",
                                "skipped": 0,
                                "success": 33,
                                "unexpected_success": 22,
                                "expected_failures": 33,
                                "failures": 11}),
                 ("foo-bar-3", {"status": "finished",
                                "started_at": "2003-01-01T00:00:00",
                                "finished_at": "2003-01-02T00:00:00",
                                "tests_duration": 33.333,
                                "tests_count": 99,
                                "run_args": "set_name=full",
                                "skipped": 0,
                                "success": 33,
                                "unexpected_success": 22,
                                "expected_failures": 33,
                                "failures": 11})]),
            report["verifications"])

        self.assertEqual({
            "some.test.TestCase.test_foo[id=iiiidddd;smoke]": {
                "by_verification": {"foo-bar-1": {"duration": "8",
                                                  "status": "success"},
                                    "foo-bar-2": {"duration": "8",
                                                  "status": "success"},
                                    "foo-bar-3": {"duration": "8",
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
                "tags": []},
            "some.test.TestCase.test_uxsuccess": {
                "name": "some.test.TestCase.test_uxsuccess",
                "tags": [],
                "by_verification": {"foo-bar-1": {
                    "details": "It should fail since I expect it",
                    "duration": "3",
                    "status": "uxsuccess"}}}},
            report["tests"])

    @mock.patch("%s.json.dumps" % PATH)
    @mock.patch("%s.JSONReporter._generate" % PATH)
    def test_generate(self, mock__generate, mock_dumps):
        reporter = reporters.JSONReporter([], output_destination=None)
        self.assertEqual({"print": mock_dumps.return_value},
                         reporter.generate())
        mock__generate.assert_called_once_with()
        mock_dumps.assert_called_once_with(mock__generate.return_value,
                                           indent=4)

        mock__generate.reset_mock()
        mock_dumps.reset_mock()

        path = "some_path"
        reporter = reporters.JSONReporter([], output_destination=path)
        self.assertEqual({"files": {path: mock_dumps.return_value},
                          "open": path}, reporter.generate())
        mock__generate.assert_called_once_with()
        mock_dumps.assert_called_once_with(mock__generate.return_value,
                                           indent=4)


@ddt.ddt
class HTMLReporterTestCase(test.TestCase):
    @mock.patch("%s.ui_utils" % PATH)
    @mock.patch("%s.json.dumps" % PATH)
    @ddt.data((reporters.HTMLReporter, False),
              (reporters.HTMLStaticReporter, True))
    @ddt.unpack
    def test_generate(self, cls, include_libs, mock_dumps, mock_ui_utils):
        mock_render = mock_ui_utils.get_template.return_value.render

        reporter = cls(get_verifications(), None)

        self.assertEqual({"print": mock_render.return_value},
                         reporter.generate())
        mock_render.assert_called_once_with(data=mock_dumps.return_value,
                                            include_libs=include_libs)
        mock_ui_utils.get_template.assert_called_once_with(
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
                "tags": []},
            "some.test.TestCase.test_uxsuccess": {
                "name": "some.test.TestCase.test_uxsuccess",
                "tags": [],
                "has_details": True,
                "by_verification": {"foo-bar-1": {
                    "details": "It should fail since I expect it",
                    "duration": "3",
                    "status": "uxsuccess"}}}},
            ctx["tests"])

    def test_generate_raw_html_report(self):
        reporter = reporters.HTMLReporter(get_verifications(), None)
        report = reporter.generate()
        self.assertTrue(report["print"])


class JUnitXMLReporterTestCase(test.TestCase):

    @mock.patch("rally.common.io.junit.dt")
    @mock.patch("rally.common.version.version_string")
    def test_generate(self, mock_version_string, mock_dt):
        mock_dt.datetime.utcnow.return_value.isoformat.return_value = "TIME"
        # release when junit reporter was introduced
        mock_version_string.return_value = "0.8.0"
        with open(os.path.join(os.path.dirname(__file__),
                               "junit_report.xml")) as f:
            expected_report = f.read()

        junit_reporter = reporters.JUnitXMLReporter(get_verifications(), None)
        self.assertEqual({"print": expected_report}, junit_reporter.generate())

        dest = "path"
        junit_reporter = reporters.JUnitXMLReporter(get_verifications(), dest)
        self.assertEqual({"open": dest,
                          "files": {dest: expected_report}},
                         junit_reporter.generate())
