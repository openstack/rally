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
from tests.unit import fakes
from tests.unit import test

MISTRAL_UTILS = "rally.plugins.openstack.scenarios.mistral.utils"
PARAMS_EXAMPLE = {"env": {"env_param": "param_value"}}
INPUT_EXAMPLE = """{"input1": "value1", "some_json_input": {"a": "b"}}"""


class MistralScenarioTestCase(test.ScenarioTestCase):

    def test_list_workbooks(self):
        scenario = utils.MistralScenario(context=self.context)
        return_wbs_list = scenario._list_workbooks()
        self.assertEqual(
            self.clients("mistral").workbooks.list.return_value,
            return_wbs_list)
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.list_workbooks"
        )

    def test_create_workbook(self):
        definition = "version: \"2.0\"\nname: wb"
        scenario = utils.MistralScenario(context=self.context)
        self.assertEqual(
            self.clients("mistral").workbooks.create.return_value,
            scenario._create_workbook(definition)
        )
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.create_workbook"
        )

    def test_delete_workbook(self):
        scenario = utils.MistralScenario(context=self.context)
        scenario._delete_workbook("wb_name")
        self.clients("mistral").workbooks.delete.assert_called_once_with(
            "wb_name"
        )
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.delete_workbook"
        )

    def test_list_executions(self):
        scenario = utils.MistralScenario(context=self.context)
        return_executions_list = scenario._list_executions()
        self.assertEqual(
            return_executions_list,
            self.clients("mistral").executions.list.return_value
        )
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.list_executions"
        )

    def test_create_execution(self):
        scenario = utils.MistralScenario(context=self.context)

        mock_wait_for_status = self.mock_wait_for_status.mock
        wf_name = "fake_wf_name"
        mock_create_exec = self.clients("mistral").executions.create

        self.assertEqual(
            mock_wait_for_status.return_value,
            scenario._create_execution("%s" % wf_name)
        )

        mock_create_exec.assert_called_once_with(wf_name, workflow_input=None)

        args, kwargs = mock_wait_for_status.call_args
        self.assertEqual(mock_create_exec.return_value, args[0])
        self.assertEqual(["ERROR"], kwargs["failure_statuses"])
        self.assertEqual(["SUCCESS"], kwargs["ready_statuses"])
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.create_execution"
        )

    def test_create_execution_with_input(self):
        scenario = utils.MistralScenario(context=self.context)

        mock_wait_for_status = self.mock_wait_for_status.mock
        wf_name = "fake_wf_name"
        mock_create_exec = self.clients("mistral").executions.create

        self.assertEqual(
            mock_wait_for_status.return_value,
            scenario._create_execution(
                wf_name, wf_input=str(INPUT_EXAMPLE))
        )

        mock_create_exec.assert_called_once_with(wf_name,
                                                 workflow_input=INPUT_EXAMPLE)

    def test_create_execution_with_params(self):
        scenario = utils.MistralScenario(context=self.context)

        mock_wait_for_status = self.mock_wait_for_status.mock
        wf_name = "fake_wf_name"
        mock_create_exec = self.clients("mistral").executions.create

        self.assertEqual(
            mock_wait_for_status.return_value,
            scenario._create_execution(
                wf_name, **PARAMS_EXAMPLE)
        )
        mock_create_exec.assert_called_once_with(wf_name, workflow_input=None,
                                                 **PARAMS_EXAMPLE)

        args, kwargs = mock_wait_for_status.call_args
        self.assertEqual(mock_create_exec.return_value, args[0])
        self.assertEqual(["ERROR"], kwargs["failure_statuses"])
        self.assertEqual(["SUCCESS"], kwargs["ready_statuses"])
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.create_execution"
        )

        args, kwargs = mock_wait_for_status.call_args
        self.assertEqual(mock_create_exec.return_value, args[0])
        self.assertEqual(["ERROR"], kwargs["failure_statuses"])
        self.assertEqual(["SUCCESS"], kwargs["ready_statuses"])
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.create_execution"
        )

    def test_delete_execution(self):
        scenario = utils.MistralScenario(context=self.context)
        execution = fakes.FakeMistralClient().execution.create()
        scenario._delete_execution(execution)
        self.clients("mistral").executions.delete.assert_called_once_with(
            execution.id
        )
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "mistral.delete_execution"
        )