# Copyright 2015: Mirantis Inc.
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

from subunit import v2

from rally.common import logging
from rally.utils import encodeutils


def prepare_input_args(func):
    # NOTE(andreykurilin): Variables 'runnable', 'eof', 'route_code' are not
    # used in parser.
    def inner(self, test_id=None, test_status=None, timestamp=None,
              file_name=None, file_bytes=None, mime_type=None, test_tags=None,
              runnable=True, eof=False, route_code=None):
        if not test_id:
            return

        if (test_id.startswith("setUpClass (") or
                test_id.startswith("tearDown (")):
            test_id = test_id[test_id.find("(") + 1:-1]

        tags = _parse_test_tags(test_id)

        if mime_type:
            mime_type, charset = mime_type.split("; ")[:2]
            charset = charset.split("=")[1]
        else:
            charset = None

        func(self, test_id, test_status, timestamp, tags,
             file_name, file_bytes, test_tags, mime_type, charset)

    return inner


def _parse_test_tags(test_id):
    tags = []
    if test_id.find("[") > -1:
        tags = test_id.split("[")[1][:-1].split(",")

    return tags


class SubunitV2StreamResult(object):

    def __init__(self, expected_failures=None, skipped_tests=None, live=False,
                 logger_name=None):
        self._tests = {}
        self._expected_failures = expected_failures or {}
        self._skipped_tests = skipped_tests or {}

        self._live = live
        self._logger = logging.getLogger(logger_name or __name__)

        self._timestamps = {}
        # NOTE(andreykurilin): _first_timestamp and _last_timestamp variables
        # are designed to calculate the total time of tests execution.
        self._first_timestamp = None
        self._last_timestamp = None

        # Store unknown entities and process them later.
        self._unknown_entities = {}
        self._is_parsed = False

    @staticmethod
    def _get_test_name(test_id):
        return test_id.split("[")[0] if test_id.find("[") > -1 else test_id

    def _check_expected_failure(self, test_id):
        if (test_id in self._expected_failures or
                self._get_test_name(test_id) in self._expected_failures):
            if self._tests[test_id]["status"] == "fail":
                self._tests[test_id]["status"] = "xfail"
                if self._expected_failures[test_id]:
                    self._tests[test_id]["reason"] = (
                        self._expected_failures[test_id])
            elif self._tests[test_id]["status"] == "success":
                self._tests[test_id]["status"] = "uxsuccess"

    def _process_skipped_tests(self):
        for t_id in self._skipped_tests.copy():
            if t_id not in self._tests:
                status = "skip"
                name = self._get_test_name(t_id)
                self._tests[t_id] = {"status": status,
                                     "name": name,
                                     "duration": "%.3f" % 0,
                                     "tags": _parse_test_tags(t_id)}
                if self._skipped_tests[t_id]:
                    self._tests[t_id]["reason"] = self._skipped_tests[t_id]
                    status += ": %s" % self._tests[t_id]["reason"]
                if self._live:
                    self._logger.info("{-} %s ... %s" % (name, status))

            self._skipped_tests.pop(t_id)

    def _parse(self):
        # NOTE(andreykurilin): When whole test class is marked as skipped or
        # failed, there is only one event with reason and status. So we should
        # modify all tests of test class manually.
        for test_id in self._unknown_entities:
            known_test_ids = filter(lambda t:
                                    t == test_id or t.startswith(
                                        "%s." % test_id), self._tests)
            for t_id in known_test_ids:
                if self._tests[t_id]["status"] == "init":
                    self._tests[t_id]["status"] = (
                        self._unknown_entities[test_id]["status"])

                if self._unknown_entities[test_id].get("reason"):
                    self._tests[t_id]["reason"] = (
                        self._unknown_entities[test_id]["reason"])
                elif self._unknown_entities[test_id].get("traceback"):
                    self._tests[t_id]["traceback"] = (
                        self._unknown_entities[test_id]["traceback"])

        # decode data
        for test_id in self._tests:
            for file_name in ["traceback", "reason"]:
                # TODO(andreykurilin): decode fields based on mime_type
                if file_name in self._tests[test_id]:
                    self._tests[test_id][file_name] = (
                        encodeutils.safe_decode(
                            self._tests[test_id][file_name]))

        self._is_parsed = True

    @property
    def tests(self):
        if not self._is_parsed:
            self._parse()
        return self._tests

    @property
    def totals(self):
        td = 0
        if self._first_timestamp:
            td = (self._last_timestamp - self._first_timestamp).total_seconds()

        return {"tests_count": len(self.tests),
                "tests_duration": "%.3f" % td,
                "failures": len(self.filter_tests("fail")),
                "skipped": len(self.filter_tests("skip")),
                "success": len(self.filter_tests("success")),
                "unexpected_success": len(self.filter_tests("uxsuccess")),
                "expected_failures": len(self.filter_tests("xfail"))}

    @prepare_input_args
    def status(self, test_id=None, test_status=None, timestamp=None, tags=None,
               file_name=None, file_bytes=None, worker=None, mime_type=None,
               charset=None):
        if timestamp:
            if not self._first_timestamp:
                self._first_timestamp = timestamp
            self._last_timestamp = timestamp

        if test_status == "exists":
            self._tests[test_id] = {"status": "init",
                                    "name": self._get_test_name(test_id),
                                    "duration": "%.3f" % 0,
                                    "tags": tags if tags else []}
        elif test_id in self._tests:
            if test_status == "inprogress":
                # timestamp of test start
                self._timestamps[test_id] = timestamp
                self._tests[test_id]["timestamp"] = timestamp.strftime(
                    "%Y-%m-%dT%H:%M:%S%z")
            elif test_status:
                self._tests[test_id]["duration"] = "%.3f" % (
                    timestamp - self._timestamps[test_id]).total_seconds()
                self._tests[test_id]["status"] = test_status

                self._check_expected_failure(test_id)
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

        if self._skipped_tests:
            self._process_skipped_tests()

        if self._live and test_status not in (None, "exists", "inprogress"):
            duration = ""
            if test_id in self._tests:
                status = self._tests[test_id]["status"]
                duration = " [%ss]" % self._tests[test_id]["duration"]
            else:
                status = test_status

            status += duration

            if "xfail" in status or "skip" in status:
                if test_id in self._tests:
                    reason = self._tests[test_id].get("reason")
                else:
                    reason = self._unknown_entities[test_id].get("reason")
                if reason:
                    status += ": %s" % reason

            w = "{%s} " % worker.pop().split("-")[1] if worker else "-"
            self._logger.info("%s ... %s"
                              % (w + self._get_test_name(test_id), status))

    def filter_tests(self, status):
        """Filter tests by given status."""
        filtered_tests = {}
        for test in self.tests:
            if self.tests[test]["status"] == status:
                filtered_tests[test] = self.tests[test]

        return filtered_tests


def parse(stream, expected_failures=None, skipped_tests=None, live=False,
          logger_name=None):
    results = SubunitV2StreamResult(expected_failures, skipped_tests, live,
                                    logger_name)
    v2.ByteStreamToStreamResult(stream, "non-subunit").run(results)

    return results


def parse_file(filename, expected_failures=None, skipped_tests=None,
               live=False, logger_name=None):
    with open(filename, "rb") as stream:
        return parse(stream, expected_failures, skipped_tests, live,
                     logger_name)
