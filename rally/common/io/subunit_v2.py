#
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
#

from oslo_utils import encodeutils
from subunit import v2


def total_seconds(td):
    """Return the total number of seconds contained in the duration.

    NOTE(andreykurilin): python 2.6 compatible method
    """
    if hasattr(td, "total_seconds"):
        s = td.total_seconds()
    else:
        # NOTE(andreykurilin): next calculation is proposed in python docs
        # https://docs.python.org/2/library/datetime.html#datetime.timedelta.total_seconds
        s = (td.microseconds +
             (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10.0 ** 6
    return "%.3f" % s


def preparse_input_args(func):
    def inner(self, test_id=None, test_status=None, test_tags=None,
              runnable=True, file_name=None, file_bytes=None, eof=False,
              mime_type=None, route_code=None, timestamp=None):
        # NOTE(andreykurilin): Variables 'runnable', 'eof', 'route_code' are
        # not used in parser. Variable 'test_tags' is used to store workers
        # info, which is not helpful in parser.

        if not test_id:
            return

        if (test_id.startswith("setUpClass (") or
                test_id.startswith("tearDown (")):
            test_id = test_id[test_id.find("(") + 1:-1]
        if test_id.find("[") > -1:
            tags = test_id.split("[")[1][:-1].split(",")
        else:
            tags = []

        if mime_type:
            mime_type, charset = mime_type.split("; ")[:2]
            charset = charset.split("=")[1]
        else:
            charset = None

        func(self, test_id, test_status, tags, file_name, file_bytes,
             mime_type, timestamp, charset)
    return inner


class SubunitV2StreamResult(object):
    """A test result for reporting the activity of a test run."""

    def __init__(self, expected_failures=None):
        self._tests = {}
        self._expected_failures = expected_failures or {}
        self._timestamps = {}
        # NOTE(andreykurilin): _first_timestamp and _last_timestamp vars are
        #   designed to calculate total time of tests executions
        self._first_timestamp = None
        self._last_timestamp = None
        # let's save unknown entities and process them after main test case
        self._unknown_entities = {}
        self._is_parsed = False

    def _post_parse(self):
        # parse unknown entities
        for test_id in self._unknown_entities:
            # NOTE(andreykurilin): When whole TestCase is marked as skipped
            # or failed, there is only one event with reason and status, so
            # we should modify all tests of TestCase manually.
            matcher = lambda i: i == test_id or i.startswith("%s." % test_id)
            known_ids = filter(matcher, self._tests)
            for id_ in known_ids:
                if self._tests[id_]["status"] == "init":
                    self._tests[id_]["status"] = (
                        self._unknown_entities[test_id]["status"])
                if self._unknown_entities[test_id].get("reason"):
                    self._tests[id_]["reason"] = (
                        self._unknown_entities[test_id]["reason"])
                elif self._unknown_entities[test_id].get("traceback"):
                    self._tests[id_]["traceback"] = (
                        self._unknown_entities[test_id]["traceback"])

        # parse expected failures
        for test_id in self._expected_failures:
            if self._tests.get(test_id):
                if self._tests[test_id]["status"] == "fail":
                    self._tests[test_id]["status"] = "xfail"
                    if self._expected_failures[test_id]:
                        self._tests[test_id]["reason"] = (
                            self._expected_failures[test_id])
                elif self._tests[test_id]["status"] == "success":
                    self._tests[test_id]["status"] = "uxsuccess"

        # decode data
        for test_id in self._tests:
            for file_name in ["traceback", "reason"]:
                # FIXME(andreykurilin): decode fields based on mime_type
                if file_name in self._tests[test_id]:
                    self._tests[test_id][file_name] = (
                        encodeutils.safe_decode(
                            self._tests[test_id][file_name]))

        self._is_parsed = True

    @property
    def tests(self):
        if not self._is_parsed:
            self._post_parse()
        return self._tests

    @property
    def total(self):
        total_time = 0
        if self._first_timestamp:
            total_time = total_seconds(
                self._last_timestamp - self._first_timestamp)
        return {"tests": len(self.tests),
                "time": total_time,
                "failures": len(self.filter_tests("fail")),
                "skipped": len(self.filter_tests("skip")),
                "success": len(self.filter_tests("success")),
                "unexpected_success": len(self.filter_tests("uxsuccess")),
                "expected_failures": len(self.filter_tests("xfail"))}

    @preparse_input_args
    def status(self, test_id=None, test_status=None, tags=None,
               file_name=None, file_bytes=None, mime_type=None,
               timestamp=None, charset=None):
        if test_status == "exists":
            self._tests[test_id] = {"status": "init",
                                    "name": (test_id.split("[")[0]
                                             if test_id.find("[") > -1
                                             else test_id),
                                    "time": "%.3f" % 0}
            if tags:
                self._tests[test_id]["tags"] = tags
        elif test_id in self._tests:
            if test_status == "inprogress":
                self._timestamps[test_id] = timestamp
            elif test_status:
                self._tests[test_id]["time"] = total_seconds(
                    timestamp - self._timestamps[test_id])
                self._tests[test_id]["status"] = test_status
            else:
                if file_name in ["traceback", "reason"]:
                    if file_name not in self._tests[test_id]:
                        self._tests[test_id][file_name] = file_bytes
                    else:
                        self._tests[test_id][file_name] += file_bytes
        else:
            self._unknown_entities.setdefault(test_id, {"name": test_id})
            self._unknown_entities[test_id]["status"] = test_status
            if file_name in ["traceback", "reason"]:
                if file_name not in self._unknown_entities[test_id]:
                    self._unknown_entities[test_id][file_name] = file_bytes
                else:
                    self._unknown_entities[test_id][file_name] += file_bytes

        if timestamp:
            if not self._first_timestamp:
                self._first_timestamp = timestamp
            self._last_timestamp = timestamp

    def filter_tests(self, status):
        """Filter results by given status."""
        filtered_tests = {}
        for test in self.tests:
            if self.tests[test]["status"] == status:
                filtered_tests[test] = self.tests[test]

        return filtered_tests


def parse_results_file(filename, expected_failures=None):
    with open(filename, "rb") as source:
        results = SubunitV2StreamResult(expected_failures)
        v2.ByteStreamToStreamResult(
            source=source, non_subunit_name="non-subunit").run(results)
        return results
