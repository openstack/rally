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

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.magnum import utils as magnum_utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="cluster_templates", order=470)
class ClusterTemplateGenerator(context.Context):
    """Context class for generating temporary cluster model for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image_id": {
                "type": "string"
            },
            "flavor_id": {
                "type": "string"
            },
            "master_flavor_id": {
                "type": "string"
            },
            "external_network_id": {
                "type": "string"
            },
            "fixed_network": {
                "type": "string"
            },
            "fixed_subnet": {
                "type": "string"
            },
            "dns_nameserver": {
                "type": "string"
            },
            "docker_volume_size": {
                "type": "integer"
            },
            "labels": {
                "type": ["string"]
            },
            "coe": {
                "type": "string"
            },
            "http_proxy": {
                "type": "string"
            },
            "https_proxy": {
                "type": "string"
            },
            "no_proxy": {
                "type": "string"
            },
            "network_driver": {
                "type": "string"
            },
            "tls_disabled": {
                "type": "boolean"
            },
            "public": {
                "type": "boolean"
            },
            "registry_enabled": {
                "type": "boolean"
            },
            "volume_driver": {
                "type": "string"
            },
            "server_type": {
                "type": "string"
            },
            "docker_storage_driver": {
                "type": "string"
            },
            "master_lb_enabled": {
                "type": "boolean"
            }
        },
        "required": ["image_id", "external_network_id", "coe"],
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `ClusterTemplate`"))
    def setup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            nova_scenario = nova_utils.NovaScenario({
                "user": user,
                "task": self.context["task"],
                "config": {"api_versions": self.context["config"].get(
                    "api_versions", [])}
            })
            keypair = nova_scenario._create_keypair()

            magnum_scenario = magnum_utils.MagnumScenario({
                "user": user,
                "task": self.context["task"],
                "config": {"api_versions": self.context["config"].get(
                    "api_versions", [])}
            })

            cluster_template = magnum_scenario._create_cluster_template(
                keypair_id=keypair, **self.config)

            ct_uuid = cluster_template.uuid
            self.context["tenants"][tenant_id]["cluster_template"] = ct_uuid

    @logging.log_task_wrapper(LOG.info, _("Exit context: `ClusterTemplate`"))
    def cleanup(self):
        resource_manager.cleanup(
            names=["magnum.cluster_templates", "nova.keypairs"],
            users=self.context.get("users", []))
