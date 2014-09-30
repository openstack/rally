# Copyright 2013: Mirantis Inc.
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

import test_cli_utils as utils


class InfoTestCase(unittest.TestCase):

    def setUp(self):
        super(InfoTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_find_scenario_group(self):
        self.assertIn("(benchmark scenario group)",
                      self.rally("info find Dummy"))

    def test_find_scenario(self):
        self.assertIn("(benchmark scenario)", self.rally("info find dummy"))

    def test_find_deployment_engine(self):
        marker_string = "ExistingCloud (deploy engine)."
        self.assertIn(marker_string, self.rally("info find ExistingCloud"))

    def test_find_server_provider(self):
        marker_string = "ExistingServers (server provider)."
        self.assertIn(marker_string, self.rally("info find ExistingServers"))

    def test_find_fails(self):
        self.assertRaises(utils.RallyCmdError, self.rally,
                          ("info find NonExistingStuff"))

    def test_find_misspelling_typos(self):
        marker_string = "ExistingServers"
        try:
            self.rally("info find ExistinfServert")
        except utils.RallyCmdError as e:
            self.assertIn(marker_string, e.output)

    def test_find_misspelling_truncated(self):
        marker_string = "boot_and_delete_server"
        try:
            self.rally("info find boot_and_delete")
        except utils.RallyCmdError as e:
            self.assertIn(marker_string, e.output)
