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
from rally.cmd.commands import info
from rally import deploy
from rally.deploy.engines import existing as existing_cloud
from rally.deploy import serverprovider
from rally.deploy.serverprovider.providers import existing as existing_servers
from rally import exceptions
from tests.unit import test


SCENARIO = "rally.cmd.commands.info.scenario_base.Scenario"
ENGINE = "rally.cmd.commands.info.deploy.EngineFactory"
PROVIDER = "rally.cmd.commands.info.serverprovider.ProviderFactory"
UTILS = "rally.cmd.commands.info.utils"


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
        self.assertEqual(None, status)

    @mock.patch(SCENARIO + ".get_scenario_by_name",
                return_value=dummy.Dummy.dummy)
    def test_find_dummy_scenario(self, mock_get_scenario_by_name):
        query = "Dummy.dummy"
        status = self.info.find(query)
        mock_get_scenario_by_name.assert_called_once_with(query)
        self.assertEqual(None, status)

    @mock.patch(SCENARIO + ".get_scenario_by_name",
                side_effect=exceptions.NoSuchScenario)
    def test_find_failure_status(self, mock_get_scenario_by_name):
        query = "Dummy.non_existing"
        status = self.info.find(query)
        mock_get_scenario_by_name.assert_called_once_with(query)
        self.assertEqual(1, status)

    @mock.patch(ENGINE + ".get_by_name",
                return_value=existing_cloud.ExistingCloud)
    def test_find_existing_cloud(self, mock_get_by_name):
        query = "ExistingCloud"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertEqual(None, status)

    @mock.patch(PROVIDER + ".get_by_name",
                return_value=existing_servers.ExistingServers)
    def test_find_existing_servers(self, mock_get_by_name):
        query = "ExistingServers"
        status = self.info.find(query)
        mock_get_by_name.assert_called_once_with(query)
        self.assertEqual(None, status)

    @mock.patch(UTILS + ".itersubclasses", return_value=[dummy.Dummy])
    def test_list(self, mock_itersubclasses):
        status = self.info.list()
        mock_itersubclasses.assert_has_calls([
            mock.call(scenario_base.Scenario),
            mock.call(deploy.EngineFactory),
            mock.call(serverprovider.ProviderFactory)])
        self.assertEqual(None, status)
