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

from rally.benchmark.scenarios.dummy import dummy
from rally.cmd.commands import info
from rally import exceptions
from tests import test


SCENARIO = "rally.cmd.commands.info.scenario_base.Scenario"


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
