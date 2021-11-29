# Copyright 2018:  ZTE Inc.
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

import subprocess

import testtools

from rally.utils import encodeutils


class CLITestCase(testtools.TestCase):

    def test_rally_cli(self):
        try:
            subprocess.check_output(["rally"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = encodeutils.safe_decode(e.output)
        else:
            self.fail("It should ve non-zero exit code.")

        self.assertIn("the following arguments are required: category", output)

    def test_version_cli(self):
        output = encodeutils.safe_decode(
            subprocess.check_output(["rally", "version"],
                                    stderr=subprocess.STDOUT))
        self.assertIn("Rally version:", output)
