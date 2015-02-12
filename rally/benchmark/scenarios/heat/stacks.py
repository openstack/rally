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
from rally.benchmark import validation
from rally import consts


class HeatStacks(utils.HeatScenario):
    """Benchmark scenarios for Heat stacks."""

    RESOURCE_NAME_PREFIX = "rally_stack_"
    RESOURCE_NAME_LENGTH = 7

    @staticmethod
    def _get_template_from_file(template_path):
        template = None
        if template_path:
            try:
                with open(template_path, "r") as f:
                    template = f.read()
            except IOError:
                raise IOError("Provided path '%(template_path)s' is not valid"
                              % {"template_path": template_path})
        return template

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_and_list_stack(self, template_path=None):
        """Add a stack and then list all stacks.

        Measure the "heat stack-create" and "heat stack-list" commands
        performance.

        :param template_path: path to template file. If None or incorrect,
                              then default empty template will be used.
        """

        template = self._get_template_from_file(template_path)
        self._create_stack(template)
        self._list_stacks()

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario()
    def list_stacks_and_resources(self):
        """List resources from tenant stacks."""

        stacks = self._list_stacks()
        with base.AtomicAction(
                self, "heat.list_resources_of_%s_stacks" % len(stacks)):
            for stack in stacks:
                self.clients("heat").resources.list(stack.id)

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_and_delete_stack(self, template_path=None):
        """Add and then delete a stack.

        Measure the "heat stack-create" and "heat stack-delete" commands
        performance.

        :param template_path: path to template file. If None or incorrect,
                              then default empty template will be used.
        """

        template = self._get_template_from_file(template_path)
        stack = self._create_stack(template)
        self._delete_stack(stack)

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_update_delete_stack(self, template_path=None,
                                   updated_template_path=None):
        """Add, update and then delete a stack.

        Measure the "heat stack-create", "heat stack-update"
        and "heat stack-delete" commands performance.

        :param template_path: path to template file. If None or incorrect,
                              then default empty template will be used.
        :param updated_template_path: path to template file that will be used
                                      for stack update. If None or incorrect,
                                      then default empty template will be
                                      used instead.
        """

        template = self._get_template_from_file(template_path)
        stack = self._create_stack(template)
        updated_template = self._get_template_from_file(updated_template_path)
        self._update_stack(stack, updated_template)
        self._delete_stack(stack)

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_suspend_resume_delete_stack(self, template_path=None):
        """Create, suspend-resume and then delete a stack.

        Measure performance of the following commands:
        heat stack-create
        heat action-suspend
        heat action-resume
        heat stack-delete

        :param template_path: path to template file. If None or incorrect,
                              then default empty template will be used.
        """

        template = self._get_template_from_file(template_path)
        s = self._create_stack(template)
        self._suspend_stack(s)
        self._resume_stack(s)
        self._delete_stack(s)