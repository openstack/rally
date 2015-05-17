# Copyright 2015: Mirantis Inc.
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

from rally.plugins.openstack.scenarios.mistral import utils
from tests.unit import test

MISTRAL_UTILS = "rally.plugins.openstack.scenarios.mistral.utils"


class MistralScenarioTestCase(test.TestCase):

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = atomic_actions.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(MISTRAL_UTILS + ".MistralScenario.clients")
    def test_list_workbooks(self, mock_clients):
        wbs_list = []
        mock_clients("mistral").workbooks.list.return_value = wbs_list
        scenario = utils.MistralScenario()
        return_wbs_list = scenario._list_workbooks()
        self.assertEqual(wbs_list, return_wbs_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "mistral.list_workbooks")

    @mock.patch(MISTRAL_UTILS + ".MistralScenario.clients")
    def test_create_workbook(self, mock_clients):
        definition = "version: \"2.0\"\nname: wb"
        mock_clients("mistral").workbooks.create.return_value = "wb"
        scenario = utils.MistralScenario()
        wb = scenario._create_workbook(definition)
        self.assertEqual("wb", wb)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "mistral.create_workbook")

    @mock.patch(MISTRAL_UTILS + ".MistralScenario.clients")
    def test_delete_workbook(self, mock_clients):
        wb = mock.Mock()
        wb.name = "wb"
        mock_clients("mistral").workbooks.delete.return_value = "ok"
        scenario = utils.MistralScenario()
        scenario._delete_workbook(wb.name)
        mock_clients("mistral").workbooks.delete.assert_called_once_with(
            wb.name
        )
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "mistral.delete_workbook")
