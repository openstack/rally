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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ironic import utils
from rally.task import validation


"""Scenarios for ironic nodes."""


@validation.required_parameters("driver")
@validation.required_services(consts.Service.IRONIC)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["ironic"]},
                    name="IronicNodes.create_and_list_node")
class CreateAndListNode(utils.IronicScenario):

    def run(self, associated=None, maintenance=None,
            marker=None, limit=None, detail=False, sort_key=None,
            sort_dir=None, **kwargs):
        """Create and list nodes.

        :param associated: Optional. Either a Boolean or a string
                           representation of a Boolean that indicates whether
                           to return a list of associated (True or "True") or
                           unassociated (False or "False") nodes.
        :param maintenance: Optional. Either a Boolean or a string
                            representation of a Boolean that indicates whether
                            to return nodes in maintenance mode (True or
                            "True"), or not in maintenance mode (False or
                            "False").
        :param marker: Optional, the UUID of a node, eg the last
                       node from a previous result set. Return
                       the next result set.
        :param limit: The maximum number of results to return per
                      request, if:
            1) limit > 0, the maximum number of nodes to return.
            2) limit == 0, return the entire list of nodes.
            3) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Ironic API
               (see Ironic's api.max_limit option).
        :param detail: Optional, boolean whether to return detailed
                       information about nodes.
        :param sort_key: Optional, field used for sorting.
        :param sort_dir: Optional, direction of sorting, either 'asc' (the
                         default) or 'desc'.
        :param kwargs: Optional additional arguments for node creation
        """

        self._create_node(**kwargs)

        self._list_nodes(
            associated=associated, maintenance=maintenance, marker=marker,
            limit=limit, detail=detail, sort_key=sort_key, sort_dir=sort_dir)


@validation.required_parameters("driver")
@validation.required_services(consts.Service.IRONIC)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["ironic"]},
                    name="IronicNodes.create_and_delete_node")
class CreateAndDeleteNode(utils.IronicScenario):

    def run(self, **kwargs):
        """Create and delete node.

        :param kwargs: Optional additional arguments for node creation
        """
        node = self._create_node(**kwargs)
        self._delete_node(node.uuid)