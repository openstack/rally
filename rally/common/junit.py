# Copyright 2015: eNovance
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

import xml.etree.ElementTree as ET


class JUnit(object):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"

    def __init__(self, test_suite_name):
        self.test_suite_name = test_suite_name
        self.test_cases = []
        self.n_tests = 0
        self.n_failures = 0
        self.n_errors = 0
        self.total_time = 0.0

    def add_test(self, test_name, time, outcome=SUCCESS, message=""):
        class_name, name = test_name.split(".", 1)
        self.test_cases.append({
            "classname": class_name,
            "name": name,
            "time": str("%.2f" % time),
            "outcome": outcome,
            "message": message
        })

        if outcome == JUnit.FAILURE:
            self.n_failures += 1
        elif outcome == JUnit.ERROR:
            self.n_errors += 1
        elif outcome != JUnit.SUCCESS:
            raise ValueError("Unexpected outcome %s" % outcome)

        self.n_tests += 1
        self.total_time += time

    def to_xml(self):
        xml = ET.Element("testsuite", {
            "name": self.test_suite_name,
            "tests": str(self.n_tests),
            "time": str("%.2f" % self.total_time),
            "failures": str(self.n_failures),
            "errors": str(self.n_errors),
        })
        for test_case in self.test_cases:
            outcome = test_case.pop("outcome")
            message = test_case.pop("message")
            if outcome in [JUnit.FAILURE, JUnit.ERROR]:
                sub = ET.SubElement(xml, "testcase", test_case)
                sub.append(ET.Element(outcome, {"message": message}))
            else:
                xml.append(ET.Element("testcase", test_case))
        return ET.tostring(xml, encoding="utf-8").decode("utf-8")
