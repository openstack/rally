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

from rally.cli.commands import info
from rally.deployment.engines import existing as existing_cloud
from rally.deployment.serverprovider.providers import (
    existing as existing_servers)
from rally import exceptions
from rally.plugins.common.scenarios.dummy import dummy
from rally.plugins.common.sla import failure_rate
from tests.unit import test


SCENARIO = "rally.cli.commands.info.scenario.Scenario"
SLA = "rally.cli.commands.info.sla.SLA"
ENGINE = "rally.cli.commands.info.engine.Engine"
PROVIDER = "rally.cli.commands.info.provider.ProviderFactory"
UTILS = "rally.cli.commands.info.utils"
DISCOVER = "rally.cli.commands.info.discover"
COMMANDS = "rally.cli.commands.info.InfoCommands"


class InfoCommandsTestCase(test.TestCase):
    def setUp(self):
        super(InfoCommandsTestCase, self).setUp()
        self.info = info.InfoCommands()

    @mock.patch(SCENARIO + ".get", return_value=dummy.Dummy.dummy)
    def test_find_dummy_scenario(self, mock_scenario_get):
        query = "Dummy.dummy"
        status = self.info.find(query)
        mock_scenario_get.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(SCENARIO + ".get", side_effect=exceptions.PluginNotFound)
    def test_find_failure_status(self, mock_scenario_get):
        query = "Dummy.non_existing"
        status = self.info.find(query)
        mock_scenario_get.assert_called_once_with(query)
        self.assertEqual(1, status)

    @mock.patch(SLA + ".get", return_value=failure_rate.FailureRate)
    def test_find_failure_rate_sla(self, mock_sla_get):
        query = "failure_rate"
        status = self.info.find(query)
        mock_sla_get.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(ENGINE + ".get",
                return_value=existing_cloud.ExistingCloud)
    def test_find_existing_cloud(self, mock_engine_get):
        query = "ExistingCloud"
        status = self.info.find(query)
        mock_engine_get.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(PROVIDER + ".get",
                return_value=existing_servers.ExistingServers)
    def test_find_existing_servers(self, mock_provider_factory_get):
        query = "ExistingServers"
        status = self.info.find(query)
        mock_provider_factory_get.assert_called_once_with(query)
        self.assertIsNone(status)

    @mock.patch(COMMANDS + ".ServerProviders")
    @mock.patch(COMMANDS + ".DeploymentEngines")
    @mock.patch(COMMANDS + ".SLA")
    @mock.patch(COMMANDS + ".BenchmarkScenarios")
    def test_list(self, mock_benchmark_scenarios, mock_sla,
                  mock_deployment_engines, mock_server_providers):
        status = self.info.list()
        mock_benchmark_scenarios.assert_called_once_with()
        mock_sla.assert_called_once_with()
        mock_deployment_engines.assert_called_once_with()
        mock_server_providers.assert_called_once_with()
        self.assertIsNone(status)

    @mock.patch(SCENARIO + ".get_all", return_value=[dummy.Dummy.dummy])
    def test_BenchmarkScenarios(self, mock_scenario_get_all):
        status = self.info.BenchmarkScenarios()
        mock_scenario_get_all.assert_called_with()
        self.assertIsNone(status)

    @mock.patch(SLA + ".get_all", return_value=[failure_rate.FailureRate])
    def test_SLA(self, mock_sla_get_all):
        status = self.info.SLA()
        mock_sla_get_all.assert_called_with()
        self.assertIsNone(status)

    @mock.patch(ENGINE + ".get_all",
                return_value=[existing_cloud.ExistingCloud])
    def test_DeploymentEngines(self, mock_engine_get_all):
        status = self.info.DeploymentEngines()
        mock_engine_get_all.assert_called_with()
        self.assertIsNone(status)

    @mock.patch(PROVIDER + ".get_all",
                return_value=[existing_servers.ExistingServers])
    def test_ServerProviders(self, mock_provider_factory_get_all):
        status = self.info.ServerProviders()
        mock_provider_factory_get_all.assert_called_with()
        self.assertIsNone(status)
