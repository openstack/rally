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

import collections
import copy
import json
import re

from rally.ui import utils


SKIP_RE = re.compile("Skipped until Bug: ?(?P<bug_number>\d+) is resolved.")
LP_BUG_LINK = "https://launchpad.net/bugs/%s"


class VerificationReport(object):
    """Generate a report for a verification or a few verifications."""

    def __init__(self, verifications_list):
        verifications = collections.OrderedDict()
        tests = {}

        for v in verifications_list:
            verifications[v.uuid] = {
                "started_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "finished_at": v.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "status": v.status,
                "run_args": v.run_args,
                "tests_count": v.tests_count,
                "tests_duration": v.tests_duration,
                "skipped": v.skipped,
                "success": v.success,
                "expected_failures": v.expected_failures,
                "unexpected_success": v.unexpected_success,
                "failures": v.failures,
            }

            for test_id, result in v.tests.items():
                if test_id not in tests:
                    # NOTE(ylobankov): It is more convenient to see test ID
                    #                  at the first place in the report.
                    tags = sorted(result.get("tags", []), reverse=True,
                                  key=lambda tag: tag.startswith("id-"))
                    tests[test_id] = {"tags": tags,
                                      "name": result["name"],
                                      "by_verification": {}}

                reason = result.get("reason", "")
                if reason:
                    match = SKIP_RE.match(reason)
                    if match:
                        link = LP_BUG_LINK % match.group("bug_number")
                        reason = re.sub(match.group("bug_number"), link,
                                        reason)
                traceback = result.get("traceback", "")
                sep = "\n\n" if reason and traceback else ""
                details = (reason + sep + traceback.strip()) or None

                tests[test_id]["by_verification"][v.uuid] = {
                    "status": result["status"],
                    "duration": result["duration"],
                    "details": details
                }

        self.report = {"verifications": verifications, "tests": tests}

    def to_html(self):
        """Generate HTML report."""
        report = copy.deepcopy(self.report)
        uuids = report["verifications"].keys()
        show_comparison_note = False

        for test in report["tests"].values():
            # make as much as possible processing here to reduce processing
            # at JS side
            test["has_details"] = False
            for test_info in test["by_verification"].values():
                if test_info["details"]:
                    test["has_details"] = True
                    break

            durations = []
            # iter by uuids to store right order for comparison
            for uuid in uuids:
                if uuid in test["by_verification"]:
                    durations.append(test["by_verification"][uuid]["duration"])
                    if float(durations[-1]) < 0.001:
                        durations[-1] = "0"
                        # not to display such little duration in the report
                        test["by_verification"][uuid]["duration"] = ""

                    if len(durations) > 1 and not (
                            durations[0] == "0" and durations[-1] == "0"):
                        # compare result with result of the first verification
                        diff = float(durations[-1]) - float(durations[0])
                        result = "%s (" % durations[-1]
                        if diff >= 0:
                            result += "+"
                        result += "%s)" % diff
                        test["by_verification"][uuid]["duration"] = result

            if not show_comparison_note and len(durations) > 2:
                # NOTE(andreykurilin): only in case of comparison of more
                #   than 2 results of the same test we should display a note
                #   about the comparison strategy
                show_comparison_note = True

        template = utils.get_template("verification/report.html")
        context = {"uuids": uuids,
                   "verifications": report["verifications"],
                   "tests": report["tests"],
                   "show_comparison_note": show_comparison_note}

        return template.render(data=json.dumps(context), include_libs=False)

    def to_json(self, indent=4):
        """Generate JSON report."""
        return json.dumps(self.report, indent=indent)
