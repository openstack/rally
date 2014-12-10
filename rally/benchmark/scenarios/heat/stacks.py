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

    RESOURCE_NAME_PREFIX = "rally_stack_"
    RESOURCE_NAME_LENGTH = 7

    def _get_template_from_file(self, template_path):
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
        """Test adding an stack and then listing all stacks.

        This scenario is a very useful tool to measure
        the "heat stack-create" and "heat stack-list" command performance.

        :param template_path: path to template file. if it's None or incorrect,
                              will be used default empty template.
        """

        stack_name = self._generate_random_name()
        template = self._get_template_from_file(template_path)

        self._create_stack(stack_name, template)
        self._list_stacks()

    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["heat"]})
    def create_and_delete_stack(self, template_path=None):
        """Test adds and then deletes stack.

        This scenario is a very useful tool to measure
        the "heat stack-create" and "heat stack-delete" command performance.

        :param template_path: path to template file. if it's None or incorrect,
                              will be used default empty template.
        """
        stack_name = self._generate_random_name()
        template = self._get_template_from_file(template_path)

        stack = self._create_stack(stack_name, template)
        self._delete_stack(stack)
