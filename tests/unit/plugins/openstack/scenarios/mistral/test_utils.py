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

from rally.plugins.openstack.scenarios.mistral import utils
from tests.unit import test

MISTRAL_UTILS = "rally.plugins.openstack.scenarios.mistral.utils"


class MistralScenarioTestCase(test.ScenarioTestCase):

    def test_list_workbooks(self):
        scenario = utils.MistralScenario(context=self.context)
        return_wbs_list = scenario._list_workbooks()
        self.assertEqual(
            self.clients("mistral").workbooks.list.return_value,
            return_wbs_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "mistral.list_workbooks")

    def test_create_workbook(self):
        definition = "version: \"2.0\"\nname: wb"
        scenario = utils.MistralScenario(context=self.context)
        self.assertEqual(scenario._create_workbook(definition),
                         self.clients("mistral").workbooks.create.return_value)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "mistral.create_workbook")

    def test_delete_workbook(self):
        scenario = utils.MistralScenario(context=self.context)
        scenario._delete_workbook("wb_name")
        self.clients("mistral").workbooks.delete.assert_called_once_with(
            "wb_name")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "mistral.delete_workbook")
