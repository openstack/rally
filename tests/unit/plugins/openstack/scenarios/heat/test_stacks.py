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


class HeatStacksTestCase(test.TestCase):

    def setUp(self):
        super(HeatStacksTestCase, self).setUp()
        self.default_template = "heat_template_version: 2013-05-23"
        self.default_parameters = {"dummy_param": "dummy_key"}
        self.default_files = ["dummy_file.yaml"]
        self.default_environment = {"env": "dummy_env"}

    @mock.patch(HEAT_STACKS + "._generate_random_name")
    @mock.patch(HEAT_STACKS + "._list_stacks")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_list_stack(self, mock_create, mock_list,
                                   mock_random_name):
        heat_scenario = stacks.HeatStacks()
        mock_random_name.return_value = "test-rally-stack"
        heat_scenario.create_and_list_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock_create.assert_called_once_with(self.default_template,
                                            self.default_parameters,
                                            self.default_files,
                                            self.default_environment)
        mock_list.assert_called_once_with()

    @mock.patch(HEAT_STACKS + ".clients")
    @mock.patch(HEAT_STACKS + "._list_stacks")
    def test_list_stack_and_resources(self, mock_list_stack, mock_clients):
        stack = mock.Mock()
        mock_list_stack.return_value = [stack]
        heat_scenario = stacks.HeatStacks()
        heat_scenario.list_stacks_and_resources()
        mock_clients("heat").resources.list.assert_called_once_with(stack.id)
        self._test_atomic_action_timer(
            heat_scenario.atomic_actions(), "heat.list_resources_of_1_stacks")

    @mock.patch(HEAT_STACKS + ".clients")
    @mock.patch(HEAT_STACKS + "._list_stacks")
    def test_list_stack_and_events(self, mock_list_stack, mock_clients):
        stack = mock.Mock()
        mock_list_stack.return_value = [stack]
        heat_scenario = stacks.HeatStacks()
        heat_scenario.list_stacks_and_events()
        mock_clients("heat").events.list.assert_called_once_with(stack.id)
        self._test_atomic_action_timer(
            heat_scenario.atomic_actions(), "heat.list_events_of_1_stacks")

    @mock.patch(HEAT_STACKS + "._generate_random_name")
    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_delete_stack(self, mock_create, mock_delete,
                                     mock_random_name):
        heat_scenario = stacks.HeatStacks()
        fake_stack = object()
        mock_create.return_value = fake_stack
        mock_random_name.return_value = "test-rally-stack"
        heat_scenario.create_and_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )

        mock_create.assert_called_once_with(self.default_template,
                                            self.default_parameters,
                                            self.default_files,
                                            self.default_environment)
        mock_delete.assert_called_once_with(fake_stack)

    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._check_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_check_delete_stack(self, mock_create, mock_check,
                                       mock_delete):
        heat_scenario = stacks.HeatStacks()
        mock_create.return_value = "fake_stack_create_check_delete"
        heat_scenario.create_check_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )
        mock_create.assert_called_once_with(self.default_template,
                                            self.default_parameters,
                                            self.default_files,
                                            self.default_environment)
        mock_check.assert_called_once_with("fake_stack_create_check_delete")
        mock_delete.assert_called_once_with("fake_stack_create_check_delete")

    @mock.patch(HEAT_STACKS + "._generate_random_name")
    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._update_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_update_delete_stack(self, mock_create, mock_update,
                                        mock_delete, mock_random_name):
        heat_scenario = stacks.HeatStacks()
        fake_stack = object()
        mock_create.return_value = fake_stack
        mock_random_name.return_value = "test-rally-stack"
        heat_scenario.create_update_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            updated_template_path=self.default_template,
            files=self.default_files,
            environment=self.default_environment
        )

        mock_create.assert_called_once_with(self.default_template,
                                            self.default_parameters,
                                            self.default_files,
                                            self.default_environment)
        mock_update.assert_called_once_with(fake_stack, self.default_template,
                                            self.default_parameters,
                                            self.default_files,
                                            self.default_environment)
        mock_delete.assert_called_once_with(fake_stack)

    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._resume_stack")
    @mock.patch(HEAT_STACKS + "._suspend_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_suspend_resume_delete_stack(self,
                                                mock_create,
                                                mock_suspend,
                                                mock_resume,
                                                mock_delete):
        heat_scenario = stacks.HeatStacks()
        mock_create.return_value = "fake_stack_create_suspend_resume_delete"
        heat_scenario.create_suspend_resume_delete_stack(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment
        )

        mock_create.assert_called_once_with(self.default_template,
                                            self.default_parameters,
                                            self.default_files,
                                            self.default_environment)
        mock_suspend.assert_called_once_with(
            "fake_stack_create_suspend_resume_delete")
        mock_resume.assert_called_once_with(
            "fake_stack_create_suspend_resume_delete")
        mock_delete.assert_called_once_with(
            "fake_stack_create_suspend_resume_delete")
