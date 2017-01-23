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
import json
import re
import xml.etree.ElementTree as ET

from rally.common import version
from rally.ui import utils
from rally.verification import reporter


SKIP_RE = re.compile("Skipped until Bug: ?(?P<bug_number>\d+) is resolved.")
LP_BUG_LINK = "https://launchpad.net/bugs/%s"
TIME_FORMAT_ISO8601 = "%Y-%m-%dT%H:%M:%S%z"


@reporter.configure("json")
class JSONReporter(reporter.VerificationReporter):
    """Generates verification report in JSON format."""
    TIME_FORMAT = TIME_FORMAT_ISO8601

    @classmethod
    def validate(cls, output_destination):
        """Validate destination of report.

        :param output_destination: Destination of report
        """
        # nothing to check :)
        pass

    def _generate(self):
        """Prepare raw report."""

        verifications = collections.OrderedDict()
        tests = {}

        for v in self.verifications:
            verifications[v.uuid] = {
                "started_at": v.created_at.strftime(self.TIME_FORMAT),
                "finished_at": v.updated_at.strftime(self.TIME_FORMAT),
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

                tests[test_id]["by_verification"][v.uuid] = {
                    "status": result["status"],
                    "duration": result["duration"]
                }

                reason = result.get("reason", "")
                if reason:
                    match = SKIP_RE.match(reason)
                    if match:
                        link = LP_BUG_LINK % match.group("bug_number")
                        reason = re.sub(match.group("bug_number"), link,
                                        reason)
                traceback = result.get("traceback", "")
                sep = "\n\n" if reason and traceback else ""
                d = (reason + sep + traceback.strip()) or None
                if d:
                    tests[test_id]["by_verification"][v.uuid]["details"] = d

        return {"verifications": verifications, "tests": tests}

    def generate(self):
        raw_report = json.dumps(self._generate(), indent=4)

        if self.output_destination:
            return {"files": {self.output_destination: raw_report},
                    "open": self.output_destination}
        else:
            return {"print": raw_report}


@reporter.configure("html")
class HTMLReporter(JSONReporter):
    """Generates verification report in HTML format."""
    INCLUDE_LIBS = False

    # "T" separator of ISO 8601 is not user-friendly enough.
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def generate(self):
        report = self._generate()
        uuids = report["verifications"].keys()
        show_comparison_note = False

        for test in report["tests"].values():
            # make as much as possible processing here to reduce processing
            # at JS side
            test["has_details"] = False
            for test_info in test["by_verification"].values():
                if "details" not in test_info:
                    test_info["details"] = None
                elif not test["has_details"]:
                    test["has_details"] = True

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

        raw_report = template.render(data=json.dumps(context),
                                     include_libs=self.INCLUDE_LIBS)

        # in future we will support html_static and will need to save more
        # files
        if self.output_destination:
            return {"files": {self.output_destination: raw_report},
                    "open": self.output_destination}
        else:
            return {"print": raw_report}


@reporter.configure("html-static")
class HTMLStaticReporter(HTMLReporter):
    """Generates verification report in HTML format with embedded JS/CSS."""
    INCLUDE_LIBS = True


@reporter.configure("junit-xml")
class JUnitXMLReporter(reporter.VerificationReporter):
    """Generates verification report in JUnit-XML format."""

    @classmethod
    def validate(cls, output_destination):
        pass

    def _prettify_xml(self, elem, level=0):
        """Adds indents.

        Code of this method was copied from
            http://effbot.org/zone/element-lib.htm#prettyprint

        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._prettify_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def generate(self):
        root = ET.Element("testsuites")

        root.append(ET.Comment("Report is generated by Rally %s at %s" % (
            version.version_string(),
            dt.datetime.utcnow().strftime(TIME_FORMAT_ISO8601))))

        for v in self.verifications:
            verification = ET.SubElement(root, "testsuite", {
                "id": v.uuid,
                "time": str(v.tests_duration),
                "tests": str(v.tests_count),
                "errors": "0",
                "skipped": str(v.skipped),
                "failures": str(v.failures + v.unexpected_success),
                "timestamp": v.created_at.strftime(TIME_FORMAT_ISO8601)
            })
            tests = sorted(v.tests.values(),
                           key=lambda t: (t.get("timestamp", ""), t["name"]))
            for result in tests:
                class_name, name = result["name"].rsplit(".", 1)
                test_case = {
                    "time": result["duration"],
                    "name": name, "class_name": class_name
                }

                test_id = [tag[3:] for tag in result.get("tags", [])
                           if tag.startswith("id-")]
                if test_id:
                    test_case["id"] = test_id[0]
                if "timestamp" in result:
                    test_case["timestamp"] = result["timestamp"]

                test_case_element = ET.SubElement(verification, "testcase",
                                                  test_case)
                if result["status"] == "success":
                    # nothing to add
                    pass
                elif result["status"] == "uxsuccess":
                    # NOTE(andreykurilin): junit doesn't support uxsuccess
                    #   status, so let's display it like "fail" with proper
                    # comment.
                    failure = ET.SubElement(test_case_element, "failure")
                    failure.text = ("It is an unexpected success due to: %s" %
                                    result.get("reason", "Unknown reason"))
                elif result["status"] == "fail":
                    failure = ET.SubElement(test_case_element, "failure")
                    failure.text = result.get("traceback", None)
                elif result["status"] == "xfail":
                    # NOTE(andreykurilin): junit doesn't support xfail status,
                    # so let's display it like "success" with proper comment
                    test_case_element.append(ET.Comment(
                        "It is an expected failure due to: %s" %
                        result.get("reason", "Unknown reason")))
                    trace = result.get("traceback", None)
                    if trace:
                        test_case_element.append(ET.Comment(
                            "Traceback:\n%s" % trace))
                elif result["status"] == "skip":
                    skipped = ET.SubElement(test_case_element, "skipped")
                    skipped.text = result.get("reason", "Unknown reason")
                else:
                    # wtf is it?! we should add validation of results...
                    pass

            self._prettify_xml(root)

        raw_report = ET.tostring(root, encoding="utf-8").decode("utf-8")
        if self.output_destination:
            return {"files": {self.output_destination: raw_report},
                    "open": self.output_destination}
        else:
            return {"print": raw_report}
