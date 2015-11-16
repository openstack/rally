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

import re

from jinja2 import utils

from rally.ui import utils as ui_utils

SKIP_RE = re.compile("Skipped until Bug: ?(?P<bug_number>\d+) is resolved.")
LAUNCHPAD_BUG_LINK = "<a href='https://launchpad.net/bugs/{0}'>{0}</a>"


def generate_report(results):
    """Generates HTML report from test results in JSON format."""
    tests = []
    for i, name in enumerate(sorted(results["test_cases"])):
        test = results["test_cases"][name]
        if "tags" in test:
            name = "%(name)s [%(tags)s]" % {"name": name,
                                            "tags": ", ".join(test["tags"])}
        if "traceback" in test:
            output = utils.escape(test["traceback"])
        elif "reason" in test:
            matcher = SKIP_RE.match(test["reason"])
            if matcher:
                href = LAUNCHPAD_BUG_LINK.format(matcher.group("bug_number"))
                output = re.sub(matcher.group("bug_number"), href,
                                test["reason"])
            else:
                output = utils.escape(test["reason"])
        else:
            output = ""

        tests.append({"id": i,
                      "time": test["time"],
                      "name": name,
                      "output": output,
                      "status": test["status"]})

    template = ui_utils.get_template("verification/report.mako")
    return template.render(report={
        "tests": tests,
        "total": results["tests"],
        "time": results["time"],
        "success": results["success"],
        "failures": results["failures"],
        "skipped": results["skipped"],
        "expected_failures": results["expected_failures"],
        "unexpected_success": results["unexpected_success"]})
