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

from oslo.config import cfg
from saharaclient.api import base as sahara_base

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils
from rally.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

CREATE_CLUSTER_OPTS = [
    cfg.IntOpt("cluster_create_timeout", default=600,
               help="A timeout in seconds for a cluster create operation"),
    cfg.IntOpt("cluster_check_interval", default=5,
               help="Cluster status polling interval in seconds")
]

benchmark_group = cfg.OptGroup(name='benchmark', title='benchmark options')
CONF.register_opts(CREATE_CLUSTER_OPTS, group=benchmark_group)


class SaharaScenario(base.Scenario):

    RESOURCE_NAME_LENGTH = 20

    # TODO(nkonovalov): Add other provisioning plugins
    NODE_PROCESSES = {
        "vanilla": {
            "1.2.1": {
                "master": ["namenode", "jobtracker"],
                "worker": ["datanode", "tasktracker"]
            },
            "2.3.0": {
                "master": ["namenode", "resourcemanager", "historyserver"],
                "worker": ["datanode", "nodemanager"]
            }
        }
    }

    REPLICATION_CONFIGS = {
        "vanilla": {
            "1.2.1": {
                "target": "HDFS",
                "config_name": "dfs.replication"
            },
            "2.3.0": {
                "target": "HDFS",
                "config_name": "dfs.replication"
            }
        }
    }

    @base.atomic_action_timer('sahara.list_node_group_templates')
    def _list_node_group_templates(self):
        """Returns user Node Group Templates list."""

        return self.clients("sahara").node_group_templates.list()

    @base.atomic_action_timer('sahara.create_master_node_group_template')
    def _create_master_node_group_template(self, flavor_id, plugin_name,
                                           hadoop_version):
        """Creates a master Node Group Template with a random name.

        :param flavor_id: The required argument for the Template
        :param plugin_name: Sahara provisioning plugin name
        :param hadoop_version: The version of Hadoop distribution supported by
            the plugin
        :return: The created Template
        """

        name = self._generate_random_name(prefix="master-ngt-")

        return self.clients("sahara").node_group_templates.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            flavor_id=flavor_id,
            node_processes=self.NODE_PROCESSES[plugin_name][hadoop_version]
            ["master"])

    @base.atomic_action_timer('sahara.create_worker_node_group_template')
    def _create_worker_node_group_template(self, flavor_id, plugin_name,
                                           hadoop_version):
        """Creates a worker Node Group Template with a random name.

        :param flavor_id: The required argument for the Template
        :param plugin_name: Sahara provisioning plugin name
        :param hadoop_version: The version of Hadoop distribution supported by
            the plugin
        :return: The created Template
        """

        name = self._generate_random_name(prefix="worker-ngt-")

        return self.clients("sahara").node_group_templates.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            flavor_id=flavor_id,
            node_processes=self.NODE_PROCESSES[plugin_name][hadoop_version]
            ["worker"])

    @base.atomic_action_timer('sahara.delete_node_group_template')
    def _delete_node_group_template(self, node_group):
        """Deletes a Node Group Template by id.

        :param node_group: The Node Group Template to be deleted
        :return:
        """

        self.clients("sahara").node_group_templates.delete(node_group.id)

    @base.atomic_action_timer('sahara.launch_cluster')
    def _launch_cluster(self, plugin_name, hadoop_version, flavor_id,
                        image_id, node_count, floating_ip_pool=None,
                        neutron_net_id=None):
        """Creates a cluster and wait until it becomes Active.

        The cluster is created with two node groups. The master Node Group is
        created with one instance. The worker node group contains
        node_count - 1 instances.

        :param plugin_name: The provisioning plugin name
        :param hadoop_version: Hadoop version supported by the plugin
        :param flavor_id: The flavor which will be used to create instances
        :param image_id: The image id that will be used to boot instances
        :param node_count: The total number of instances. 1 master node, others
        for the workers
        :param floating_ip_pool: The floating ip pool name from which Floating
        IPs will be allocated
        :param neutron_net_id: The network id to allocate Fixed IPs
        from when Neutron is enabled for networking
        :return: The created cluster
        """

        node_groups = [
            {
                "name": "master-ng",
                "flavor_id": flavor_id,
                "node_processes": self.NODE_PROCESSES[plugin_name]
                [hadoop_version]["master"],
                "count": 1
            }, {
                "name": "worker-ng",
                "flavor_id": flavor_id,
                "node_processes": self.NODE_PROCESSES[plugin_name]
                [hadoop_version]["worker"],
                "count": node_count - 1
            }
        ]

        if floating_ip_pool:
            LOG.debug("Floating IP pool is set. Appending to Node Groups")
            for ng in node_groups:
                ng["floating_ip_pool"] = floating_ip_pool

        name = self._generate_random_name(prefix="sahara-cluster-")

        replication_value = min(node_count - 1, 3)
        # 3 is a default Hadoop replication

        conf = self.REPLICATION_CONFIGS[plugin_name][hadoop_version]
        LOG.debug("Using replication factor: %s" % replication_value)

        cluster_object = self.clients("sahara").clusters.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            node_groups=node_groups,
            default_image_id=image_id,
            net_id=neutron_net_id,
            cluster_configs={conf["target"]: {
                conf["config_name"]: replication_value}
            }
        )

        def is_active(cluster_id):
            return self.clients("sahara").clusters.get(
                cluster_id).status.lower() == "active"

        bench_utils.wait_for(
            resource=cluster_object.id, is_ready=is_active,
            timeout=CONF.benchmark.cluster_create_timeout,
            check_interval=CONF.benchmark.cluster_check_interval)

        return self.clients("sahara").clusters.get(cluster_object.id)

    @base.atomic_action_timer('sahara.delete_cluster')
    def _delete_cluster(self, cluster):
        """Calls a Cluster delete by id and waits for complete deletion.

        :param cluster: The Cluster to be deleted
        :return:
        """

        self.clients("sahara").clusters.delete(cluster.id)

        def is_deleted(cl_id):
            try:
                self.clients("sahara").clusters.get(cl_id)
                return False
            except sahara_base.APIException:
                return True

        bench_utils.wait_for(resource=cluster.id, is_ready=is_deleted)
