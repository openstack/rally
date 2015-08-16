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

from oslo_config import cfg


from rally.common import utils
from rally.plugins.openstack import scenario
from rally.task import atomic


IRONIC_BENCHMARK_OPTS = [
    cfg.FloatOpt("ironic_node_create_poll_interval",
                 default=1.0,
                 help="Interval(in sec) between checks when waiting for node "
                      "creation."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(IRONIC_BENCHMARK_OPTS, group=benchmark_group)


class IronicScenario(scenario.OpenStackScenario):
    """Base class for Ironic scenarios with basic atomic actions."""

    @atomic.action_timer("ironic.create_node")
    def _create_node(self, **kwargs):
        """Create node immediately.

        :param kwargs: optional parameters to create image
        :returns: node object
        """
        if "name" not in kwargs:
            # NOTE(rvasilets): can't use _generate_random_name() because
            # ironic have specific format for node name.
            # Check that the supplied hostname conforms to:
            # * http://en.wikipedia.org/wiki/Hostname
            # * http://tools.ietf.org/html/rfc952
            # * http://tools.ietf.org/html/rfc1123
            # or the name could be just uuid.
            kwargs["name"] = utils.generate_random_name(
                prefix="rally", choice=string.ascii_lowercase + string.digits)

        return self.admin_clients("ironic").node.create(**kwargs)

    @atomic.action_timer("ironic.list_nodes")
    def _list_nodes(self, associated=None, maintenance=None, marker=None,
                    limit=None, detail=False, sort_key=None, sort_dir=None):
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
        :param detail: Optional, boolean whether to return detailed information
                       about nodes.
        :param sort_key: Optional, field used for sorting.
        :param sort_dir: Optional, direction of sorting, either 'asc' (the
                         default) or 'desc'.
        :returns: A list of nodes.
        """
        return self.admin_clients("ironic").node.list(
            associated=associated, maintenance=maintenance, marker=marker,
            limit=limit, detail=detail, sort_key=sort_key, sort_dir=sort_dir)

    @atomic.action_timer("ironic.delete_node")
    def _delete_node(self, node_id):
        """Delete the node with specific id.

        :param node_id: id of the node to be deleted
        """
        self.admin_clients("ironic").node.delete(node_id)
