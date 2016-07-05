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

import difflib
import os

from oslo_utils import encodeutils

import rally
from rally.cli import cliutils
from tests.unit import test

RES_PATH = os.path.join(os.path.dirname(rally.__file__), os.pardir, "etc")


class BashCompletionTestCase(test.TestCase):
    def test_bash_completion(self):
        old = open(os.path.join(RES_PATH,
                   "rally.bash_completion"), "r").read().splitlines()
        new = cliutils._generate_bash_completion_script().splitlines()
        if old != new:
            for line in difflib.unified_diff(old, new):
                print(line)
            new_filename = "/tmp/rally.bash.new"
            with open(new_filename, "wb") as new_file:
                new_file.write(encodeutils.safe_encode("\n".join(new)))
            self.fail("bash completion script is outdated. "
                      "New script is located at %s "
                      "You may fix this by executing "
                      "`mv %s etc/rally.bash_completion`" % (new_filename,
                                                             new_filename))
