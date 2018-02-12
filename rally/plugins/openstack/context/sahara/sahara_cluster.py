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

from rally.common import cfg
from rally.common import utils as rutils
from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.sahara import utils
from rally.task import context
from rally.task import utils as bench_utils


CONF = cfg.CONF


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="sahara_cluster", platform="openstack", order=441)
class SaharaCluster(context.Context):
    """Context class for setting up the Cluster an EDP job."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "plugin_name": {
                "type": "string"
            },
            "hadoop_version": {
                "type": "string",
            },
            "workers_count": {
                "type": "integer",
                "minimum": 1
            },
            "flavor_id": {
                "type": "string",
            },
            "master_flavor_id": {
                "type": "string",
            },
            "worker_flavor_id": {
                "type": "string",
            },
            "floating_ip_pool": {
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
            "auto_security_group": {
                "type": "boolean",
            },
            "security_groups": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "node_configs": {
                "type": "object",
                "additionalProperties": True
            },
            "cluster_configs": {
                "type": "object",
                "additionalProperties": True
            },
            "enable_anti_affinity": {
                "type": "boolean"
            },
            "enable_proxy": {
                "type": "boolean"
            },
            "use_autoconfig": {
                "type": "boolean"
            },
        },
        "additionalProperties": False,
        "required": ["plugin_name", "hadoop_version", "workers_count",
                     "master_flavor_id", "worker_flavor_id"]
    }

    def setup(self):
        utils.init_sahara_context(self)
        self.context["sahara"]["clusters"] = {}

        wait_dict = {}

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            image_id = self.context["tenants"][tenant_id]["sahara"]["image"]

            floating_ip_pool = self.config.get("floating_ip_pool")

            temporary_context = {
                "user": user,
                "tenant": self.context["tenants"][tenant_id],
                "task": self.context["task"],
                "owner_id": self.context["owner_id"]
            }
            scenario = utils.SaharaScenario(context=temporary_context)

            cluster = scenario._launch_cluster(
                plugin_name=self.config["plugin_name"],
                hadoop_version=self.config["hadoop_version"],
                flavor_id=self.config.get("flavor_id"),
                master_flavor_id=self.config["master_flavor_id"],
                worker_flavor_id=self.config["worker_flavor_id"],
                workers_count=self.config["workers_count"],
                image_id=image_id,
                floating_ip_pool=floating_ip_pool,
                volumes_per_node=self.config.get("volumes_per_node"),
                volumes_size=self.config.get("volumes_size", 1),
                auto_security_group=self.config.get("auto_security_group",
                                                    True),
                security_groups=self.config.get("security_groups"),
                node_configs=self.config.get("node_configs"),
                cluster_configs=self.config.get("cluster_configs"),
                enable_anti_affinity=self.config.get("enable_anti_affinity",
                                                     False),
                enable_proxy=self.config.get("enable_proxy", False),
                wait_active=False,
                use_autoconfig=self.config.get("use_autoconfig", True)
            )

            self.context["tenants"][tenant_id]["sahara"]["cluster"] = (
                cluster.id)

            # Need to save the client instance to poll for active status
            wait_dict[cluster] = scenario.clients("sahara")

        bench_utils.wait_for(
            resource=wait_dict,
            update_resource=self.update_clusters_dict,
            is_ready=self.all_clusters_active,
            timeout=CONF.openstack.sahara_cluster_create_timeout,
            check_interval=CONF.openstack.sahara_cluster_check_interval)

    def update_clusters_dict(self, dct):
        new_dct = {}
        for cluster, client in dct.items():
            new_cl = client.clusters.get(cluster.id)
            new_dct[new_cl] = client

        return new_dct

    def all_clusters_active(self, dct):
        for cluster, client in dct.items():
            cluster_status = cluster.status.lower()
            if cluster_status == "error":
                msg = ("Sahara cluster %(name)s has failed to"
                       " %(action)s. Reason: '%(reason)s'"
                       % {"name": cluster.name, "action": "start",
                          "reason": cluster.status_description})
                raise exceptions.ContextSetupFailure(ctx_name=self.get_name(),
                                                     msg=msg)
            elif cluster_status != "active":
                return False
        return True

    def cleanup(self):
        resource_manager.cleanup(names=["sahara.clusters"],
                                 users=self.context.get("users", []),
                                 superclass=utils.SaharaScenario,
                                 task_id=self.get_owner_id())
