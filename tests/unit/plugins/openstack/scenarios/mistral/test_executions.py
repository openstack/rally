# Copyright 2016: Nokia Inc.
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

from rally.plugins.openstack.scenarios.mistral import executions
from tests.unit import test

BASE = "rally.plugins.openstack.scenarios.mistral.executions"
MISTRAL_WBS_BASE = "rally.plugins.openstack.scenarios.mistral.workbooks"


WB_DEFINITION = """---
version: 2.0
name: wb
workflows:
  wf1:
    type: direct
    tasks:
      noop_task:
        action: std.noop
  wf2:
    type: direct
    tasks:
      noop_task:
        action: std.noop
  wf3:
    type: direct
    tasks:
      noop_task:
        action: std.noop
  wf4:
    type: direct
    tasks:
      noop_task:
        action: std.noop
"""

WB_DEF_ONE_WF = """---
version: 2.0
name: wb
workflows:
  wf1:
    type: direct
    tasks:
      noop_task:
        action: std.noop
"""

PARAMS_EXAMPLE = {"env": {"env_param": "env_param_value"}}
INPUT_EXAMPLE = """{"input1": "value1", "some_json_input": {"a": "b"}}"""

WB = type("obj", (object,), {"name": "wb", "definition": WB_DEFINITION})()
WB_ONE_WF = (
    type("obj", (object,), {"name": "wb", "definition": WB_DEF_ONE_WF})()
)


class MistralExecutionsTestCase(test.ScenarioTestCase):

    @mock.patch("%s.ListExecutions._list_executions" % BASE)
    def test_list_executions(self, mock__list_executions):
        executions.ListExecutions(self.context).run()
        self.assertEqual(1, mock__list_executions.called)

    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB)
    def test_create_execution(self, mock__create_workbook,
                              mock__create_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(WB_DEFINITION)

        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)

    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB)
    def test_create_execution_with_input(self, mock__create_workbook,
                                         mock__create_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(
            WB_DEFINITION, wf_input=INPUT_EXAMPLE)

        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)

    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB)
    @mock.patch("json.loads", return_value=PARAMS_EXAMPLE)
    def test_create_execution_with_params(self, mock_loads,
                                          mock__create_workbook,
                                          mock__create_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(
            WB_DEFINITION, params=str(PARAMS_EXAMPLE))

        self.assertEqual(1, mock_loads.called)
        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)

    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB)
    def test_create_execution_with_wf_name(self, mock__create_workbook,
                                           mock__create_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(
            WB_DEFINITION, "wf4")

        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)

        # we concatenate workbook name with the workflow name in the test
        # the workbook name is not random because we mock the method that
        # adds the random part
        mock__create_execution.assert_called_once_with("wb.wf4", None,)

    @mock.patch("%s.CreateExecutionFromWorkbook._delete_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._delete_workbook" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB)
    def test_create_delete_execution(
            self, mock__create_workbook, mock__create_execution,
            mock__delete_workbook, mock__delete_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(
            WB_DEFINITION, do_delete=True)

        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)
        self.assertEqual(1, mock__delete_workbook.called)
        self.assertEqual(1, mock__delete_execution.called)

    @mock.patch("%s.CreateExecutionFromWorkbook._delete_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._delete_workbook" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB)
    def test_create_delete_execution_with_wf_name(
            self, mock__create_workbook, mock__create_execution,
            mock__delete_workbook, mock__delete_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(
            WB_DEFINITION, "wf4", do_delete=True)

        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)
        self.assertEqual(1, mock__delete_workbook.called)
        self.assertEqual(1, mock__delete_execution.called)

        # we concatenate workbook name with the workflow name in the test
        # the workbook name is not random because we mock the method that
        # adds the random part
        mock__create_execution.assert_called_once_with("wb.wf4", None)

    @mock.patch("%s.CreateExecutionFromWorkbook._delete_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._delete_workbook" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_execution" % BASE)
    @mock.patch("%s.CreateExecutionFromWorkbook._create_workbook" % BASE,
                return_value=WB_ONE_WF)
    def test_create_delete_execution_without_wf_name(
            self, mock__create_workbook, mock__create_execution,
            mock__delete_workbook, mock__delete_execution):

        executions.CreateExecutionFromWorkbook(self.context).run(
            WB_DEF_ONE_WF, do_delete=True)

        self.assertEqual(1, mock__create_workbook.called)
        self.assertEqual(1, mock__create_execution.called)
        self.assertEqual(1, mock__delete_workbook.called)
        self.assertEqual(1, mock__delete_execution.called)

        # we concatenate workbook name with the workflow name in the test
        # the workbook name is not random because we mock the method that
        # adds the random part
        mock__create_execution.assert_called_once_with("wb.wf1", None)
