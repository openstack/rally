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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.mistral import utils
from rally.task import types
from rally.task import validation


"""Scenarios for Mistral workbook."""


@validation.required_clients("mistral")
@validation.required_openstack(users=True)
@validation.required_services(consts.Service.MISTRAL)
@scenario.configure(name="MistralWorkbooks.list_workbooks")
class ListWorkbooks(utils.MistralScenario):

    def run(self):
        """Scenario test mistral workbook-list command.

        This simple scenario tests the Mistral workbook-list
        command by listing all the workbooks.
        """
        self._list_workbooks()


@validation.required_parameters("definition")
@validation.file_exists("definition")
@types.convert(definition={"type": "file"})
@validation.required_clients("mistral")
@validation.required_openstack(users=True)
@validation.required_services(consts.Service.MISTRAL)
@scenario.configure(context={"cleanup": ["mistral"]},
                    name="MistralWorkbooks.create_workbook")
class CreateWorkbook(utils.MistralScenario):

    def run(self, definition, do_delete=False):
        """Scenario tests workbook creation and deletion.

        This scenario is a very useful tool to measure the
        "mistral workbook-create" and "mistral workbook-delete"
        commands performance.
        :param definition: string (yaml string) representation of given
                           file content (Mistral workbook definition)
        :param do_delete: if False than it allows to check performance
                          in "create only" mode.
        """
        wb = self._create_workbook(definition)

        if do_delete:
            self._delete_workbook(wb.name)
