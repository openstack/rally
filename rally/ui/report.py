# Copyright 2016: Mirantis Inc.
# All Rights Reserved.
#
#    Author: Oleksandr Savatieiev osavatieiev@mirantis.com
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

import csv
import io
import json
import re

from jinja2 import utils as jinja_utils

from rally.ui import utils


class VerificationReport(object):

    SKIP_RE = re.compile(
        "Skipped until Bug: ?(?P<bug_number>\d+) is resolved.")
    LP_BUG_LINK = "<a href='https://launchpad.net/bugs/{0}'>{0}</a>"

    def __init__(self, verifications):
        self._runs = verifications
        self._uuids = list(verifications.keys())

        # NOTE(amaretskiy): make aggregated list of all tests
        tests = {}
        for uuid, verification in self._runs.items():
            for name, test in verification["tests"].items():
                if name not in tests:
                    # NOTE(ylobankov): It is more convenient to see resource
                    #                  ID at the first place in the report.
                    tags = sorted(test["tags"], reverse=True,
                                  key=lambda tag: tag.startswith("id-"))
                    tests[name] = {"name": name,
                                   "tags": tags,
                                   "by_verification": {},
                                   "has_details": False}

                tests[name]["by_verification"][uuid] = {
                    "status": test["status"],
                    "duration": test["duration"],
                    "details": test["details"]
                }

                if test["details"]:
                    tests[name]["has_details"] = True

                    match = self.SKIP_RE.match(test["details"])
                    if match:
                        href = self.LP_BUG_LINK.format(
                            match.group("bug_number"))
                        test["details"] = re.sub(
                            match.group("bug_number"), href, test["details"])

                    test["details"] = jinja_utils.escape(test["details"])

        self._tests = list(tests.values())

    def to_html(self):
        """Make HTML report."""
        template = utils.get_template("verification/report.html")
        context = {"uuids": self._uuids, "verifications": self._runs,
                   "tests": self._tests}
        return template.render(data=json.dumps(context), include_libs=False)

    def to_json(self, indent=4):
        """Make JSON report."""
        return json.dumps(self._tests, indent=indent)

    def to_csv(self, **kwargs):
        """Make CSV report."""
        header = ["test name", "tags", "has errors"]
        for uuid in self._uuids:
            header.extend(["%s status" % uuid, "%s duration" % uuid])
        rows = [header]
        for test in self._tests:
            row = [test["name"], " ".join(test["tags"])]
            for uuid in self._uuids:
                if uuid not in test["by_verification"]:
                    row.extend([None, None])
                    continue
                row.append(test["by_verification"][uuid]["status"])
                row.append(test["by_verification"][uuid]["duration"])
            rows.append(row)

        with io.BytesIO() as stream:
            csv.writer(stream, **kwargs).writerows(rows)
            return stream.getvalue()
