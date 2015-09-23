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

from rally.plugins.openstack.scenarios.mistral import workbooks
from tests.unit import test

MISTRAL_WBS = ("rally.plugins.openstack.scenarios."
               "mistral.workbooks.MistralWorkbooks")


class MistralWorkbooksTestCase(test.ScenarioTestCase):

    @mock.patch(MISTRAL_WBS + "._list_workbooks")
    def test_list_workbooks(self, mock__list_workbooks):
        mistral_scenario = workbooks.MistralWorkbooks(self.context)
        mistral_scenario.list_workbooks()
        mock__list_workbooks.assert_called_once_with()

    @mock.patch(MISTRAL_WBS + "._create_workbook")
    def test_create_workbook(self, mock__create_workbook):
        mistral_scenario = workbooks.MistralWorkbooks(self.context)
        definition = "---\nversion: \"2.0\"\nname: wb"
        fake_wb = mock.MagicMock()
        fake_wb.name = "wb"
        mock__create_workbook.return_value = fake_wb
        mistral_scenario.create_workbook(definition)

        self.assertEqual(1, mock__create_workbook.called)

    @mock.patch(MISTRAL_WBS + "._delete_workbook")
    @mock.patch(MISTRAL_WBS + "._create_workbook")
    def test_create_delete_workbook(self,
                                    mock__create_workbook,
                                    mock__delete_workbook):
        mistral_scenario = workbooks.MistralWorkbooks(self.context)
        definition = "---\nversion: \"2.0\"\nname: wb"
        fake_wb = mock.MagicMock()
        fake_wb.name = "wb"
        mock__create_workbook.return_value = fake_wb
        mistral_scenario.create_workbook(definition, do_delete=True)

        self.assertEqual(1, mock__create_workbook.called)
        mock__delete_workbook.assert_called_once_with(fake_wb.name)
