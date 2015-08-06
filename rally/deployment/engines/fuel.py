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

from rally.common.i18n import _
from rally.common import objects
from rally import consts
from rally.deployment import engine
from rally.deployment.fuel import fuelclient
from rally import exceptions


FILTER_SCHEMA = {
    "type": "string",
    "pattern": "^(ram|cpus|storage|mac)(==|<=?|>=?|!=)(.+)$",
}

NODE_SCHEMA = {
    "type": "object",
    "required": ["amount"],
    "properties": {
        "amount": {"type": "integer"},
        "filters": {
            "type": "array",
            "uniqueItems": True,
            "items": FILTER_SCHEMA,
        },
    },
    "additionalProperties": False
}


IPV4_PATTERN = "(\d+\.){3}\d+"
IPV4_ADDRESS_PATTERN = "^%s$" % IPV4_PATTERN
IPV4_CIDR_PATTERN = "^%s\/\d+$" % IPV4_PATTERN

IP_RANGE_SCHEMA = {
    "type": "array",
    "maxItems": 2,
    "minItems": 2,
    "items": {
        "type": "string",
        "pattern": IPV4_ADDRESS_PATTERN,
    }
}

NETWORK_SCHEMA = {
    "type": "object",
    "properties": {
        "cidr": {"type": "string", "pattern": IPV4_CIDR_PATTERN},
        "gateway": {"type": "string", "pattern": IPV4_ADDRESS_PATTERN},
        "ip_ranges": {"type": "array", "items": IP_RANGE_SCHEMA},
        "vlan_start": {"type": "integer"},
    }
}

NETWORKS_SCHEMA = {
    "type": "object",
    "properties": {
        "public": NETWORK_SCHEMA,
        "floating": NETWORK_SCHEMA,
        "management": NETWORK_SCHEMA,
        "storage": NETWORK_SCHEMA,
    },
}


@engine.configure(name="FuelEngine")
class FuelEngine(engine.Engine):
    """Deploy with FuelWeb.

    Sample configuration:

        {
            "type": "FuelEngine",
            "deploy_name": "Rally multinode 01",
            "release": "Havana on CentOS 6.4",
            "api_url": "http://10.20.0.2:8000/api/v1/",
            "mode": "multinode",
            "nodes": {
               "controller": {"amount": 1, "filters": ["storage>80G"]},
               "compute": {"amount": 1, "filters": ["storage>80G"]}
            },
            "net_provider": "nova_network",
            "dns_nameservers": ["172.18.208.44", "8.8.8.8"],
            "networks": {

                "public": {
                    "cidr": "10.3.3.0/24",
                    "gateway": "10.3.3.1",
                    "ip_ranges": [["10.3.3.5", "10.3.3.254"]],
                    "vlan_start": 14
                },

                "floating": {
                    "cidr": "10.3.4.0/24",
                    "ip_ranges": [["10.3.4.5", "10.3.4.254"]],
                    "vlan_start": 14
                }
            }
        }
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["deploy_name", "api_url", "mode", "networks",
                     "nodes", "release", "net_provider"],
        "properties": {
            "release": {"type": "string"},
            "deploy_name": {"type": "string"},
            "api_url": {"type": "string"},
            "mode": {"type": "string"},
            "net_provider": {"type": "string"},
            "networks": NETWORKS_SCHEMA,
            "nodes": {
                "type": "object",
                "required": ["controller"],
                "properties": {
                    "controller": NODE_SCHEMA,
                    "compute": NODE_SCHEMA,
                    "cinder": NODE_SCHEMA,
                    "cinder+compute": NODE_SCHEMA,
                },
            },
        },
    }

    def validate(self):
        super(FuelEngine, self).validate()
        if "compute" not in self.config["nodes"]:
            if "cinder+compute" not in self.config["nodes"]:
                raise exceptions.ValidationError(
                    _("At least one compute is required."))

    def _get_nodes(self, key):
        if key not in self.config["nodes"]:
            return []
        amount = self.config["nodes"][key]["amount"]
        filters = self.config["nodes"][key]["filters"]
        nodes = []
        for i in range(amount):
            node = self.nodes.pop(filters)
            if node is None:
                raise exceptions.NoNodesFound(filters=filters)
            nodes.append(node)
        return nodes

    def _get_release_id(self):
        releases = self.client.get_releases()
        for release in releases:
            if release["name"] == self.config["release"]:
                return release["id"]
        raise exceptions.UnknownRelease(release=self.config["release"])

    def deploy(self):
        self.client = fuelclient.FuelClient(self.config["api_url"])

        self.nodes = self.client.get_nodes()

        controllers = self._get_nodes("controller")
        computes = self._get_nodes("compute")
        cinders = self._get_nodes("cinder")
        computes_cinders = self._get_nodes("cinder+compute")

        cluster = fuelclient.FuelCluster(
            self.client,
            name=self.config["deploy_name"],
            release=self._get_release_id(),
            mode=self.config["mode"],
            net_provider=self.config["net_provider"],
            net_segment_type=self.config.get("net_segment_type", "gre"),
        )

        cluster.set_nodes(controllers, ["controller"])
        cluster.set_nodes(computes, ["compute"])
        cluster.set_nodes(cinders, ["cinder"])
        cluster.set_nodes(computes_cinders, ["compute", "cinder"])

        cluster.configure_network(self.config["networks"])
        cluster.deploy()

        self.deployment.add_resource("FuelEngine",
                                     type="cloud",
                                     info={"id": cluster.cluster["id"]})

        ip = cluster.get_endpoint_ip()
        attrs = cluster.get_attributes()["editable"]["access"]

        admin_endpoint = objects.Endpoint(
            "http://%s:5000/v2.0/" % ip,
            attrs["user"]["value"],
            attrs["password"]["value"],
            attrs["tenant"]["value"],
            consts.EndpointPermission.ADMIN)
        return {"admin": admin_endpoint}

    def cleanup(self):
        resources = self.deployment.get_resources(provider_name="FuelEngine",
                                                  type="cloud")
        self.client = fuelclient.FuelClient(self.config["api_url"])
        for res in resources:
            self.client.delete_cluster(res["info"]["id"])
            objects.Deployment.delete_resource(res["id"])
