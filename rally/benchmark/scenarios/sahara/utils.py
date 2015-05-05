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

import random

from oslo_config import cfg
from oslo_utils import uuidutils
from saharaclient.api import base as sahara_base

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.sahara import consts as sahara_consts
from rally.benchmark import utils as bench_utils
from rally.common.i18n import _
from rally.common import log as logging
from rally import consts
from rally import exceptions

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

SAHARA_TIMEOUT_OPTS = [
    cfg.IntOpt("cluster_create_timeout", default=1800,
               help="A timeout in seconds for a cluster create operation"),
    cfg.IntOpt("cluster_delete_timeout", default=900,
               help="A timeout in seconds for a cluster delete operation"),
    cfg.IntOpt("cluster_check_interval", default=5,
               help="Cluster status polling interval in seconds"),
    cfg.IntOpt("job_execution_timeout", default=600,
               help="A timeout in seconds for a Job Execution to complete"),
    cfg.IntOpt("job_check_interval", default=5,
               help="Job Execution status polling interval in seconds")
]

benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(SAHARA_TIMEOUT_OPTS, group=benchmark_group)


class SaharaScenario(base.Scenario):
    """Base class for Sahara scenarios with basic atomic actions."""

    RESOURCE_NAME_LENGTH = 20

    @base.atomic_action_timer("sahara.list_node_group_templates")
    def _list_node_group_templates(self):
        """Return user Node Group Templates list."""
        return self.clients("sahara").node_group_templates.list()

    @base.atomic_action_timer("sahara.create_master_node_group_template")
    def _create_master_node_group_template(self, flavor_id, plugin_name,
                                           hadoop_version):
        """Create a master Node Group Template with a random name.

        :param flavor_id: The required argument for the Template
        :param plugin_name: Sahara provisioning plugin name
        :param hadoop_version: The version of Hadoop distribution supported by
                               the plugin
        :returns: The created Template
        """
        name = self._generate_random_name(prefix="master-ngt-")

        return self.clients("sahara").node_group_templates.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            flavor_id=flavor_id,
            node_processes=sahara_consts.NODE_PROCESSES[plugin_name]
            [hadoop_version]["master"])

    @base.atomic_action_timer("sahara.create_worker_node_group_template")
    def _create_worker_node_group_template(self, flavor_id, plugin_name,
                                           hadoop_version):
        """Create a worker Node Group Template with a random name.

        :param flavor_id: The required argument for the Template
        :param plugin_name: Sahara provisioning plugin name
        :param hadoop_version: The version of Hadoop distribution supported by
                               the plugin
        :returns: The created Template
        """
        name = self._generate_random_name(prefix="worker-ngt-")

        return self.clients("sahara").node_group_templates.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            flavor_id=flavor_id,
            node_processes=sahara_consts.NODE_PROCESSES[plugin_name]
            [hadoop_version]["worker"])

    @base.atomic_action_timer("sahara.delete_node_group_template")
    def _delete_node_group_template(self, node_group):
        """Delete a Node Group Template by id.

        :param node_group: The Node Group Template to be deleted
        """
        self.clients("sahara").node_group_templates.delete(node_group.id)

    def _wait_active(self, cluster_object):
        bench_utils.wait_for(
            resource=cluster_object, is_ready=self._is_cluster_active,
            update_resource=self._update_cluster,
            timeout=CONF.benchmark.cluster_create_timeout,
            check_interval=CONF.benchmark.cluster_check_interval)

    def _setup_neutron_floating_ip_pool(self, name_or_id):
        if name_or_id:
            if uuidutils.is_uuid_like(name_or_id):
                # Looks like an id is provided Return as is.
                return name_or_id
            else:
                # It's a name. Changing to id.
                for net in self.clients("neutron").list_networks()["networks"]:
                    if net["name"] == name_or_id:
                        return net["id"]
                # If the name is not found in the list. Exit with error.
                raise exceptions.BenchmarkSetupFailure(
                    "Could not resolve Floating IP Pool name %(name)s to id" %
                    name_or_id)
        else:
            # Pool is not provided. Using the one set as GW for current router.

            net = self.context["tenant"]["networks"][0]
            router_id = net["router_id"]
            router = self.clients("neutron").show_router(router_id)["router"]
            net_id = router["external_gateway_info"]["network_id"]

            return net_id

    def _setup_nova_floating_ip_pool(self, name):
        if name:
            # The name is provided returning it as is.
            return name
        else:
            # The name is not provided. Discovering
            LOG.debug("No Floating Ip Pool provided. Taking random.")
            pools = self.clients("nova").floating_ip_pools.list()

            if pools:
                return random.choice(pools).name
            else:
                LOG.warn("No Floating Ip Pools found. This may cause "
                         "instances to be unreachable.")
                return None

    def _setup_floating_ip_pool(self, node_groups, floating_ip_pool):
        if consts.Service.NEUTRON in self._clients.services().values():
            LOG.debug("Neutron detected as networking backend.")
            floating_ip_pool_value = self._setup_neutron_floating_ip_pool(
                floating_ip_pool)
        else:
            LOG.debug("Nova Network detected as networking backend.")
            floating_ip_pool_value = self._setup_nova_floating_ip_pool(
                floating_ip_pool)

        if floating_ip_pool_value:
            LOG.debug("Using floating ip pool %s." % floating_ip_pool_value)
            # If the pool is set by any means assign it to all node groups.
            for ng in node_groups:
                ng["floating_ip_pool"] = floating_ip_pool_value

        return node_groups

    def _setup_volumes(self, node_groups, volumes_per_node, volumes_size):
        if volumes_per_node:
            LOG.debug("Adding volumes config to Node Groups")
            for ng in node_groups:
                ng["volumes_per_node"] = volumes_per_node
                ng["volumes_size"] = volumes_size

        return node_groups

    def _setup_security_groups(self, node_groups, auto_security_group,
                               security_groups):
        if auto_security_group:
            LOG.debug("Auto security group enabled. Adding to Node Groups.")
        if security_groups:
            LOG.debug("Adding provided Security Groups to Node Groups.")

        for ng in node_groups:
            if auto_security_group:
                ng["auto_security_group"] = auto_security_group
            if security_groups:
                ng["security_groups"] = security_groups

        return node_groups

    def _setup_node_configs(self, node_groups, node_configs):
        if node_configs:
            LOG.debug("Adding Hadoop configs to Node Groups")
            for ng in node_groups:
                ng["node_configs"] = node_configs

        return node_groups

    def _setup_replication_config(self, hadoop_version, workers_count,
                                  plugin_name):
        replication_value = min(workers_count, 3)
        # 3 is a default Hadoop replication
        conf = sahara_consts.REPLICATION_CONFIGS[plugin_name][hadoop_version]
        LOG.debug("Using replication factor: %s" % replication_value)
        replication_config = {
            conf["target"]: {
                conf["config_name"]: replication_value
            }
        }
        return replication_config

    @base.atomic_action_timer("sahara.launch_cluster")
    def _launch_cluster(self, plugin_name, hadoop_version, flavor_id,
                        image_id, workers_count, floating_ip_pool=None,
                        volumes_per_node=None,
                        volumes_size=None, auto_security_group=None,
                        security_groups=None, node_configs=None,
                        cluster_configs=None, enable_anti_affinity=False,
                        wait_active=True):
        """Create a cluster and wait until it becomes Active.

        The cluster is created with two node groups. The master Node Group is
        created with one instance. The worker node group contains
        node_count - 1 instances.

        :param plugin_name: provisioning plugin name
        :param hadoop_version: Hadoop version supported by the plugin
        :param flavor_id: flavor which will be used to create instances
        :param image_id: image id that will be used to boot instances
        :param workers_count: number of worker instances. All plugins will
                              also add one Master instance and some plugins
                              add a Manager instance.
        :param floating_ip_pool: floating ip pool name from which Floating
                                 IPs will be allocated
        :param volumes_per_node: number of Cinder volumes that will be
                                 attached to every cluster node
        :param volumes_size: size of each Cinder volume in GB
        :param auto_security_group: boolean value. If set to True Sahara will
                                    create a Security Group for each Node Group
                                    in the Cluster automatically.
        :param security_groups: list of security groups that will be used
                                while creating VMs. If auto_security_group is
                                set to True, this list can be left empty.
        :param node_configs: configs dict that will be passed to each Node
                             Group
        :param cluster_configs: configs dict that will be passed to the
                                Cluster
        :param enable_anti_affinity: If set to true the vms will be scheduled
                                     one per compute node.
        :param wait_active: Wait until a Cluster gets int "Active" state
        :returns: created cluster
        """
        node_groups = [
            {
                "name": "master-ng",
                "flavor_id": flavor_id,
                "node_processes": sahara_consts.NODE_PROCESSES[plugin_name]
                [hadoop_version]["master"],
                "count": 1
            }, {
                "name": "worker-ng",
                "flavor_id": flavor_id,
                "node_processes": sahara_consts.NODE_PROCESSES[plugin_name]
                [hadoop_version]["worker"],
                "count": workers_count
            }
        ]

        if "manager" in (sahara_consts.NODE_PROCESSES[plugin_name]
                         [hadoop_version]):
            # Adding manager group separately as it is supported only in
            # specific configurations.

            node_groups.append({
                "name": "manager-ng",
                "flavor_id": flavor_id,
                "node_processes": sahara_consts.NODE_PROCESSES[plugin_name]
                [hadoop_version]["manager"],
                "count": 1
            })

        node_groups = self._setup_floating_ip_pool(node_groups,
                                                   floating_ip_pool)

        neutron_net_id = self._get_neutron_net_id()

        node_groups = self._setup_volumes(node_groups, volumes_per_node,
                                          volumes_size)

        node_groups = self._setup_security_groups(node_groups,
                                                  auto_security_group,
                                                  security_groups)

        node_groups = self._setup_node_configs(node_groups, node_configs)

        replication_config = self._setup_replication_config(hadoop_version,
                                                            workers_count,
                                                            plugin_name)

        # The replication factor should be set for small clusters. However the
        # cluster_configs parameter can override it
        merged_cluster_configs = self._merge_configs(replication_config,
                                                     cluster_configs)

        aa_processes = None
        if enable_anti_affinity:
            aa_processes = (sahara_consts.ANTI_AFFINITY_PROCESSES[plugin_name]
                            [hadoop_version])

        name = self._generate_random_name(prefix="sahara-cluster-")

        cluster_object = self.clients("sahara").clusters.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            node_groups=node_groups,
            default_image_id=image_id,
            net_id=neutron_net_id,
            cluster_configs=merged_cluster_configs,
            anti_affinity=aa_processes
        )

        if wait_active:
            self._wait_active(cluster_object)

        return self.clients("sahara").clusters.get(cluster_object.id)

    def _update_cluster(self, cluster):
        return self.clients("sahara").clusters.get(cluster.id)

    def _is_cluster_active(self, cluster):
        cluster_status = cluster.status.lower()

        if cluster_status == "error":
            raise exceptions.SaharaClusterFailure(
                name=cluster.name,
                action="start",
                reason=cluster.status_description)

        return cluster_status == "active"

    def _scale_cluster(self, cluster, delta):
        """The scaling helper.

        This method finds the worker node group in a cluster, builds a
        scale_object required by Sahara API and waits for the scaling to
        complete.

        NOTE: This method is not meant to be called directly in benchmarks.
        There two specific scaling methods of up and down scaling which have
        different atomic timers.
        """
        worker_node_group = [g for g in cluster.node_groups
                             if "worker" in g["name"]][0]
        scale_object = {
            "resize_node_groups": [
                {
                    "name": worker_node_group["name"],
                    "count": worker_node_group["count"] + delta
                }
            ]
        }
        self.clients("sahara").clusters.scale(cluster.id, scale_object)

        self._wait_active(cluster)

    @base.atomic_action_timer("sahara.scale_up")
    def _scale_cluster_up(self, cluster, delta):
        """Add a given number of worker nodes to the cluster.

        :param cluster: The cluster to be scaled
        :param delta: The number of workers to be added. (A positive number is
                      expected here)
        """
        self._scale_cluster(cluster, delta)

    @base.atomic_action_timer("sahara.scale_down")
    def _scale_cluster_down(self, cluster, delta):
        """Remove a given number of worker nodes from the cluster.

        :param cluster: The cluster to be scaled
        :param delta: The number of workers to be removed. (A negative number
                      is expected here)
        """
        self._scale_cluster(cluster, delta)

    @base.atomic_action_timer("sahara.delete_cluster")
    def _delete_cluster(self, cluster):
        """Delete cluster.

        :param cluster: cluster to delete
        """
        self.clients("sahara").clusters.delete(cluster.id)

        bench_utils.wait_for(
            resource=cluster.id,
            timeout=CONF.benchmark.cluster_delete_timeout,
            check_interval=CONF.benchmark.cluster_check_interval,
            is_ready=self._is_cluster_deleted)

    def _is_cluster_deleted(self, cl_id):
        try:
            self.clients("sahara").clusters.get(cl_id)
            return False
        except sahara_base.APIException:
            return True

    def _create_output_ds(self):
        """Create an output Data Source based on EDP context

        :return: The created Data Source
        """
        ds_type = self.context["sahara_output_conf"]["output_type"]
        url_prefix = self.context["sahara_output_conf"]["output_url_prefix"]

        if ds_type == "swift":
            raise exceptions.RallyException(
                _("Swift Data Sources are not implemented yet"))

        url = (url_prefix.rstrip("/") + "/%s" %
               self._generate_random_name(length=10))

        return self.clients("sahara").data_sources.create(
            name=self._generate_random_name(prefix="out_"),
            description="",
            data_source_type=ds_type,
            url=url)

    def _run_job_execution(self, job_id, cluster_id, input_id, output_id,
                           configs, job_idx):
        """Run a Job Execution and wait until it completes or fails.

        The Job Execution is accepted as successful when Oozie reports
        "success" or "succeeded" status. The failure statuses are "failed" and
        "killed".

        The timeout and the polling interval may be configured through
        "job_execution_timeout" and "job_check_interval" parameters under the
        "benchmark" section.

        :param job_id: The Job id that will be executed
        :param cluster_id: The Cluster id which will execute the Job
        :param input_id: The input Data Source id
        :param output_id: The output Data Source id
        :param configs: The config dict that will be passed as Job Execution's
                        parameters.
        :param job_idx: The index of a job in a sequence

        """
        @base.atomic_action_timer("sahara.job_execution_%s" % job_idx)
        def run(self):
            job_execution = self.clients("sahara").job_executions.create(
                job_id=job_id,
                cluster_id=cluster_id,
                input_id=input_id,
                output_id=output_id,
                configs=configs)

            bench_utils.wait_for(
                resource=job_execution.id,
                is_ready=self._job_execution_is_finished,
                timeout=CONF.benchmark.job_execution_timeout,
                check_interval=CONF.benchmark.job_check_interval)

        run(self)

    def _job_execution_is_finished(self, je_id):
        status = self.clients("sahara").job_executions.get(je_id).info[
            "status"]
        if status.lower() in ("success", "succeeded"):
            return True
        elif status.lower() in ("failed", "killed"):
            raise exceptions.RallyException(
                "Job execution %s has failed" % je_id)
        return False

    def _merge_configs(self, *configs):
        """Merge configs in special format.

        It supports merging of configs in the following format:
        applicable_target -> config_name -> config_value

        """
        result = {}
        for config_dict in configs:
            if config_dict:
                for a_target in config_dict:
                    if a_target not in result or not result[a_target]:
                        result[a_target] = {}
                    result[a_target].update(config_dict[a_target])

        return result

    def _get_neutron_net_id(self):
        """Get the Neutron Network id from context.

        If Nova Network is used as networking backend, None is returned.

        :return: Network id for Neutron or None for Nova Networking.
        """

        if consts.Service.NEUTRON not in self._clients.services().values():
            return None

        # Taking net id from context.
        net = self.context["tenant"]["networks"][0]
        neutron_net_id = net["id"]
        LOG.debug("Using neutron network %s." % neutron_net_id)
        LOG.debug("Using neutron router %s." % net["router_id"])

        return neutron_net_id
