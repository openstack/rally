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

import json

import six
import yaml

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.mistral import utils
from rally.task import types
from rally.task import validation


"""Scenarios for Mistral execution."""


@validation.required_clients("mistral")
@validation.required_openstack(users=True)
@validation.required_services(consts.Service.MISTRAL)
@scenario.configure(name="MistralExecutions.list_executions",
                    context={"cleanup": ["mistral"]})
class ListExecutions(utils.MistralScenario):

    def run(self, marker="", limit=None, sort_keys="", sort_dirs=""):
        """Scenario test mistral execution-list command.

        This simple scenario tests the Mistral execution-list
        command by listing all the executions.
        :param marker: The last execution uuid of the previous page, displays
                       list of executions after "marker".
        :param limit: number Maximum number of executions to return in a single
                      result.
        :param sort_keys: id,description
        :param sort_dirs: [SORT_DIRS] Comma-separated list of sort directions.
                          Default: asc.
        """
        self._list_executions(marker=marker, limit=limit,
                              sort_keys=sort_keys, sort_dirs=sort_dirs)


@validation.required_parameters("definition")
@validation.file_exists("definition")
@types.convert(definition={"type": "file"})
@types.convert(params={"type": "file"})
@types.convert(wf_input={"type": "file"})
@validation.required_clients("mistral")
@validation.required_openstack(users=True)
@validation.required_services(consts.Service.MISTRAL)
@validation.workbook_contains_workflow("definition", "workflow_name")
@scenario.configure(
    name="MistralExecutions.create_execution_from_workbook",
    context={"cleanup": ["mistral"]})
class CreateExecutionFromWorkbook(utils.MistralScenario):

    def run(self, definition, workflow_name=None, wf_input=None, params=None,
            do_delete=False):
        """Scenario tests execution creation and deletion.

        This scenario is a very useful tool to measure the
        "mistral execution-create" and "mistral execution-delete"
        commands performance.
        :param definition: string (yaml string) representation of given file
                           content (Mistral workbook definition)
        :param workflow_name: string the workflow name to execute. Should be
                              one of the to workflows in the definition. If no
                               workflow_name is passed, one of the workflows in
                               the definition will be taken.
        :param wf_input: file containing a json string of mistral workflow
                         input
        :param params: file containing a json string of mistral params
                       (the string is the place to pass the environment)
        :param do_delete: if False than it allows to check performance
                          in "create only" mode.
        """

        wb = self._create_workbook(definition)
        wb_def = yaml.safe_load(wb.definition)

        if not workflow_name:
            workflow_name = six.next(six.iterkeys(wb_def["workflows"]))

        workflow_identifier = ".".join([wb.name, workflow_name])

        if not params:
            params = {}
        else:
            params = json.loads(params)

        ex = self._create_execution(workflow_identifier, wf_input, **params)

        if do_delete:
            self._delete_workbook(wb.name)
            self._delete_execution(ex)
