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
from rally.benchmark import sla
from rally.cli.commands import info
from rally import deploy
from rally.deploy.engines import existing as existing_cloud
from rally.deploy.serverprovider import provider
from rally.deploy.serverprovider.providers import existing as existing_servers
from rally import exceptions
from rally.plugins.common.scenarios.dummy import dummy
from rally.plugins.common.sla import failure_rate
from tests.unit import test


SCENARIO = "rally.cli.commands.info.scenario_base.Scenario"
SLA = "rally.cli.commands.info.sla.SLA"
ENGINE = "rally.cli.commands.info.deploy.EngineFactory"
PROVIDER = "rally.cli.commands.info.provider.ProviderFactory"
UTILS = "rally.cli.commands.info.utils"
DISCOVER = "rally.cli.commands.info.discover"
COMMANDS = "rally.cli.commands.info.InfoCommands"


class InfoCommandsTestCase(test.TestCase):
    def setUp(self):
        super(InfoCommandsTestCase, self).setUp()
        self.info = info.InfoCommands()

    @mock.patch(SCENARIO + ".get_by_name",
                return_value=dummy.Dummy)
    def test_find_dummy_scenario_group(self, mock_get):
        query = "Dummy"
        status = self.info.find(query)
        mock_get.assert_called_once_with(query)
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

    @mock.patch(SLA + ".get", return_value=failure_rate.FailureRate)
    def test_find_failure_rate_sla(self, mock_get):
        query = "failure_rate"
        status = self.info.find(query)
        mock_get.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(ENGINE + ".get",
                return_value=existing_cloud.ExistingCloud)
    def test_find_existing_cloud(self, mock_get):
        query = "ExistingCloud"
        status = self.info.find(query)
        mock_get.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(PROVIDER + ".get",
                return_value=existing_servers.ExistingServers)
    def test_find_existing_servers(self, mock_get):
        query = "ExistingServers"
        status = self.info.find(query)
        mock_get.assert_called_once_with(query)
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

    @mock.patch(DISCOVER + ".itersubclasses", return_value=[dummy.Dummy])
    def test_BenchmarkScenarios(self, mock_itersubclasses):
        status = self.info.BenchmarkScenarios()
        mock_itersubclasses.assert_called_with(scenario_base.Scenario)
        self.assertIsNone(status)

    @mock.patch(DISCOVER + ".itersubclasses",
                return_value=[failure_rate.FailureRate])
    def test_SLA(self, mock_itersubclasses):
        status = self.info.SLA()
        mock_itersubclasses.assert_called_with(sla.SLA)
        self.assertIsNone(status)

    @mock.patch(DISCOVER + ".itersubclasses",
                return_value=[existing_cloud.ExistingCloud])
    def test_DeploymentEngines(self, mock_itersubclasses):
        status = self.info.DeploymentEngines()
        mock_itersubclasses.assert_called_with(deploy.EngineFactory)
        self.assertIsNone(status)

    @mock.patch(DISCOVER + ".itersubclasses",
                return_value=[existing_servers.ExistingServers])
    def test_ServerProviders(self, mock_itersubclasses):
        status = self.info.ServerProviders()
        mock_itersubclasses.assert_called_with(provider.ProviderFactory)
        self.assertIsNone(status)
