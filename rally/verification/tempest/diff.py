# Copyright 2014 Dell Inc.
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

import json

from rally.verification.tempest import compare2html


class Diff(object):

    def __init__(self, test_cases1, test_cases2, threshold):
        """Compare two verification results.

        Compares two verification results and emits
        desired output, csv, html, json or pprint.

        :param test_cases1: older verification json
        :param test_cases2: newer verification json
        :param threshold: test time difference percentage threshold

        """
        self.threshold = threshold
        self.diffs = self._compare(test_cases1, test_cases2)

    def _compare(self, tc1, tc2):
        """Compare two verification results.

        :param tc1: first verification test cases json
        :param tc2: second verification test cases json

        Typical test case json schema:
            "test_case_key": {
                "traceback": "", # exists only for "fail" status
                "reason": "",    # exists only for "skip" status
                "name": "",
                "status": "",
                "time": 0.0
            }
        """
        diffs = []
        names1 = set(tc1.keys())
        names2 = set(tc2.keys())

        common_tests = list(names1.intersection(names2))
        removed_tests = list(names1.difference(common_tests))
        new_tests = list(names2.difference(common_tests))

        for name in removed_tests:
            diffs.append({"type": "removed_test", "test_name": name})
        for name in new_tests:
            diffs.append({"type": "new_test", "test_name": name})
        for name in common_tests:
                diffs.extend(self._diff_values(name, tc1[name], tc2[name]))

        return diffs

    def _diff_values(self, name, result1, result2):
        fields = ["status", "time", "traceback", "reason"]
        diffs = []
        for field in fields:
            val1 = result1.get(field, 0)
            val2 = result2.get(field, 0)
            if val1 != val2:
                if field == "time":
                    max_ = max(float(val1), float(val2))
                    min_ = min(float(val1), float(val2))
                    time_threshold = ((max_ - min_) / (min_ or 1)) * 100
                    if time_threshold < self.threshold:
                        continue

                diffs.append({
                    "field": field,
                    "type": "value_changed",
                    "test_name": name,
                    "val1": val1,
                    "val2": val2
                })
        return diffs

    def to_csv(self):
        rows = (("Type", "Field", "Value 1", "Value 2", "Test Name"),)
        for res in self.diffs:
            row = (res.get("type"), res.get("field", ""),
                   res.get("val1", ""), res.get("val2", ""),
                   res.get("test_name"))
            rows = rows + (row,)
        return rows

    def to_json(self):
        return json.dumps(self.diffs, sort_keys=True, indent=4)

    def to_html(self):
        return compare2html.create_report(self.diffs)
