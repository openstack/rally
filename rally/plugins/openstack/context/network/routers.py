# Copyright 2017: Orange
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

from rally.common import utils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.task import context


@validation.add("required_platform", platform="openstack", admin=True,
                users=True)
@context.configure(name="router", platform="openstack", order=351)
class Router(context.Context):
    """Create networking resources.

    This creates router for all tenants.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "routers_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "admin_state_up ": {
                "description": "A human-readable description for the resource",
                "type": "boolean",
            },
            "external_gateway_info": {
                "description": "The external gateway information .",
                "type": "object",
                "properties": {
                    "network_id": {"type": "string"},
                    "enable_snat": {"type": "boolean"}
                },
                "additionalProperties": False
            },
            "network_id": {
                "description": "Network ID",
                "type": "string"
            },
            "external_fixed_ips": {
                "description": "Ip(s) of the external gateway interface.",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ip_address": {"type": "string"},
                        "subnet_id": {"type": "string"}
                    },
                    "additionalProperties": False,
                }
            },
            "distributed": {
                "description": "Distributed router. Require dvr extension.",
                "type": "boolean"
            },
            "ha": {
                "description": "Highly-available router. Require l3-ha.",
                "type": "boolean"
            },
            "availability_zone_hints": {
                "description": "Require router_availability_zone extension.",
                "type": "boolean"
            }
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "routers_per_tenant": 1,
    }

    def setup(self):
        kwargs = {}
        parameters = ("admin_state_up", "external_gateway_info", "network_id",
                      "external_fixed_ips", "distributed", "ha",
                      "availability_zone_hints")
        for parameter in parameters:
            if parameter in self.config:
                kwargs[parameter] = self.config[parameter]
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            self.context["tenants"][tenant_id]["routers"] = []
            scenario = neutron_utils.NeutronScenario(
                context={"user": user, "task": self.context["task"],
                         "owner_id": self.context["owner_id"]}
            )
            for i in range(self.config["routers_per_tenant"]):
                router = scenario._create_router(kwargs)
                self.context["tenants"][tenant_id]["routers"].append(router)

    def cleanup(self):
        resource_manager.cleanup(
            names=["neutron.router"],
            users=self.context.get("users", []),
            superclass=neutron_utils.NeutronScenario,
            task_id=self.get_owner_id())
