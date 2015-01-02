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

from rally.ui import utils as ui_utils
from rally.verification.tempest import subunit2json


STATUS_MAP = {subunit2json.STATUS_PASS: "pass",
              subunit2json.STATUS_SKIP: "skip",
              subunit2json.STATUS_FAIL: "fail",
              subunit2json.STATUS_ERROR: "error"}


class HtmlOutput(object):
    """Output test results in HTML."""

    def __init__(self, results):
        self.num_passed = results["success"]
        self.num_failed = results["failures"]
        self.num_errors = results["errors"]
        self.num_skipped = results["skipped"]
        self.num_total = results["tests"]
        self.results = results["test_cases"]

    def _generate_report(self):
        tests = []
        for i, name in enumerate(sorted(self.results)):
            test = self.results[name]
            log = test.get("failure", {}).get("log", "")
            status = STATUS_MAP.get(test["status"])
            tests.append({"id": i,
                          "time": test["time"],
                          "desc": name,
                          "output": test["output"] + log,
                          "status": status})

        return dict(tests=tests, total=self.num_total,
                    passed=self.num_passed, failed=self.num_failed,
                    errors=self.num_errors, skipped=self.num_skipped)

    def create_report(self):
        template = ui_utils.get_template("verification/report.mako")
        return template.render(report=self._generate_report())
