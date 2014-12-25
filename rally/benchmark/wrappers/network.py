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

import abc

import netaddr
import six

from rally.common import utils
from rally import consts
from rally import log as logging


LOG = logging.getLogger(__name__)


cidr_incr = utils.RAMInt()


def generate_cidr(start_cidr="1.1.0.0/26"):
    """Generate next CIDR for network or subnet, without IP overlapping.

    This is process and thread safe, because `cidr_incr' points to
    value stored directly in RAM. This guarantees that CIDRs will be
    serial and unique even under hard multiprocessing/threading load.

    :param start_cidr: start CIDR str
    :returns: next available CIDR str
    """
    cidr = str(netaddr.IPNetwork(start_cidr).next(next(cidr_incr)))
    LOG.debug("CIDR generated: %s" % cidr)
    return cidr


@six.add_metaclass(abc.ABCMeta)
class NetworkWrapper(object):
    """Base class for network service implementations.

    We aclually have two network services implementations, with different API:
    NovaNetwork and Neutron. The idea is (at least to try) to use unified
    service, which hides most differences and routines behind the scenes.
    This allows to significantly re-use and simplify code.
    """
    START_CIDR = "1.1.0.0/26"
    SERVICE_IMPL = None

    def __init__(self, clients, config=None):
        self.client = getattr(clients, self.SERVICE_IMPL)()
        self.config = config or {}
        self.start_cidr = self.config.get("start_cidr", self.START_CIDR)

    @abc.abstractmethod
    def create_network(self):
        """Create network."""

    @abc.abstractmethod
    def delete_network(self):
        """Delete network."""

    @abc.abstractmethod
    def list_networks(self):
        """List networks."""


class NovaNetworkWrapper(NetworkWrapper):
    SERVICE_IMPL = consts.Service.NOVA

    def __init__(self, *args):
        super(NovaNetworkWrapper, self).__init__(*args)
        self.skip_cidrs = [n.cidr for n in self.client.networks.list()]

    def _generate_cidr(self):
        cidr = generate_cidr(start_cidr=self.start_cidr)
        while cidr in self.skip_cidrs:
            cidr = generate_cidr(start_cidr=self.start_cidr)
        return cidr

    def create_network(self, tenant_id, **kwargs):
        """Create network.

        :param tenant_id: str, tenant ID
        :param **kwargs: for compatibility, not used here
        :returns: dict, network data
        """
        cidr = self._generate_cidr()
        label = utils.generate_random_name("rally_ctx_net_")
        network = self.client.networks.create(
            tenant_id=tenant_id, cidr=cidr, label=label)
        return {"id": network.id,
                "cidr": network.cidr,
                "name": network.label,
                "status": "ACTIVE",
                "external": False,
                "tenant_id": tenant_id}

    def delete_network(self, network):
        return self.client.networks.delete(network["id"])

    def list_networks(self):
        return self.client.networks.list()


class NeutronWrapper(NetworkWrapper):
    SERVICE_IMPL = consts.Service.NEUTRON
    SUBNET_IP_VERSION = 4

    def _generate_cidr(self):
        # TODO(amaretskiy): Generate CIDRs unique for network, not cluster
        return generate_cidr(start_cidr=self.start_cidr)

    def create_network(self, tenant_id, **kwargs):
        """Create network.

        :param tenant_id: str, tenant ID
        :param **kwargs: extra options
        :returns: dict, network data
        """
        network_args = {
            "network": {
                "tenant_id": tenant_id,
                "name": utils.generate_random_name("rally_ctx_net_")}}
        network = self.client.create_network(network_args)["network"]

        router = None
        if kwargs.get("add_router", False):
            router_args = {
                "router": {
                    "tenant_id": tenant_id,
                    "name": utils.generate_random_name("rally_ctx_router_")}}
            for net in self.list_networks():
                if net.get("router:external"):
                    router_args["router"]["external_gateway_info"] = {
                        "network_id": net["id"],
                        "enable_snat": True}
                    break
            router = self.client.create_router(router_args)["router"]

        subnets = []
        subnets_num = kwargs.get("subnets_num", 0)
        for i in range(subnets_num):
            subnet_args = {
                "subnet": {
                    "tenant_id": tenant_id,
                    "network_id": network["id"],
                    "name": utils.generate_random_name("rally_ctx_subnet_"),
                    "ip_version": self.SUBNET_IP_VERSION,
                    "cidr": self._generate_cidr(),
                    "enable_dhcp": True}}
            subnet = self.client.create_subnet(subnet_args)["subnet"]
            subnets.append(subnet["id"])

            if router:
                self.client.add_interface_router(router["id"],
                                                 {"subnet_id": subnet["id"]})

        return {"id": network["id"],
                "name": network["name"],
                "status": network["status"],
                "subnets": subnets,
                "external": network.get("router:external", False),
                "router_id": router and router["id"] or None,
                "tenant_id": tenant_id}

    def delete_network(self, network):
        net_dhcps = self.client.list_dhcp_agent_hosting_networks(
            network["id"])["agents"]
        for net_dhcp in net_dhcps:
            self.client.remove_network_from_dhcp_agent(net_dhcp["id"],
                                                       network["id"])
        router_id = network["router_id"]
        if router_id:
            self.client.remove_gateway_router(router_id)
            for subnet_id in network["subnets"]:
                self.client.remove_interface_router(router_id,
                                                    {"subnet_id": subnet_id})
            self.client.delete_router(router_id)

        for subnet_id in network["subnets"]:
            self.client.delete_subnet(subnet_id)

        return self.client.delete_network(network["id"])

    def list_networks(self):
        return self.client.list_networks()["networks"]


def wrap(clients, config=None):
    """Returns available network wrapper instance.

    :param clients: rally.osclients.Clients instance
    :param config: task config dict
    :returns: NetworkWrapper subclass instance
    """
    if consts.Service.NEUTRON in clients.services().values():
        return NeutronWrapper(clients, config)
    return NovaNetworkWrapper(clients, config)
