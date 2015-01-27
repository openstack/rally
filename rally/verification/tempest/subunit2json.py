# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import collections
import datetime
import errno
import io
import os
import tempfile
import traceback

from oslo_serialization import jsonutils
from oslo_utils import timeutils
import subunit
import testtools


STATUS_PASS = "OK"
STATUS_SKIP = "SKIP"
STATUS_FAIL = "FAIL"
STATUS_ERROR = "ERROR"


class JsonOutput(testtools.TestResult):
    """Output test results in Json."""

    def __init__(self, results_file):
        super(JsonOutput, self).__init__()
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        self.skip_count = 0
        self.total_time = 0
        self.test_cases = {}
        self.results_file = results_file

    def _format_result(self, name, time, status, output, failure=None):
        # We do not need `setUpClass' in test name
        if name[:12] == "setUpClass (" and name[-1] == ")":
            name = name[12:-1]

        self.test_cases[name] = {"name": name, "status": status,
                                 "time": time, "output": output}
        if failure:
            self.test_cases[name].update({"failure": failure})

    def _test_time(self, before, after):
        return timeutils.delta_seconds(before, after)

    def addSuccess(self, test):
        self.success_count += 1
        test_time = self._test_time(test._timestamps[0],
                                    test._timestamps[1])
        self.total_time += test_time
        output = test.shortDescription()
        if output is None:
            output = test.id()
        self._format_result(test.id(), test_time, STATUS_PASS, output)

    def addSkip(self, test, err):
        output = test.shortDescription()
        test_time = self._test_time(test._timestamps[0],
                                    test._timestamps[1])
        self.total_time += test_time

        if output is None:
            output = test.id()
        self.skip_count += 1
        self._format_result(test.id(), test_time, STATUS_SKIP, output)

    def addError(self, test, err):
        output = test.shortDescription()
        test_time = self._test_time(test._timestamps[0],
                                    test._timestamps[1])
        self.total_time += test_time
        if output is None:
            output = test.id()
        else:
            self.error_count += 1
            _exc_str = self.formatErr(err)
            failure_type = "%s.%s" % (err[0].__module__, err[1].__name__)
            self._format_result(test.id(), test_time, STATUS_ERROR, output,
                                failure={"type": failure_type,
                                         "log": _exc_str})

    def addFailure(self, test, err):
        self.failure_count += 1
        test_time = self._test_time(test._timestamps[0],
                                    test._timestamps[1])
        self.total_time += test_time
        _exc_str = self.formatErr(err)
        output = test.shortDescription()
        if output is None:
            output = test.id()
        failure_type = "%s.%s" % (err[0].__module__, err[0].__name__)
        self._format_result(test.id(), test_time, STATUS_FAIL, output,
                            failure={"type": failure_type, "log": _exc_str})

    def formatErr(self, err):
        exctype, value, tb = err
        return "".join(traceback.format_exception(exctype, value, tb))

    def stopTestRun(self):
        super(JsonOutput, self).stopTestRun()
        self.stopTime = datetime.datetime.now()
        total_count = (self.success_count + self.failure_count +
                       self.error_count + self.skip_count)
        total = {"tests": total_count, "errors": self.error_count,
                 "skipped": self.skip_count, "success": self.success_count,
                 "failures": self.failure_count, "time": self.total_time}
        if self.results_file:
            with open(self.results_file, "wb") as results_file:
                output = jsonutils.dumps({"total": total,
                                          "test_cases": self.test_cases})
                results_file.write(output)

    def startTestRun(self):
        super(JsonOutput, self).startTestRun()


class FileAccumulator(testtools.StreamResult):

    def __init__(self):
        super(FileAccumulator, self).__init__()
        self.route_codes = collections.defaultdict(io.BytesIO)

    def status(self, **kwargs):
        if kwargs.get("file_name") != "stdout":
            return
        file_bytes = kwargs.get("file_bytes")
        if not file_bytes:
            return
        route_code = kwargs.get("route_code")
        stream = self.route_codes[route_code]
        stream.write(file_bytes)


def main(subunit_log_file):
    fd, results_file = tempfile.mkstemp()
    result = JsonOutput(results_file)
    stream = open(subunit_log_file, "rb")

    # Feed the subunit stream through both a V1 and V2 parser.
    # Depends on having the v2 capable libraries installed.
    # First V2.
    # Non-v2 content and captured non-test output will be presented as file
    # segments called stdout.
    suite = subunit.ByteStreamToStreamResult(stream, non_subunit_name="stdout")
    # The JSON output code is in legacy mode.
    raw_result = testtools.StreamToExtendedDecorator(result)
    # Divert non-test output
    accumulator = FileAccumulator()
    result = testtools.StreamResultRouter(raw_result)
    result.add_rule(accumulator, "test_id", test_id=None)
    result.startTestRun()
    suite.run(result)
    # Now reprocess any found stdout content as V1 subunit
    for bytes_io in accumulator.route_codes.values():
        bytes_io.seek(0)
        suite = subunit.ProtocolTestCase(bytes_io)
        suite.run(result)
    result.stopTestRun()
    with open(results_file, "rb") as temp_results_file:
        data = temp_results_file.read()
    try:
        os.unlink(results_file)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    return data
