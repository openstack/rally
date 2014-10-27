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

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import manager as resource_manager
from rally.benchmark.scenarios.nova import utils as nova_utils
from rally.benchmark import types as types
from rally.i18n import _
from rally import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class ServerGenerator(base.Context):
    """Context class for adding temporary servers for benchmarks.

        Servers are added for each tenant.
    """
    __ctx_name__ = "servers"
    __ctx_order__ = 412
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
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
            },
        },
        'required': ['image', 'flavor'],
        "additionalProperties": False
    }

    def __init__(self, context):
        super(ServerGenerator, self).__init__(context)
        self.config.setdefault("servers_per_tenant", 5)
        self.context.setdefault("servers", [])

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Servers`"))
    def setup(self):
        image = self.config["image"]
        flavor = self.config["flavor"]
        servers_per_tenant = self.config["servers_per_tenant"]

        current_tenants = []
        for user in self.context["users"]:
            if user["tenant_id"] not in current_tenants:
                LOG.debug("Booting servers for user tenant %s "
                          % (user["tenant_id"]))
                current_tenants.append(user["tenant_id"])
                clients = osclients.Clients(user["endpoint"])
                nova_scenario = nova_utils.NovaScenario(clients=clients)
                image_id = types.ImageResourceType.transform(
                    clients=clients, resource_config=image)
                flavor_id = types.FlavorResourceType.transform(
                    clients=clients, resource_config=flavor)

                server_name_prefix = nova_scenario._generate_random_name()

                LOG.debug("Calling _boot_servers with server_name_prefix=%s "
                          "image_id=%s flavor_id=%s servers_per_tenant=%s"
                          % (server_name_prefix, image_id,
                             flavor_id, flavor_id))

                current_servers = []

                servers = nova_scenario._boot_servers(
                    server_name_prefix, image_id,
                    flavor_id,
                    servers_per_tenant)

                for server in servers:
                    current_servers.append(server.id)

                LOG.debug("Adding booted servers %s to context"
                          % current_servers)

                self.context["servers"].append(
                    {"server_ids": current_servers,
                     "endpoint": user["endpoint"],
                     "tenant_id": user["tenant_id"]}
                )

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Servers`"))
    def cleanup(self):
        resource_manager.cleanup(names=["nova.servers"],
                                 users=self.context.get("users", []))
