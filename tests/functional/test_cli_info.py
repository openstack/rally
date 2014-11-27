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

    def test_find_scenario_group(self):
        output = self.rally("info find Dummy")
        self.assertIn("(benchmark scenario group)", output)
        self.assertIn("Dummy.dummy_exception", output)
        self.assertIn("Dummy.dummy_random_fail_in_atomic", output)

    def test_find_scenario_group_base_class(self):
        output = self.rally("info find CeilometerScenario")
        self.assertIn("(benchmark scenario group)", output)

    def test_find_scenario(self):
        self.assertIn("(benchmark scenario)", self.rally("info find dummy"))

    def test_find_sla(self):
        self.assertIn("(SLA)", self.rally("info find FailureRate"))

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
        marker_string = "ExistingServers (server provider)."
        self.assertIn(marker_string, self.rally("info find ExistinfServert"))

    def test_find_misspelling_truncated(self):
        marker_string = ("NovaServers.boot_and_delete_server "
                         "(benchmark scenario).")
        self.assertIn(marker_string, self.rally("info find boot_and_delete"))

    def test_list(self):
        output = self.rally("info list")
        self.assertIn("Benchmark scenario groups:", output)
        self.assertIn("NovaServers", output)
        self.assertIn("SLA:", output)
        self.assertIn("FailureRate", output)
        self.assertIn("Deploy engines:", output)
        self.assertIn("ExistingCloud", output)
        self.assertIn("Server providers:", output)
        self.assertIn("ExistingServers", output)

    def test_BenchmarkScenarios(self):
        output = self.rally("info BenchmarkScenarios")
        self.assertIn("Benchmark scenario groups:", output)
        self.assertIn("NovaServers", output)

    def test_SLA(self):
        output = self.rally("info SLA")
        self.assertIn("SLA:", output)
        self.assertIn("FailureRate", output)

    def test_DeployEngines(self):
        output = self.rally("info DeployEngines")
        self.assertIn("Deploy engines:", output)
        self.assertIn("ExistingCloud", output)

    def test_ServerProviders(self):
        output = self.rally("info ServerProviders")
        self.assertIn("Server providers:", output)
        self.assertIn("ExistingServers", output)
