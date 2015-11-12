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


class HtmlOutput(object):
    """Output test results in HTML."""

    def __init__(self, results):
        self.results = results

    def _generate_report(self):
        tests = []
        for i, name in enumerate(sorted(self.results["test_cases"])):
            test = self.results["test_cases"][name]
            if "tags" in test:
                name = "%(name)s [%(tags)s]" % {
                    "name": name, "tags": ", ".join(test["tags"])}

            if "traceback" in test:
                output = test["traceback"]
            elif "reason" in test:
                output = test["reason"]
            else:
                output = ""

            tests.append({"id": i,
                          "time": test["time"],
                          "name": name,
                          "output": output,
                          "status": test["status"]})

        return {
            "tests": tests,
            "total": self.results["tests"],
            "time": self.results["time"],
            "success": self.results["success"],
            "failures": self.results["failures"],
            "skipped": self.results["skipped"],
            "expected_failures": self.results["expected_failures"],
            "unexpected_success": self.results["unexpected_success"]}

    def create_report(self):
        template = ui_utils.get_template("verification/report.mako")
        return template.render(report=self._generate_report())
