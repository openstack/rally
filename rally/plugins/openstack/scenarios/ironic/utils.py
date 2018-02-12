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

import string

from rally.common import cfg
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils


CONF = cfg.CONF


class IronicScenario(scenario.OpenStackScenario):
    """Base class for Ironic scenarios with basic atomic actions."""

    # NOTE(stpierre): Ironic has two name checkers. The new-style
    # checker, in API v1.10+, is quite relaxed and will Just Work with
    # the default random name pattern. (See
    # https://bugs.launchpad.net/ironic/+bug/1434376.) The old-style
    # checker *claims* to implement RFCs 952 and 1123, but it doesn't
    # actually. (See https://bugs.launchpad.net/ironic/+bug/1468508
    # for details.) The default RESOURCE_NAME_FORMAT works fine for
    # the new-style checker, but the old-style checker only allows
    # underscores after the first dot, for reasons that I'm sure are
    # entirely obvious, so we have to supply a bespoke format for
    # Ironic names.
    RESOURCE_NAME_FORMAT = "s-rally-XXXXXXXX-XXXXXXXX"
    RESOURCE_NAME_ALLOWED_CHARACTERS = string.ascii_lowercase + string.digits

    @atomic.action_timer("ironic.create_node")
    def _create_node(self, driver, properties, **kwargs):
        """Create node immediately.

        :param driver: The name of the driver used to manage this Node.
        :param properties: Key/value pair describing the physical
            characteristics of the node.
        :param kwargs: optional parameters to create image
        :returns: node object
        """
        kwargs["name"] = self.generate_random_name()
        node = self.admin_clients("ironic").node.create(driver=driver,
                                                        properties=properties,
                                                        **kwargs)

        self.sleep_between(CONF.openstack.ironic_node_create_poll_interval)
        node = utils.wait_for_status(
            node,
            ready_statuses=["AVAILABLE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.ironic_node_create_timeout,
            check_interval=CONF.openstack.ironic_node_poll_interval,
            id_attr="uuid", status_attr="provision_state"
        )

        return node

    @atomic.action_timer("ironic.list_nodes")
    def _list_nodes(self, associated=None, maintenance=None, detail=False,
                    sort_dir=None):
        """Return list of nodes.

        :param associated: Optional. Either a Boolean or a string
                           representation of a Boolean that indicates whether
                           to return a list of associated (True or "True") or
                           unassociated (False or "False") nodes.
        :param maintenance: Optional. Either a Boolean or a string
                            representation of a Boolean that indicates whether
                            to return nodes in maintenance mode (True or
                            "True"), or not in maintenance mode (False or
                            "False").
        :param detail: Optional, boolean whether to return detailed information
                       about nodes.
        :param sort_dir: Optional, direction of sorting, either 'asc' (the
                         default) or 'desc'.
        :returns: A list of nodes.
        """
        return self.admin_clients("ironic").node.list(
            associated=associated, maintenance=maintenance, detail=detail,
            sort_dir=sort_dir)

    @atomic.action_timer("ironic.delete_node")
    def _delete_node(self, node):
        """Delete the node with specific id.

        :param node: Ironic node object
        """
        self.admin_clients("ironic").node.delete(node.uuid)

        utils.wait_for_status(
            node,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.ironic_node_delete_timeout,
            check_interval=CONF.openstack.ironic_node_poll_interval,
            id_attr="uuid", status_attr="provision_state"
        )
