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

import mock

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark.scenarios.dummy import dummy
from rally.benchmark.sla import base as sla_base
from rally.cmd.commands import info
from rally import deploy
from rally.deploy.engines import existing as existing_cloud
from rally.deploy import serverprovider
from rally.deploy.serverprovider.providers import existing as existing_servers
from rally import exceptions
from tests.unit import test


SCENARIO = "rally.cmd.commands.info.scenario_base.Scenario"
SLA = "rally.cmd.commands.info.sla_base.SLA"
ENGINE = "rally.cmd.commands.info.deploy.EngineFactory"
PROVIDER = "rally.cmd.commands.info.serverprovider.ProviderFactory"
UTILS = "rally.cmd.commands.info.utils"
COMMANDS = "rally.cmd.commands.info.InfoCommands"


class InfoCommandsTestCase(test.TestCase):
    def setUp(self):
        super(InfoCommandsTestCase, self).setUp()
        self.info = info.InfoCommands()

    @mock.patch(SCENARIO + ".get_by_name",
                return_value=dummy.Dummy)
    def test_find_dummy_scenario_group(self, mock_get_by_name):
        query = "Dummy"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(SCENARIO + ".get_scenario_by_name",
                return_value=dummy.Dummy.dummy)
    def test_find_dummy_scenario(self, mock_get_scenario_by_name):
        query = "Dummy.dummy"
        status = self.info.find(query)
        mock_get_scenario_by_name.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(SCENARIO + ".get_scenario_by_name",
                side_effect=exceptions.NoSuchScenario)
    def test_find_failure_status(self, mock_get_scenario_by_name):
        query = "Dummy.non_existing"
        status = self.info.find(query)
        mock_get_scenario_by_name.assert_called_once_with(query)
        self.assertEqual(1, status)

    @mock.patch(SLA + ".get_by_name", return_value=sla_base.FailureRate)
    def test_find_failure_rate_sla(self, mock_get_by_name):
        query = "failure_rate"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(SLA + ".get_by_name", return_value=sla_base.FailureRate)
    def test_find_failure_rate_sla_by_class_name(self, mock_get_by_name):
        query = "FailureRate"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(ENGINE + ".get_by_name",
                return_value=existing_cloud.ExistingCloud)
    def test_find_existing_cloud(self, mock_get_by_name):
        query = "ExistingCloud"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(PROVIDER + ".get_by_name",
                return_value=existing_servers.ExistingServers)
    def test_find_existing_servers(self, mock_get_by_name):
        query = "ExistingServers"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(COMMANDS + ".ServerProviders")
    @mock.patch(COMMANDS + ".DeploymentEngines")
    @mock.patch(COMMANDS + ".SLA")
    @mock.patch(COMMANDS + ".BenchmarkScenarios")
    def test_list(self, mock_BenchmarkScenarios, mock_SLA,
                  mock_DeploymentEngines, mock_ServerProviders):
        status = self.info.list()
        mock_BenchmarkScenarios.assert_called_once_with()
        mock_SLA.assert_called_once_with()
        mock_DeploymentEngines.assert_called_once_with()
        mock_ServerProviders.assert_called_once_with()
        self.assertIsNone(status)

    @mock.patch(UTILS + ".itersubclasses", return_value=[dummy.Dummy])
    def test_BenchmarkScenarios(self, mock_itersubclasses):
        status = self.info.BenchmarkScenarios()
        mock_itersubclasses.assert_called_with(scenario_base.Scenario)
        self.assertIsNone(status)

    @mock.patch(UTILS + ".itersubclasses", return_value=[sla_base.FailureRate])
    def test_SLA(self, mock_itersubclasses):
        status = self.info.SLA()
        mock_itersubclasses.assert_called_with(sla_base.SLA)
        self.assertIsNone(status)

    @mock.patch(UTILS + ".itersubclasses",
                return_value=[existing_cloud.ExistingCloud])
    def test_DeploymentEngines(self, mock_itersubclasses):
        status = self.info.DeploymentEngines()
        mock_itersubclasses.assert_called_with(deploy.EngineFactory)
        self.assertIsNone(status)

    @mock.patch(UTILS + ".itersubclasses",
                return_value=[existing_servers.ExistingServers])
    def test_ServerProviders(self, mock_itersubclasses):
        status = self.info.ServerProviders()
        mock_itersubclasses.assert_called_with(serverprovider.ProviderFactory)
        self.assertIsNone(status)
