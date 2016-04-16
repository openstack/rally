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

from rally.common.io import subunit_v2
from tests.unit import test


class SubunitParserTestCase(test.TestCase):
    fake_stream = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "subunit_v2.stream")

    def test_parse_results_file(self):
        result = subunit_v2.parse_results_file(self.fake_stream)

        self.assertEqual({"skipped": 1,
                          "success": 2,
                          "time": "5.007",
                          "failures": 3,
                          "expected_failures": 0,
                          "tests": 7,
                          "unexpected_success": 1}, result.total)
        self.assertEqual(len(result.tests), result.total["tests"])

        skipped_tests = result.filter_tests("skip")
        skipped_test = "test_foo.SimpleTestCase.test_skip_something"

        self.assertEqual(result.total["skipped"], len(skipped_tests))
        self.assertSequenceEqual([skipped_test], skipped_tests.keys())
        self.assertEqual(
            {"status": "skip", "reason": "This should be skipped.",
             "time": "0.000", "name": skipped_test},
            skipped_tests[skipped_test])

        failed_tests = result.filter_tests("fail")
        failed_test = "test_foo.SimpleTestCaseWithBrokenSetup.test_something"

        self.assertEqual(result.total["failures"], len(failed_tests))
        self.assertIn(failed_test, failed_tests)
        trace = """Traceback (most recent call last):
  File "test_foo.py", line 34, in setUp
    raise RuntimeError("broken setUp method")
RuntimeError: broken setUp method
"""
        self.assertEqual({"status": "fail", "traceback": trace,
                          "time": "0.000", "name": failed_test},
                         failed_tests[failed_test])

    def test_filter_results(self):
        results = subunit_v2.SubunitV2StreamResult()
        results._tests = {
            "failed_test_1": {"status": "fail"},
            "failed_test_2": {"status": "fail"},
            "passed_test_1": {"status": "success"},
            "passed_test_2": {"status": "success"},
            "passed_test_3": {"status": "success"}}
        self.assertEqual({"failed_test_1": results.tests["failed_test_1"],
                          "failed_test_2": results.tests["failed_test_2"]},
                         results.filter_tests("fail"))
        self.assertEqual({"passed_test_1": results.tests["passed_test_1"],
                          "passed_test_2": results.tests["passed_test_2"],
                          "passed_test_3": results.tests["passed_test_3"]},
                         results.filter_tests("success"))

    def test_property_test(self):
        results = subunit_v2.SubunitV2StreamResult()
        results._tests = {
            "SkippedTestCase.test_1": {"status": "init"},
            "SkippedTestCase.test_2": {"status": "init"}}
        results._unknown_entities = {"SkippedTestCase": {"status": "skip",
                                                         "reason": ":("}}

        self.assertFalse(results._is_parsed)

        self.assertEqual(
            {"SkippedTestCase.test_1": {"status": "skip", "reason": ":("},
             "SkippedTestCase.test_2": {"status": "skip", "reason": ":("}},
            results.tests)

        self.assertTrue(results._is_parsed)

    def test_preparse_input_args(self):
        some_mock = mock.MagicMock()

        @subunit_v2.preparse_input_args
        def some_a(self_, test_id, test_status, test_tags, file_name,
                   file_bytes, mime_type, timestamp, charset):
            some_mock(test_id, test_tags)

        some_a("", "setUpClass (some_test[tag1,tag2])")
        some_mock.assert_called_once_with(
            "some_test[tag1,tag2]", ["tag1", "tag2"])

        some_mock.reset_mock()
        some_a("", "tearDown (some_test[tag1,tag2])")
        some_mock.assert_called_once_with(
            "some_test[tag1,tag2]", ["tag1", "tag2"])

    def test_no_status_called(self):
        self.assertEqual({"tests": 0, "time": 0, "failures": 0, "skipped": 0,
                          "success": 0, "unexpected_success": 0,
                          "expected_failures": 0},
                         subunit_v2.SubunitV2StreamResult().total)

    def test_parse_results_file_with_expected_failures(self):
        test_1 = "test_foo.SimpleTestCase.test_something_that_fails"
        test_2 = "test_foo.SimpleTestCase.test_something_that_passes"
        expected_failures = {
            test_1: "Some details about why this test fails",
            test_2: None
        }

        result = subunit_v2.parse_results_file(self.fake_stream,
                                               expected_failures)
        tests = result.tests

        self.assertEqual("xfail", tests[test_1]["status"])
        self.assertEqual("Some details about why this test fails",
                         tests[test_1]["reason"])
        self.assertEqual("uxsuccess", tests[test_2]["status"])
