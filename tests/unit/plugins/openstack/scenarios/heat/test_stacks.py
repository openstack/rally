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

BASE = "rally.plugins.openstack.scenarios.heat.stacks"


class HeatStacksTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(HeatStacksTestCase, self).setUp()
        self.default_template = "heat_template_version: 2013-05-23"
        self.default_parameters = {"dummy_param": "dummy_key"}
        self.default_files = ["dummy_file.yaml"]
        self.default_environment = {"env": "dummy_env"}
        self.default_output_key = "dummy_output_key"

    @mock.patch("%s.CreateAndListStack._list_stacks" % BASE)
    @mock.patch("%s.CreateAndListStack._create_stack" % BASE)
    @mock.patch("%s.CreateAndListStack.generate_random_name" % BASE,
                return_value="test-rally-stack")
    def test_create_and_list_stack(self,
                                   mock_generate_random_name,
                                   mock__create_stack,
                                   mock__list_stacks):
        stacks.CreateAndListStack(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__list_stacks.assert_called_once_with()

    @mock.patch("%s.ListStacksAndResources._list_stacks" % BASE)
    def test_list_stack_and_resources(self, mock__list_stacks):
        stack = mock.Mock()
        heat_scenario = stacks.ListStacksAndResources(self.context)
        mock__list_stacks.return_value = [stack]
        heat_scenario.run()
        self.clients("heat").resources.list.assert_called_once_with(
            stack.id)
        self._test_atomic_action_timer(heat_scenario.atomic_actions(),
                                       "heat.list_resources_of_1_stacks")

    @mock.patch("%s.ListStacksAndEvents._list_stacks" % BASE)
    def test_list_stack_and_events(self, mock__list_stacks):
        stack = mock.Mock()
        mock__list_stacks.return_value = [stack]
        heat_scenario = stacks.ListStacksAndEvents(self.context)
        heat_scenario.run()
        self.clients("heat").events.list.assert_called_once_with(stack.id)
        self._test_atomic_action_timer(
            heat_scenario.atomic_actions(), "heat.list_events_of_1_stacks")

    @mock.patch("%s.CreateAndDeleteStack._delete_stack" % BASE)
    @mock.patch("%s.CreateAndDeleteStack._create_stack" % BASE)
    @mock.patch("%s.CreateAndDeleteStack.generate_random_name" % BASE,
                return_value="test-rally-stack")
    def test_create_and_delete_stack(self,
                                     mock_generate_random_name,
                                     mock__create_stack,
                                     mock__delete_stack):
        fake_stack = object()
        mock__create_stack.return_value = fake_stack
        stacks.CreateAndDeleteStack(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template,
            self.default_parameters,
            self.default_files,
            self.default_environment)
        mock__delete_stack.assert_called_once_with(fake_stack)

    @mock.patch("%s.CreateCheckDeleteStack._delete_stack" % BASE)
    @mock.patch("%s.CreateCheckDeleteStack._check_stack" % BASE)
    @mock.patch("%s.CreateCheckDeleteStack._create_stack" % BASE)
    def test_create_check_delete_stack(self,
                                       mock__create_stack,
                                       mock__check_stack,
                                       mock__delete_stack):
        stacks.CreateCheckDeleteStack(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__check_stack.assert_called_once_with(
            mock__create_stack.return_value)
        mock__delete_stack.assert_called_once_with(
            mock__create_stack.return_value)

    @mock.patch("%s.CreateUpdateDeleteStack._delete_stack" % BASE)
    @mock.patch("%s.CreateUpdateDeleteStack._update_stack" % BASE)
    @mock.patch("%s.CreateUpdateDeleteStack._create_stack" % BASE)
    @mock.patch("%s.CreateUpdateDeleteStack.generate_random_name" % BASE,
                return_value="test-rally-stack")
    def test_create_update_delete_stack(self,
                                        mock_generate_random_name,
                                        mock__create_stack,
                                        mock__update_stack,
                                        mock__delete_stack):
        fake_stack = object()
        mock__create_stack.return_value = fake_stack
        stacks.CreateUpdateDeleteStack(self.context).run(
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
        heat_scenario = stacks.CreateStackAndScale(self.context)
        stack = mock.Mock()
        heat_scenario._create_stack = mock.Mock(return_value=stack)
        heat_scenario._scale_stack = mock.Mock()

        heat_scenario.run(
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

    @mock.patch("%s.CreateSuspendResumeDeleteStack._delete_stack" % BASE)
    @mock.patch("%s.CreateSuspendResumeDeleteStack._resume_stack" % BASE)
    @mock.patch("%s.CreateSuspendResumeDeleteStack._suspend_stack" % BASE)
    @mock.patch("%s.CreateSuspendResumeDeleteStack._create_stack" % BASE)
    def test_create_suspend_resume_delete_stack(self,
                                                mock__create_stack,
                                                mock__suspend_stack,
                                                mock__resume_stack,
                                                mock__delete_stack):
        stacks.CreateSuspendResumeDeleteStack(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

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
            mock__create_stack.return_value)

    @mock.patch("%s.CreateSnapshotRestoreDeleteStack._delete_stack" % BASE)
    @mock.patch("%s.CreateSnapshotRestoreDeleteStack._restore_stack" % BASE)
    @mock.patch("%s.CreateSnapshotRestoreDeleteStack._snapshot_stack" % BASE,
                return_value={"id": "dummy_id"})
    @mock.patch("%s.CreateSnapshotRestoreDeleteStack._create_stack" % BASE,
                return_value=object())
    def test_create_snapshot_restore_delete_stack(self,
                                                  mock__create_stack,
                                                  mock__snapshot_stack,
                                                  mock__restore_stack,
                                                  mock__delete_stack):

        stacks.CreateSnapshotRestoreDeleteStack(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__snapshot_stack.assert_called_once_with(
            mock__create_stack.return_value)
        mock__restore_stack.assert_called_once_with(
            mock__create_stack.return_value, "dummy_id")
        mock__delete_stack.assert_called_once_with(
            mock__create_stack.return_value)

    @mock.patch("%s.CreateStackAndShowOutputViaAPI"
                "._stack_show_output_via_API" % BASE)
    @mock.patch("%s.CreateStackAndShowOutputViaAPI._create_stack" % BASE)
    def test_create_and_show_output_via_API(self,
                                            mock__create_stack,
                                            mock__stack_show_output_api):
        stacks.CreateStackAndShowOutputViaAPI(self.context).run(
            template_path=self.default_template,
            output_key=self.default_output_key,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_show_output_api.assert_called_once_with(
            mock__create_stack.return_value, self.default_output_key)

    @mock.patch("%s.CreateStackAndShowOutput._stack_show_output" % BASE)
    @mock.patch("%s.CreateStackAndShowOutput._create_stack" % BASE)
    def test_create_and_show_output(self,
                                    mock__create_stack,
                                    mock__stack_show_output):
        stacks.CreateStackAndShowOutput(self.context).run(
            template_path=self.default_template,
            output_key=self.default_output_key,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_show_output.assert_called_once_with(
            mock__create_stack.return_value, self.default_output_key)

    @mock.patch("%s.CreateStackAndListOutputViaAPI"
                "._stack_list_output_via_API" % BASE)
    @mock.patch("%s.CreateStackAndListOutputViaAPI._create_stack" % BASE)
    def test_create_and_list_output_via_API(self,
                                            mock__create_stack,
                                            mock__stack_list_output_api):
        stacks.CreateStackAndListOutputViaAPI(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_list_output_api.assert_called_once_with(
            mock__create_stack.return_value)

    @mock.patch("%s.CreateStackAndListOutput._stack_list_output" % BASE)
    @mock.patch("%s.CreateStackAndListOutput._create_stack" % BASE)
    def test_create_and_list_output(self,
                                    mock__create_stack,
                                    mock__stack_list_output):
        stacks.CreateStackAndListOutput(self.context).run(
            template_path=self.default_template,
            parameters=self.default_parameters,
            files=self.default_files,
            environment=self.default_environment)

        mock__create_stack.assert_called_once_with(
            self.default_template, self.default_parameters,
            self.default_files, self.default_environment)
        mock__stack_list_output.assert_called_once_with(
            mock__create_stack.return_value)