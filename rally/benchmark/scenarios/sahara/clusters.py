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
from rally.benchmark.scenarios.sahara import utils
from rally.benchmark import types
from rally.benchmark import validation
from rally import consts
from rally.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class SaharaClusters(utils.SaharaScenario):

    @types.set(flavor=types.FlavorResourceType)
    @validation.flavor_exists('flavor')
    @validation.required_contexts("users", "sahara_image")
    @validation.number("node_count", minval=2, integer_only=True)
    @validation.required_services(consts.Service.SAHARA)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["sahara"]})
    def create_and_delete_cluster(self, flavor, node_count, plugin_name,
                                  hadoop_version, floating_ip_pool=None,
                                  neutron_net_id=None):
        """Test the Sahara Cluster launch and delete commands.

        This scenario launches a Hadoop cluster, waits until it becomes
        'Active' and deletes it.

        :param flavor: The Nova flavor that will be for nodes in the
        created node groups
        :param node_count: The total number of instances in a cluster (>= 2)
        :param plugin_name: The name of a provisioning plugin
        :param hadoop_version: The version of Hadoop distribution supported by
        the specified plugin.
        :param floating_ip_pool: The floating ip pool name from which Floating
        IPs will be allocated. Sahara will determine automatically how to treat
        this depending on it's own configurations. Defaults to None because in
        some cases Sahara may work w/o Floating IPs.
        :param neutron_management_network: The id of a Neutron network that
        will be used for fixed IPs. This parameter is ignored when Nova Network
        is set up.
        """

        tenant_id = self.clients("keystone").tenant_id
        image_id = self.context()["sahara_images"][tenant_id]

        LOG.debug("Using Image: %s" % image_id)

        cluster = self._launch_cluster(
            flavor_id=flavor,
            image_id=image_id,
            node_count=node_count,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            floating_ip_pool=floating_ip_pool,
            neutron_net_id=neutron_net_id)

        self._delete_cluster(cluster)
