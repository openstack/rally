# Copyright 2014: Mirantis Inc.
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

from rally.plugins.openstack.scenarios.heat import stacks
from tests.unit import test

HEAT_STACKS = "rally.plugins.openstack.scenarios.heat.stacks.HeatStacks"


class HeatStacksTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(HeatStacksTestCase, self).setUp()
        self.default_template = "heat_template_version: 2013-05-23"
        self.default_parameters = {"dummy_param": "dummy_key"}
        self.default_files = ["dummy_file.yaml"]
        self.default_environment = {"env": "dummy_env"}
        self.default_output_key = "dummy_output_key"

    @mock.patch(HEAT_STACKS + ".generate_random_name")
    @mock.patch(HEAT_STACKS + "._list_stacks")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_list_stack(self, mock__create_stack, mock__list_stacks,
                                   mock_generate_random_name):
        heat_scenario = stacks.HeatStacks(self.context)
        mock_generate_random_name.return_value = "test-rally-stack"
        heat_scenario.create_and_list_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters, self.default_files,
            self.default_environment)
        mock__list_stacks.assert_called_once_with()

    @mock.patch(HEAT_STACKS + "._list_stacks")
    def test_list_stack_and_resources(self, mock__list_stacks):
        stack = mock.Mock()
        mock__list_stacks.return_value = [stack]
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.list_stacks_and_resources()
        self.clients("heat").resources.list.assert_called_once_with(stack.id)
        self._test_atomic_action_timer(
            heat_scenario.atomic_actions(), "heat.list_resources_of_1_stacks")

    @mock.patch(HEAT_STACKS + "._list_stacks")
    def test_list_stack_and_events(self, mock__list_stacks):
        stack = mock.Mock()
        mock__list_stacks.return_value = [stack]
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.list_stacks_and_events()
        self.clients("heat").events.list.assert_called_once_with(stack.id)
        self._test_atomic_action_timer(
            heat_scenario.atomic_actions(), "heat.list_events_of_1_stacks")

    @mock.patch(HEAT_STACKS + ".generate_random_name")
    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_delete_stack(
            self, mock__create_stack, mock__delete_stack,
            mock_generate_random_name):
        heat_scenario = stacks.HeatStacks(self.context)
        fake_stack = object()
        mock__create_stack.return_value = fake_stack
        mock_generate_random_name.return_value = "test-rally-stack"
        heat_scenario.create_and_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )

        mock__create_stack.assert_called_once_with(
            self.default_template,
            self.default_parameters,
            self.default_files,
            self.default_environment)
        mock__delete_stack.assert_called_once_with(fake_stack)

    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._check_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_check_delete_stack(
            self, mock__create_stack, mock__check_stack, mock__delete_stack):
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.create_check_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters, self.default_files,
            self.default_environment)
        mock__check_stack.assert_called_once_with(
            mock__create_stack.return_value)
        mock__delete_stack.assert_called_once_with(
            mock__create_stack.return_value)

    @mock.patch(HEAT_STACKS + ".generate_random_name")
    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._update_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_update_delete_stack(
            self, mock__create_stack, mock__update_stack, mock__delete_stack,
            mock_generate_random_name):
        heat_scenario = stacks.HeatStacks(self.context)
        fake_stack = object()
        mock__create_stack.return_value = fake_stack
        mock_generate_random_name.return_value = "test-rally-stack"
        heat_scenario.create_update_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            updated_template_path=self.default_template,
            files=self.default_files,
            environment=self.default_environment
        )

        mock__create_stack.assert_called_once_with(
            self.default_template,
            self.default_parameters,
            self.default_files,
            self.default_environment)
        mock__update_stack.assert_called_once_with(
            fake_stack, self.default_template,
            self.default_parameters,
            self.default_files,
            self.default_environment)
        mock__delete_stack.assert_called_once_with(fake_stack)

    def test_create_stack_and_scale(self):
        heat_scenario = stacks.HeatStacks(self.context)
        stack = mock.Mock()
        heat_scenario._create_stack = mock.Mock(return_value=stack)
        heat_scenario._scale_stack = mock.Mock()

        heat_scenario.create_stack_and_scale(
            self.default_template, "key", -1,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)
        heat_scenario._create_stack.assert_called_once_with(
            self.default_template,
            self.default_parameters,
            self.default_files,
            self.default_environment)
        heat_scenario._scale_stack.assert_called_once_with(
            stack, "key", -1)

    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._resume_stack")
    @mock.patch(HEAT_STACKS + "._suspend_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_suspend_resume_delete_stack(
            self, mock__create_stack, mock__suspend_stack, mock__resume_stack,
            mock__delete_stack):
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.create_suspend_resume_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )

        mock__create_stack.assert_called_once_with(
            self.default_template,
            self.default_parameters,
            self.default_files,
            self.default_environment
        )
        mock__suspend_stack.assert_called_once_with(
            mock__create_stack.return_value)
        mock__resume_stack.assert_called_once_with(
            mock__create_stack.return_value)
        mock__delete_stack.assert_called_once_with(
            mock__create_stack.return_value
        )

    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._restore_stack")
    @mock.patch(HEAT_STACKS + "._snapshot_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_snapshot_restore_delete_stack(
            self, mock__create_stack, mock__snapshot_stack,
            mock__restore_stack, mock__delete_stack):
        heat_scenario = stacks.HeatStacks(self.context)
        mock__snapshot_stack.return_value = {"id": "dummy_id"}
        heat_scenario.create_snapshot_restore_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__snapshot_stack.assert_called_once_with(
            mock__create_stack.return_value)
        mock__restore_stack.assert_called_once_with(
            mock__create_stack.return_value, "dummy_id")
        mock__delete_stack.assert_called_once_with(
            mock__create_stack.return_value)

    @mock.patch(HEAT_STACKS + "._stack_show_output_via_API")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_show_output_via_API(self, mock__create_stack,
                                            mock__stack_show_output_via_api):
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.create_stack_and_show_output_via_API(
            template_path=self.default_template,
            output_key=self.default_output_key,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_show_output_via_api.assert_called_once_with(
            mock__create_stack.return_value, self.default_output_key)

    @mock.patch(HEAT_STACKS + "._stack_show_output")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_show_output(self, mock__create_stack,
                                    mock__stack_show_output):
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.create_stack_and_show_output(
            template_path=self.default_template,
            output_key=self.default_output_key,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_show_output.assert_called_once_with(
            mock__create_stack.return_value, self.default_output_key)

    @mock.patch(HEAT_STACKS + "._stack_list_output_via_API")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_list_output_via_API(self, mock__create_stack,
                                            mock__stack_list_output_via_api):
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.create_stack_and_list_output_via_API(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_list_output_via_api.assert_called_once_with(
            mock__create_stack.return_value)

    @mock.patch(HEAT_STACKS + "._stack_list_output")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_list_output(self, mock__create_stack,
                                    mock__stack_list_output):
        heat_scenario = stacks.HeatStacks(self.context)
        heat_scenario.create_stack_and_list_output(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_list_output.assert_called_once_with(
            mock__create_stack.return_value)
