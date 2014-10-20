# Copyright 2014: Mirantis Inc.
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
import unittest

from tests.functional import utils


class VerifyTestCase(unittest.TestCase):

    def setUp(self):
        super(VerifyTestCase, self).setUp()
        self.rally = utils.Rally()

    def _verify_start_and_get_results_in_json(self, set_name):
        self.rally("verify start %s" % set_name)
        results = json.loads(self.rally("verify results --json"))

        failed_tests = results["failures"] * 100.0 / results["tests"]
        if failed_tests >= 50:
            self.fail("Number of failed tests more than 50%.")

        show_output = self.rally("verify show")

        total_raw = show_output.split("\n").pop(5)[1:-1].replace(" ", "")
        total = total_raw.split('|')

        self.assertEqual(set_name, total[2])
        self.assertEqual(results["tests"], int(total[3]))
        self.assertEqual(results["failures"], int(total[4]))
        self.assertEqual("finished", total[6])

    def test_image_set(self):
        self._verify_start_and_get_results_in_json("image")

    def test_smoke_set(self):
        self._verify_start_and_get_results_in_json("smoke")
