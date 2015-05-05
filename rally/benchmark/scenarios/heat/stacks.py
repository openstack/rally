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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.heat import utils
from rally.benchmark import types
from rally.benchmark import validation
from rally import consts


class HeatStacks(utils.HeatScenario):
    """Benchmark scenarios for Heat stacks."""

    RESOURCE_NAME_PREFIX = "rally_stack_"
    RESOURCE_NAME_LENGTH = 7

    @types.set(template_path=types.FileType)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_and_list_stack(self, template_path):
        """Add a stack and then list all stacks.

        Measure the "heat stack-create" and "heat stack-list" commands
        performance.

        :param template_path: path to stack template file
        """
        self._create_stack(template_path)
        self._list_stacks()

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario()
    def list_stacks_and_resources(self):
        """List all resources from tenant stacks."""

        stacks = self._list_stacks()
        with base.AtomicAction(
                self, "heat.list_resources_of_%s_stacks" % len(stacks)):
            for stack in stacks:
                self.clients("heat").resources.list(stack.id)

    @types.set(template_path=types.FileType)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_and_delete_stack(self, template_path):
        """Add and then delete a stack.

        Measure the "heat stack-create" and "heat stack-delete" commands
        performance.

        :param template_path: path to stack template file
        """

        stack = self._create_stack(template_path)
        self._delete_stack(stack)

    @types.set(template_path=types.FileType)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_check_delete_stack(self, template_path):
        """Create, check and delete a stack.

        Measure the performance of the following commands:
        - heat stack-create
        - heat action-check
        - heat stack-delete

        :param template_path: path to stack template file
        """

        stack = self._create_stack(template_path)
        self._check_stack(stack)
        self._delete_stack(stack)

    @types.set(template_path=types.FileType,
               updated_template_path=types.FileType)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_update_delete_stack(self, template_path, updated_template_path):
        """Add, update and then delete a stack.

        Measure the "heat stack-create", "heat stack-update"
        and "heat stack-delete" commands performance.

        :param template_path: path to stack template file
        :param updated_template_path: path to updated stack template file
        """

        stack = self._create_stack(template_path)
        self._update_stack(stack, updated_template_path)
        self._delete_stack(stack)

    @types.set(template_path=types.FileType)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_suspend_resume_delete_stack(self, template_path):
        """Create, suspend-resume and then delete a stack.

        Measure performance of the following commands:
        heat stack-create
        heat action-suspend
        heat action-resume
        heat stack-delete

        :param template_path: path to stack template file
        """

        s = self._create_stack(template_path)
        self._suspend_stack(s)
        self._resume_stack(s)
        self._delete_stack(s)

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario()
    def list_stacks_and_events(self):
        """List events from tenant stacks."""

        stacks = self._list_stacks()
        with base.AtomicAction(
                self, "heat.list_events_of_%s_stacks" % len(stacks)):
            for stack in stacks:
                self.clients("heat").events.list(stack.id)
