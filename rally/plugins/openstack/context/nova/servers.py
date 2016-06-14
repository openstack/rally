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
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack import types
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="servers", order=430)
class ServerGenerator(context.Context):
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
            },
            "auto_assign_nic": {
                "type": "boolean",
            },
            "nics": {
                "type": "array",
                "properties": {
                    "net-id": {
                        "type": "string"
                    }
                }
            }
        },
        "required": ["image", "flavor"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "servers_per_tenant": 5,
        "auto_assign_nic": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Servers`"))
    def setup(self):
        image = self.config["image"]
        flavor = self.config["flavor"]
        auto_nic = self.config["auto_assign_nic"]
        servers_per_tenant = self.config["servers_per_tenant"]
        kwargs = {"nics": self.config.get("nics", [])}

        clients = osclients.Clients(self.context["users"][0]["credential"])
        image_id = types.GlanceImage.transform(clients=clients,
                                               resource_config=image)
        flavor_id = types.Flavor.transform(clients=clients,
                                           resource_config=flavor)

        for iter_, (user, tenant_id) in enumerate(rutils.iterate_per_tenants(
                self.context["users"])):
            LOG.debug("Booting servers for user tenant %s "
                      % (user["tenant_id"]))
            tmp_context = {"user": user,
                           "tenant": self.context["tenants"][tenant_id],
                           "task": self.context["task"],
                           "iteration": iter_}
            nova_scenario = nova_utils.NovaScenario(tmp_context)

            LOG.debug("Calling _boot_servers with image_id=%(image_id)s "
                      "flavor_id=%(flavor_id)s "
                      "servers_per_tenant=%(servers_per_tenant)s"
                      % {"image_id": image_id,
                         "flavor_id": flavor_id,
                         "servers_per_tenant": servers_per_tenant})

            servers = nova_scenario._boot_servers(image_id, flavor_id,
                                                  requests=servers_per_tenant,
                                                  auto_assign_nic=auto_nic,
                                                  **kwargs)

            current_servers = [server.id for server in servers]

            LOG.debug("Adding booted servers %s to context"
                      % current_servers)

            self.context["tenants"][tenant_id][
                "servers"] = current_servers

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Servers`"))
    def cleanup(self):
        resource_manager.cleanup(names=["nova.servers"],
                                 users=self.context.get("users", []))
