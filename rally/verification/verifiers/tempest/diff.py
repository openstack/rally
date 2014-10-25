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

import compare2html


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
                "failure": {
                    "log": ""
                },
                "name": "",
                "output": "",
                "status": "",
                "time": 0.0
            }
        """
        names1 = sorted(tc1)
        names2 = sorted(tc2)

        diffs = []
        i = j = 0
        while i < len(names1) and j < len(names2):
            name1 = names1[i] if i < len(names1) else None
            name2 = names2[j] if j < len(names2) else None
            if name1 and name2 and name1 == name2:
                diffs.extend(self._diff_values(name1, tc1[name1], tc2[name2]))
                i += 1
                j += 1

            elif (not name1) or (name1 > name2):
                diffs.append({"type": "new_test", "test_name": name2})
                j += 1
            else:
                diffs.append({"type": "removed_test", "test_name": name1})
                i += 1

        return diffs

    def _diff_values(self, name, result1, result2):
        th = self.threshold
        fields = ["status", "time", "output"]
        diffs = []
        for field in fields:
            val1 = result1[field]
            val2 = result2[field]
            if val1 != val2 and not (field == "time"
                                     and abs(((val2 - val1) / val1) * 100)
                                     < th):
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
