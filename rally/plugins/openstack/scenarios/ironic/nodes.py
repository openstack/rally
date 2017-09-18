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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ironic import utils
from rally.task import validation


"""Scenarios for ironic nodes."""


@logging.log_deprecated_args("Useless arguments detected", "0.10.0",
                             ("marker", "limit", "sort_key"), once=True)
@validation.add("required_services", services=[consts.Service.IRONIC])
@validation.add("restricted_parameters", param_names="name")
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["ironic"]},
                    name="IronicNodes.create_and_list_node",
                    platform="openstack")
class CreateAndListNode(utils.IronicScenario):

    def run(self, driver, properties=None, associated=None, maintenance=None,
            detail=False, sort_dir=None, marker=None, limit=None,
            sort_key=None, **kwargs):
        """Create and list nodes.

        :param driver: The name of the driver used to manage this Node.
        :param properties: Key/value pair describing the physical
            characteristics of the node.
        :param associated: Optional argument of list request. Either a Boolean
            or a string representation of a Boolean that indicates whether to
            return a list of associated (True or "True") or unassociated
            (False or "False") nodes.
        :param maintenance: Optional argument of list request. Either a Boolean
            or a string representation of a Boolean that indicates whether
            to return nodes in maintenance mode (True or "True"), or not in
            maintenance mode (False or "False").
        :param detail: Optional, boolean whether to return detailed
                       information about nodes.
        :param sort_dir: Optional, direction of sorting, either 'asc' (the
                         default) or 'desc'.
        :param marker: DEPRECATED since Rally 0.10.0
        :param limit: DEPRECATED since Rally 0.10.0
        :param sort_key: DEPRECATED since Rally 0.10.0
        :param kwargs: Optional additional arguments for node creation
        """

        node = self._create_node(driver, properties, **kwargs)
        list_nodes = self._list_nodes(
            associated=associated, maintenance=maintenance, detail=detail,
            sort_dir=sort_dir)
        self.assertIn(node.name, [n.name for n in list_nodes])


@validation.add("required_services", services=[consts.Service.IRONIC])
@validation.add("restricted_parameters", param_names="name")
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["ironic"]},
                    name="IronicNodes.create_and_delete_node",
                    platform="openstack")
class CreateAndDeleteNode(utils.IronicScenario):

    def run(self, driver, properties=None, **kwargs):
        """Create and delete node.

        :param driver: The name of the driver used to manage this Node.
        :param properties: Key/value pair describing the physical
            characteristics of the node.
        :param kwargs: Optional additional arguments for node creation
        """
        node = self._create_node(driver, properties, **kwargs)
        self._delete_node(node)
