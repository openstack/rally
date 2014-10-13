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

import unittest

from tests.functional import utils


class CliUtilsTestCase(unittest.TestCase):

    def setUp(self):
        super(CliUtilsTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_missing_argument(self):
        with self.assertRaises(utils.RallyCmdError) as e:
            self.rally("use task")
        self.assertIn("--uuid", e.exception.output)
