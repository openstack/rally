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

BASE = "rally.plugins.openstack.scenarios.mistral.workbooks"


class MistralWorkbooksTestCase(test.ScenarioTestCase):

    @mock.patch("%s.ListWorkbooks._list_workbooks" % BASE)
    def test_list_workbooks(self, mock_list_workbooks__list_workbooks):
        workbooks.ListWorkbooks(self.context).run()
        mock_list_workbooks__list_workbooks.assert_called_once_with()

    @mock.patch("%s.CreateWorkbook._create_workbook" % BASE)
    def test_create_workbook(self, mock_create_workbook__create_workbook):
        definition = "---\nversion: \"2.0\"\nname: wb"
        fake_wb = mock.MagicMock()
        fake_wb.name = "wb"
        mock_create_workbook__create_workbook.return_value = fake_wb
        workbooks.CreateWorkbook(self.context).run(definition)

        self.assertEqual(1, mock_create_workbook__create_workbook.called)

    @mock.patch("%s.CreateWorkbook._delete_workbook" % BASE)
    @mock.patch("%s.CreateWorkbook._create_workbook" % BASE)
    def test_create_delete_workbook(self,
                                    mock_create_workbook__create_workbook,
                                    mock_create_workbook__delete_workbook):
        definition = "---\nversion: \"2.0\"\nname: wb"
        fake_wb = mock.MagicMock()
        fake_wb.name = "wb"
        mock_create_workbook__create_workbook.return_value = fake_wb

        workbooks.CreateWorkbook(self.context).run(definition, do_delete=True)

        self.assertTrue(mock_create_workbook__create_workbook.called)
        mock_create_workbook__delete_workbook.assert_called_once_with(
            fake_wb.name)