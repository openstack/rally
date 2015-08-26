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

from tests.functional import utils


class InfoTestCase(unittest.TestCase):

    def setUp(self):
        super(InfoTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_find_scenario(self):
        self.assertIn("(task scenario)",
                      self.rally("info find Dummy.dummy"))

    def test_find_scenario_misspelling_typos(self):
        self.assertIn("(task scenario)",
                      self.rally("info find Dummy.dummi"))

    def test_find_sla(self):
        expected = "failure_rate (SLA)"
        self.assertIn(expected, self.rally("info find failure_rate"))

    def test_find_sla_misspelling_typos(self):
        expected = "failure_rate (SLA)"
        self.assertIn(expected, self.rally("info find failure_rte"))

    def test_find_deployment_engine(self):
        marker_string = "ExistingCloud (deploy engine)"
        self.assertIn(marker_string, self.rally("info find ExistingCloud"))

    def test_find_deployment_engine_misspelling_typos(self):
        marker_string = "ExistingCloud (deploy engine)"
        self.assertIn(marker_string, self.rally("info find ExistinCloud"))

    def test_find_server_provider(self):
        marker_string = "ExistingServers (server provider)"
        self.assertIn(marker_string, self.rally("info find ExistingServers"))

    def test_find_server_provider_misspelling_typos(self):
        marker_string = "ExistingServers (server provider)"
        self.assertIn(marker_string, self.rally("info find ExistingServer"))

    def test_find_fails(self):
        self.assertRaises(utils.RallyCliError, self.rally,
                          ("info find NonExistingStuff"))

    def test_find_misspelling_truncated(self):
        marker_string = ("NovaServers.boot_and_list_server "
                         "(task scenario)")
        self.assertIn(marker_string,
                      self.rally("info find boot_and_list"))

    def test_find_misspelling_truncated_many_substitutions(self):
        try:
            self.rally("info find Nova")
        except utils.RallyCliError as e:
            self.assertIn("NovaServers", e.output)
            self.assertIn("NovaServers.boot_and_delete_server", e.output)
            self.assertIn("NovaServers.snapshot_server", e.output)

    def test_find_displays_args(self):
        output = self.rally("info find Dummy.dummy")
        self.assertIn("sleep: idle time of method (in seconds). [Default: 0]",
                      output)

    def test_list(self):
        output = self.rally("info list")
        self.assertIn("NovaServers", output)
        self.assertIn("SLA checks:", output)
        self.assertIn("failure_rate", output)
        self.assertIn("Deployment engines:", output)
        self.assertIn("ExistingCloud", output)
        self.assertIn("Server providers:", output)
        self.assertIn("ExistingServers", output)

    def test_BenchmarkScenarios(self):
        output = self.rally("info BenchmarkScenarios")
        self.assertIn("NovaServers", output)
        self.assertNotIn("NovaScenario", output)

    def test_SLA(self):
        output = self.rally("info SLA")
        self.assertIn("SLA checks:", output)
        self.assertIn("failure_rate", output)

    def test_DeploymentEngines(self):
        output = self.rally("info DeploymentEngines")
        self.assertIn("Deployment engines:", output)
        self.assertIn("ExistingCloud", output)

    def test_ServerProviders(self):
        output = self.rally("info ServerProviders")
        self.assertIn("Server providers:", output)
        self.assertIn("ExistingServers", output)
