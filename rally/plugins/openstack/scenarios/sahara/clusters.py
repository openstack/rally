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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.sahara import utils
from rally.task import types
from rally.task import validation

LOG = logging.getLogger(__name__)

"""Scenarios for Sahara clusters."""


@types.convert(flavor={"type": "nova_flavor"},
               master_flavor={"type": "nova_flavor"},
               worker_flavor={"type": "nova_flavor"},
               neutron_net={"type": "neutron_network"},
               floating_ip_pool={"type": "neutron_network"})
@validation.flavor_exists("master_flavor")
@validation.flavor_exists("worker_flavor")
@validation.required_contexts("users", "sahara_image")
@validation.number("workers_count", minval=1, integer_only=True)
@validation.required_services(consts.Service.SAHARA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["sahara"]},
                    name="SaharaClusters.create_and_delete_cluster")
class CreateAndDeleteCluster(utils.SaharaScenario):

    def run(self, workers_count, plugin_name, hadoop_version,
            master_flavor=None, worker_flavor=None, flavor=None,
            floating_ip_pool=None, volumes_per_node=None,
            volumes_size=None, auto_security_group=None,
            security_groups=None, node_configs=None,
            cluster_configs=None, enable_anti_affinity=False,
            enable_proxy=False, use_autoconfig=True):
        """Launch and delete a Sahara Cluster.

        This scenario launches a Hadoop cluster, waits until it becomes
        'Active' and deletes it.

        :param flavor: Nova flavor that will be for nodes in the
                       created node groups. Deprecated.
        :param master_flavor: Nova flavor that will be used for the master
                              instance of the cluster
        :param worker_flavor: Nova flavor that will be used for the workers of
                              the cluster
        :param workers_count: number of worker instances in a cluster
        :param plugin_name: name of a provisioning plugin
        :param hadoop_version: version of Hadoop distribution supported by
                               the specified plugin.
        :param floating_ip_pool: floating ip pool name from which Floating
                                 IPs will be allocated. Sahara will determine
                                 automatically how to treat this depending on
                                 its own configurations. Defaults to None
                                 because in some cases Sahara may work w/o
                                 Floating IPs.
        :param volumes_per_node: number of Cinder volumes that will be
                                 attached to every cluster node
        :param volumes_size: size of each Cinder volume in GB
        :param auto_security_group: boolean value. If set to True Sahara will
                                    create a Security Group for each Node Group
                                    in the Cluster automatically.
        :param security_groups: list of security groups that will be used
                                while creating VMs. If auto_security_group
                                is set to True, this list can be left empty.
        :param node_configs: config dict that will be passed to each Node
                             Group
        :param cluster_configs: config dict that will be passed to the
                                Cluster
        :param enable_anti_affinity: If set to true the vms will be scheduled
                                     one per compute node.
        :param enable_proxy: Use Master Node of a Cluster as a Proxy node and
                             do not assign floating ips to workers.
        :param use_autoconfig: If True, instances of the node group will be
                               automatically configured during cluster
                               creation. If False, the configuration values
                               should be specify manually
        """

        image_id = self.context["tenant"]["sahara"]["image"]

        LOG.debug("Using Image: %s" % image_id)

        cluster = self._launch_cluster(
            flavor_id=flavor,
            master_flavor_id=master_flavor,
            worker_flavor_id=worker_flavor,
            image_id=image_id,
            workers_count=workers_count,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            floating_ip_pool=floating_ip_pool,
            volumes_per_node=volumes_per_node,
            volumes_size=volumes_size,
            auto_security_group=auto_security_group,
            security_groups=security_groups,
            node_configs=node_configs,
            cluster_configs=cluster_configs,
            enable_anti_affinity=enable_anti_affinity,
            enable_proxy=enable_proxy,
            use_autoconfig=use_autoconfig)

        self._delete_cluster(cluster)


@types.convert(flavor={"type": "nova_flavor"},
               master_flavor={"type": "nova_flavor"},
               worker_flavor={"type": "nova_flavor"})
