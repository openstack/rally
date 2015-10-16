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

import yaml

from rally.plugins.openstack import scenario
from rally.task import atomic


class MistralScenario(scenario.OpenStackScenario):
    """Base class for Mistral scenarios with basic atomic actions."""

    @atomic.action_timer("mistral.list_workbooks")
    def _list_workbooks(self):
        """Gets list of existing workbooks."""
        return self.clients("mistral").workbooks.list()

    @atomic.action_timer("mistral.create_workbook")
    def _create_workbook(self, definition):
        """Create a new workbook.

        :param definition: workbook description in string
                           (yaml string) format
        :returns: workbook object
        """
        definition = yaml.safe_load(definition)
        definition["name"] = self.generate_random_name()
        definition = yaml.safe_dump(definition)

        return self.clients("mistral").workbooks.create(definition)

    @atomic.action_timer("mistral.delete_workbook")
    def _delete_workbook(self, wb_name):
        """Delete the given workbook.

        :param wb_name: the name of workbook that would be deleted.
        """
        self.clients("mistral").workbooks.delete(wb_name)
