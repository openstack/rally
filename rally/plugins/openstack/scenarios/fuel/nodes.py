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

import random

from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.fuel import utils
from rally.task import validation


"""Scenarios for Fuel nodes."""


@validation.required_clients("fuel", admin=True)
@validation.required_openstack(admin=True)
@validation.required_contexts("fuel_environments")
@scenario.configure(name="FuelNodes.add_and_remove_node")
class AddAndRemoveNode(utils.FuelScenario):

    def run(self, node_roles=None):
        """Add node to environment and remove.

        :param node_roles: list. Roles, which node should be assigned to
            env with
        """

        env_id = random.choice(self.context["fuel"]["environments"])

        node_id = self._get_free_node_id()
        self._add_node(env_id, [node_id], node_roles)
        self._remove_node(env_id, node_id)
