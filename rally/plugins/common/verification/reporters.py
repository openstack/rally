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

from rally.common import utils
from rally.common import version
from rally import consts
from rally.ui import utils as ui_utils
from rally.verification import reporter


SKIP_RE = re.compile("Skipped until Bug: ?(?P<bug_number>\d+) is resolved.")
LP_BUG_LINK = "https://launchpad.net/bugs/%s"
TIME_FORMAT = consts.TimeFormat.ISO8601


@reporter.configure("json")
class JSONReporter(reporter.VerificationReporter):
    """Generates verification report in JSON format.

    An example of the report (All dates, numbers, names appearing in this
    example are fictitious. Any resemblance to real things is purely
    coincidental):

      .. code-block:: json

        {"verifications": {
            "verification-uuid-1": {
                "status": "finished",
                "skipped": 1,
                "started_at": "2001-01-01T00:00:00",
                "finished_at": "2001-01-01T00:05:00",
                "tests_duration": 5,
                "run_args": {
                    "pattern": "set=smoke",
                    "xfail_list": {"some.test.TestCase.test_xfail":
                                       "Some reason why it is expected."},
                    "skip_list": {"some.test.TestCase.test_skipped":
                                      "This test was skipped intentionally"},
                },
                "success": 1,
                "expected_failures": 1,
                "tests_count": 3,
                "failures": 0,
                "unexpected_success": 0
            },
            "verification-uuid-2": {
                "status": "finished",
                "skipped": 1,
                "started_at": "2002-01-01T00:00:00",
                "finished_at": "2002-01-01T00:05:00",
                "tests_duration": 5,
                "run_args": {
                    "pattern": "set=smoke",
                    "xfail_list": {"some.test.TestCase.test_xfail":
                                       "Some reason why it is expected."},
                    "skip_list": {"some.test.TestCase.test_skipped":
                                      "This test was skipped intentionally"},
                },
                "success": 1,
                "expected_failures": 1,
                "tests_count": 3,
                "failures": 1,
                "unexpected_success": 0
            }
         },
         "tests": {
            "some.test.TestCase.test_foo[tag1,tag2]": {
                "name": "some.test.TestCase.test_foo",
                "tags": ["tag1","tag2"],
                "by_verification": {
                    "verification-uuid-1": {
                        "status": "success",
                        "duration": "1.111"
                    },
                    "verification-uuid-2": {
                        "status": "success",
                        "duration": "22.222"
                    }
                }
            },
            "some.test.TestCase.test_skipped[tag1]": {
                "name": "some.test.TestCase.test_skipped",
                "tags": ["tag1"],
                "by_verification": {
                    "verification-uuid-1": {
                        "status": "skipped",
                        "duration": "0",
                        "details": "Skipped until Bug: 666 is resolved."
                    },
                    "verification-uuid-2": {
                        "status": "skipped",
                        "duration": "0",
                        "details": "Skipped until Bug: 666 is resolved."
                    }
                }
            },
            "some.test.TestCase.test_xfail": {
                "name": "some.test.TestCase.test_xfail",
                "tags": [],
                "by_verification": {
                    "verification-uuid-1": {
                        "status": "xfail",
                        "duration": "3",
                        "details": "Some reason why it is expected.\\n\\n"
                            "Traceback (most recent call last): \\n"
                            "  File "fake.py", line 13, in <module>\\n"
                            "    yyy()\\n"
                            "  File "fake.py", line 11, in yyy\\n"
                            "    xxx()\\n"
                            "  File "fake.py", line 8, in xxx\\n"
                            "    bar()\\n"
                            "  File "fake.py", line 5, in bar\\n"
                            "    foo()\\n"
                            "  File "fake.py", line 2, in foo\\n"
                            "    raise Exception()\\n"
                            "Exception"
                    },
                    "verification-uuid-2": {
                        "status": "xfail",
                        "duration": "3",
                        "details": "Some reason why it is expected.\\n\\n"
                            "Traceback (most recent call last): \\n"
                            "  File "fake.py", line 13, in <module>\\n"
                            "    yyy()\\n"
                            "  File "fake.py", line 11, in yyy\\n"
                            "    xxx()\\n"
                            "  File "fake.py", line 8, in xxx\\n"
                            "    bar()\\n"
                            "  File "fake.py", line 5, in bar\\n"
                            "    foo()\\n"
                            "  File "fake.py", line 2, in foo\\n"
                            "    raise Exception()\\n"
                            "Exception"
                    }
                }
            },
            "some.test.TestCase.test_failed": {
                "name": "some.test.TestCase.test_failed",
                "tags": [],
                "by_verification": {
                    "verification-uuid-2": {
                        "status": "fail",
                        "duration": "4",
                        "details": "Some reason why it is expected.\\n\\n"
                            "Traceback (most recent call last): \\n"
                            "  File "fake.py", line 13, in <module>\\n"
                            "    yyy()\\n"
                            "  File "fake.py", line 11, in yyy\\n"
                            "    xxx()\\n"
                            "  File "fake.py", line 8, in xxx\\n"
                            "    bar()\\n"
                            "  File "fake.py", line 5, in bar\\n"
                            "    foo()\\n"
                            "  File "fake.py", line 2, in foo\\n"
                            "    raise Exception()\\n"
                            "Exception"
                        }
                    }
                }
            }
        }

    """

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
                "started_at": v.created_at.strftime(TIME_FORMAT),
                "finished_at": v.updated_at.strftime(TIME_FORMAT),
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

        template = ui_utils.get_template("verification/report.html")
        context = {"uuids": list(uuids),
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
    """Generates verification report in JUnit-XML format.

    An example of the report (All dates, numbers, names appearing in this
    example are fictitious. Any resemblance to real things is purely
    coincidental):

      .. code-block:: xml

        <testsuites>
          <!--Report is generated by Rally 0.8.0 at 2002-01-01T00:00:00-->
          <testsuite id="verification-uuid-1"
                     tests="9"
                     time="1.111"
                     errors="0"
                     failures="3"
                     skipped="0"
                     timestamp="2001-01-01T00:00:00">
            <testcase classname="some.test.TestCase"
                      name="test_foo"
                      time="8"
                      timestamp="2001-01-01T00:01:00" />
            <testcase classname="some.test.TestCase"
                      name="test_skipped"
                      time="0"
                      timestamp="2001-01-01T00:02:00">
              <skipped>Skipped until Bug: 666 is resolved.</skipped>
            </testcase>
            <testcase classname="some.test.TestCase"
                      name="test_xfail"
                      time="3"
                      timestamp="2001-01-01T00:03:00">
              <!--It is an expected failure due to: something-->
              <!--Traceback:
        HEEELP-->
            </testcase>
            <testcase classname="some.test.TestCase"
                      name="test_uxsuccess"
                      time="3"
                      timestamp="2001-01-01T00:04:00">
              <failure>
                  It is an unexpected success. The test should fail due to:
                  It should fail, I said!
              </failure>
            </testcase>
          </testsuite>
          <testsuite id="verification-uuid-2"
                     tests="99"
                     time="22.222"
                     errors="0"
                     failures="33"
                     skipped="0"
                     timestamp="2002-01-01T00:00:00">
            <testcase classname="some.test.TestCase"
                      name="test_foo"
                      time="8"
                      timestamp="2001-02-01T00:01:00" />
            <testcase classname="some.test.TestCase"
                      name="test_failed"
                      time="8"
                      timestamp="2001-02-01T00:02:00">
              <failure>HEEEEEEELP</failure>
            </testcase>
            <testcase classname="some.test.TestCase"
                      name="test_skipped"
                      time="0"
                      timestamp="2001-02-01T00:03:00">
              <skipped>Skipped until Bug: 666 is resolved.</skipped>
            </testcase>
            <testcase classname="some.test.TestCase"
                      name="test_xfail"
                      time="4"
                      timestamp="2001-02-01T00:04:00">
              <!--It is an expected failure due to: something-->
              <!--Traceback:
        HEEELP-->
            </testcase>
          </testsuite>
        </testsuites>

    """

    @classmethod
    def validate(cls, output_destination):
        pass

    def generate(self):
        root = ET.Element("testsuites")

        root.append(ET.Comment("Report is generated by Rally %s at %s" % (
            version.version_string(),
            dt.datetime.utcnow().strftime(TIME_FORMAT))))

        for v in self.verifications:
            verification = ET.SubElement(root, "testsuite", {
                "id": v.uuid,
                "time": str(v.tests_duration),
                "tests": str(v.tests_count),
                "errors": "0",
                "skipped": str(v.skipped),
                "failures": str(v.failures + v.unexpected_success),
                "timestamp": v.created_at.strftime(TIME_FORMAT)
            })
            tests = sorted(v.tests.values(),
                           key=lambda t: (t.get("timestamp", ""), t["name"]))
            for result in tests:
                class_name, name = result["name"].rsplit(".", 1)
                test_case = {
                    "time": result["duration"],
                    "name": name, "classname": class_name
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
                    failure.text = ("It is an unexpected success. The test "
                                    "should fail due to: %s" %
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

            utils.prettify_xml(root)

        raw_report = ET.tostring(root, encoding="utf-8").decode("utf-8")
        if self.output_destination:
            return {"files": {self.output_destination: raw_report},
                    "open": self.output_destination}
        else:
            return {"print": raw_report}