@validation.flavor_exists("master_flavor")
@validation.flavor_exists("worker_flavor")
@validation.required_services(consts.Service.SAHARA)
@validation.required_contexts("users", "sahara_image")
@validation.number("workers_count", minval=1, integer_only=True)
@scenario.configure(context={"cleanup": ["sahara"]},
                    name="SaharaClusters.create_scale_delete_cluster")
class CreateScaleDeleteCluster(utils.SaharaScenario):

    def run(self, master_flavor, worker_flavor, workers_count,
            plugin_name, hadoop_version, deltas, flavor=None,
            floating_ip_pool=None, volumes_per_node=None,
            volumes_size=None, auto_security_group=None,
            security_groups=None, node_configs=None,
            cluster_configs=None, enable_anti_affinity=False,
            enable_proxy=False, use_autoconfig=True):
        """Launch, scale and delete a Sahara Cluster.

        This scenario launches a Hadoop cluster, waits until it becomes
        'Active'. Then a series of scale operations is applied. The scaling
        happens according to numbers listed in :param deltas. Ex. if
        deltas is set to [2, -2] it means that the first scaling operation will
        add 2 worker nodes to the cluster and the second will remove two.

        :param flavor: Nova flavor that will be for nodes in the
                       created node groups. Deprecated.
        :param master_flavor: Nova flavor that will be used for the master
                              instance of the cluster
        :param worker_flavor: Nova flavor that will be used for the workers of
                              the cluster
        :param workers_count: number of worker instances in a cluster
        :param plugin_name: name of a provisioning plugin
        :param hadoop_version: version of Hadoop distribution supported by
                               the specified plugin.
        :param deltas: list of integers which will be used to add or
                       remove worker nodes from the cluster
        :param floating_ip_pool: floating ip pool name from which Floating
                                 IPs will be allocated. Sahara will determine
                                 automatically how to treat this depending on
                                 its own configurations. Defaults to None
                                 because in some cases Sahara may work w/o
                                 Floating IPs.
        :param neutron_net_id: id of a Neutron network that will be used
                               for fixed IPs. This parameter is ignored when
                               Nova Network is set up.
        :param volumes_per_node: number of Cinder volumes that will be
                                 attached to every cluster node
        :param volumes_size: size of each Cinder volume in GB
        :param auto_security_group: boolean value. If set to True Sahara will
                                    create a Security Group for each Node Group
                                    in the Cluster automatically.
        :param security_groups: list of security groups that will be used
                                while creating VMs. If auto_security_group
                                is set to True this list can be left empty.
        :param node_configs: configs dict that will be passed to each Node
                             Group
        :param cluster_configs: configs dict that will be passed to the
                                Cluster
        :param enable_anti_affinity: If set to true the vms will be scheduled
                                     one per compute node.
        :param enable_proxy: Use Master Node of a Cluster as a Proxy node and
                             do not assign floating ips to workers.
        :param use_autoconfig: If True, instances of the node group will be
                               automatically configured during cluster
                               creation. If False, the configuration values
                               should be specify manually
        """

        image_id = self.context["tenant"]["sahara"]["image"]

        LOG.debug("Using Image: %s" % image_id)

        cluster = self._launch_cluster(
            flavor_id=flavor,
            master_flavor_id=master_flavor,
            worker_flavor_id=worker_flavor,
            image_id=image_id,
            workers_count=workers_count,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            floating_ip_pool=floating_ip_pool,
            volumes_per_node=volumes_per_node,
            volumes_size=volumes_size,
            auto_security_group=auto_security_group,
            security_groups=security_groups,
            node_configs=node_configs,
            cluster_configs=cluster_configs,
            enable_anti_affinity=enable_anti_affinity,
            enable_proxy=enable_proxy,
            use_autoconfig=use_autoconfig)

        for delta in deltas:
            # The Cluster is fetched every time so that its node groups have
            # correct 'count' values.
            cluster = self.clients("sahara").clusters.get(cluster.id)

            if delta == 0:
                # Zero scaling makes no sense.
                continue
            elif delta > 0:
                self._scale_cluster_up(cluster, delta)
            elif delta < 0:
                self._scale_cluster_down(cluster, delta)

        self._delete_cluster(cluster)