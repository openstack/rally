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
from rally import osclients
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.ec2 import utils as ec2_utils
from rally.plugins.openstack import types
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="ec2_servers", order=460)
class EC2ServerGenerator(context.Context):
    """Context class for adding temporary servers for benchmarks.

    Servers are added for each tenant.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            },
            "flavor": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            },
            "servers_per_tenant": {
                "type": "integer",
                "minimum": 1
            }
        },
        "required": ["image", "flavor", "servers_per_tenant"],
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `EC2 Servers`"))
    def setup(self):
        image = self.config["image"]
        flavor = self.config["flavor"]

        clients = osclients.Clients(self.context["users"][0]["credential"])
        image_id = types.EC2Image.transform(clients=clients,
                                            resource_config=image)

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            LOG.debug("Booting servers for tenant %s "
                      % (user["tenant_id"]))
            user_clients = osclients.Clients(user["credential"])
            ec2_scenario = ec2_utils.EC2Scenario(clients=user_clients)

            LOG.debug(
                "Calling _boot_servers with "
                "image_id={image_id} flavor_name={flavor_name} "
                "servers_per_tenant={servers_per_tenant}".format(
                    image_id=image_id, flavor_name=flavor["name"],
                    servers_per_tenant=self.config["servers_per_tenant"]))

            servers = ec2_scenario._boot_servers(
                image_id, flavor["name"], self.config["servers_per_tenant"])

            current_servers = [server.id for server in servers]

            self.context["tenants"][tenant_id]["ec2_servers"] = current_servers

    @logging.log_task_wrapper(LOG.info, _("Exit context: `EC2 Servers`"))
    def cleanup(self):
        resource_manager.cleanup(names=["ec2.servers"],
                                 users=self.context.get("users", []))
