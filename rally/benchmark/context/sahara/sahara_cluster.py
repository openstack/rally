# Copyright 2014: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo.config import cfg

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import utils as cleanup_utils
from rally.benchmark.scenarios.sahara import utils
from rally.benchmark import utils as bench_utils
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class SaharaCluster(base.Context):
    """Context class for setting up the Cluster an EDP job."""

    __ctx_name__ = "sahara_cluster"
    __ctx_order__ = 413
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
            "plugin_name": {
                "type": "string"
            },
            "hadoop_version": {
                "enum": ["1.2.1", "2.3.0", "2.4.1"]
            },
            "node_count": {
                "type": "integer",
                "minimum": 2
            },
            "flavor_id": {
                "type": "string",
            },
            "floating_ip_pool": {
                "type": "string",
            },
            "neutron_net_id": {
                "type": "string",
            },
            "volumes_per_node": {
                "type": "integer",
                "minimum": 1
            },
            "volumes_size": {
                "type": "integer",
                "minimum": 1
            },
            "node_configs": {
                "type": "object"
            },
            "cluster_configs": {
                "type": "object"
            }
        },
        "additionalProperties": False,
        "required": ["plugin_name", "hadoop_version", "node_count",
                     "flavor_id"]
    }

    def __init__(self, context):
        super(SaharaCluster, self).__init__(context)
        self.context["sahara_clusters"] = {}

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Sahara Cluster`"))
    def setup(self):
        ready_tenants = set()
        wait_dict = dict()

        for user in self.context.get("users", []):
            tenant_id = user["tenant_id"]
            if tenant_id not in ready_tenants:
                ready_tenants.add(tenant_id)

                clients = osclients.Clients(user["endpoint"])

                image_id = self.context["sahara_images"][tenant_id]

                cluster = utils.SaharaScenario(
                    context=self.context, clients=clients)._launch_cluster(
                        plugin_name=self.config["plugin_name"],
                        hadoop_version=self.config["hadoop_version"],
                        flavor_id=self.config["flavor_id"],
                        node_count=self.config["node_count"],
                        image_id=image_id,
                        floating_ip_pool=self.config.get("floating_ip_pool"),
                        neutron_net_id=self.config.get("neutron_net_id"),
                        volumes_per_node=self.config.get("volumes_per_node"),
                        volumes_size=self.config.get("volumes_size", 1),
                        node_configs=self.config.get("node_configs"),
                        cluster_configs=self.config.get("cluster_configs"),
                        wait_active=False)

                self.context["sahara_clusters"][tenant_id] = cluster.id

                # Need to save the client instance to poll for active status
                wait_dict[cluster.id] = clients.sahara()

        def all_active(dct):
            for cl_id, client in dct.items():
                cl = client.clusters.get(cl_id)
                if cl.status.lower() != "active":
                    return False
            return True

        bench_utils.wait_for(
            resource=wait_dict,
            is_ready=all_active,
            timeout=CONF.benchmark.cluster_create_timeout,
            check_interval=CONF.benchmark.cluster_check_interval)

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Sahara Cluster`"))
    def cleanup(self):
        clean_tenants = set()
        for user in self.context.get("users", []):
            tenant_id = user["tenant_id"]
            if tenant_id not in clean_tenants:
                clean_tenants.add(tenant_id)

                sahara = osclients.Clients(user["endpoint"]).sahara()
                cleanup_utils.delete_clusters(sahara)