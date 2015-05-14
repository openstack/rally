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

from rally.benchmark import utils as bench_utils
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils
from rally import consts
from rally import exceptions

from neutronclient.common import exceptions as neutron_exceptions
from novaclient import exceptions as nova_exceptions


LOG = logging.getLogger(__name__)


cidr_incr = utils.RAMInt()


def generate_cidr(start_cidr="10.2.0.0/24"):
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


class NetworkWrapperException(exceptions.RallyException):
    msg_fmt = _("%(message)s")


@six.add_metaclass(abc.ABCMeta)
class NetworkWrapper(object):
    """Base class for network service implementations.

    We actually have two network services implementations, with different API:
    NovaNetwork and Neutron. The idea is (at least to try) to use unified
    service, which hides most differences and routines behind the scenes.
    This allows to significantly re-use and simplify code.
    """
    START_CIDR = "10.2.0.0/24"
    SERVICE_IMPL = None

    def __init__(self, clients, config=None):
        if hasattr(clients, self.SERVICE_IMPL):
            self.client = getattr(clients, self.SERVICE_IMPL)()
        else:
            self.client = clients(self.SERVICE_IMPL)
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

    @abc.abstractmethod
    def create_floating_ip(self):
        """Create floating IP."""

    @abc.abstractmethod
    def delete_floating_ip(self):
        """Delete floating IP."""

    @abc.abstractmethod
    def supports_security_group(self):
        """Checks whether security group is supported."""


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
        label = utils.generate_random_name("rally_net_")
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

    def create_floating_ip(self, ext_network=None, **kwargs):
        """Allocate a floating ip from the given nova-network pool

        :param ext_network: name or external network, str
        :param **kwargs: for compatibility, not used here
        :returns: floating IP dict
        """
        if not ext_network:
            try:
                ext_network = self.client.floating_ip_pools.list()[0].name
            except IndexError:
                raise NetworkWrapperException("No floating IP pools found")
        fip = self.client.floating_ips.create(ext_network)
        return {"id": fip.id, "ip": fip.ip}

    def _get_floating_ip(self, fip_id, do_raise=False):
        try:
            fip = self.client.floating_ips.get(fip_id)
        except nova_exceptions.NotFound:
            if not do_raise:
                return None
            raise exceptions.GetResourceNotFound(
                resource="Floating IP %s" % fip_id)
        return fip.id

    def delete_floating_ip(self, fip_id, wait=False):
        """Delete floating IP.

        :param fip_id: int floating IP id
        :param wait: if True then wait to return until floating ip is deleted
        """
        self.client.floating_ips.delete(fip_id)
        if not wait:
            return
        bench_utils.wait_for_delete(
            fip_id,
            update_resource=lambda i: self._get_floating_ip(i, do_raise=True))

    def supports_security_group(self):
        """Check whether security group is supported

        :return: result tuple. Always (True, "") for nova-network.
        :rtype: (bool, string)
        """
        return True, ""


class NeutronWrapper(NetworkWrapper):
    SERVICE_IMPL = consts.Service.NEUTRON
    SUBNET_IP_VERSION = 4

    @property
    def external_networks(self):
        return self.client.list_networks(**{
            "router:external": True})["networks"]

    def get_network(self, net_id=None, name=None):
        net = None
        try:
            if net_id:
                net = self.client.show_network(net_id)["network"]
            else:
                for net in self.client.list_networks(name=name)["networks"]:
                    break
            return {"id": net["id"],
                    "name": net["name"],
                    "tenant_id": net["tenant_id"],
                    "status": net["status"],
                    "external": net["router:external"],
                    "subnets": net["subnets"],
                    "router_id": None}
        except (TypeError, neutron_exceptions.NeutronClientException):
            raise NetworkWrapperException(
                "Network not found: %s" % (name or net_id))

    def create_router(self, external=False, **kwargs):
        """Create neutron router.

        :param external: bool, whether to set setup external_gateway_info
        :param **kwargs: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        if "name" not in kwargs:
            kwargs["name"] = utils.generate_random_name("rally_router_")

        if external and "external_gateway_info" not in kwargs:
            for net in self.external_networks:
                kwargs["external_gateway_info"] = {
                    "network_id": net["id"], "enable_snat": True}
        return self.client.create_router({"router": kwargs})["router"]

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
                "name": utils.generate_random_name("rally_net_")
            }
        }
        network = self.client.create_network(network_args)["network"]

        router = None
        if kwargs.get("add_router", False):
            router = self.create_router(external=True, tenant_id=tenant_id)

        subnets = []
        subnets_num = kwargs.get("subnets_num", 0)
        for i in range(subnets_num):
            subnet_args = {
                "subnet": {
                    "tenant_id": tenant_id,
                    "network_id": network["id"],
                    "name": utils.generate_random_name("rally_subnet_"),
                    "ip_version": self.SUBNET_IP_VERSION,
                    "cidr": self._generate_cidr(),
                    "enable_dhcp": True,
                    "dns_nameservers": kwargs.get("dns_nameservers",
                                                  ["8.8.8.8", "8.8.4.4"])
                }
            }
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

        for port in self.client.list_ports(network_id=network["id"])["ports"]:
            self.client.delete_port(port["id"])

        for subnet_id in network["subnets"]:
            self._delete_subnet(subnet_id)

        return self.client.delete_network(network["id"])

    def _delete_subnet(self, subnet_id):
        self.client.delete_subnet(subnet_id)

    def list_networks(self):
        return self.client.list_networks()["networks"]

    def create_port(self, network_id, **kwargs):
        """Create neutron port.

        :param network_id: neutron network id
        :param **kwargs: POST /v2.0/ports request options
        :returns: neutron port dict
        """
        kwargs["network_id"] = network_id
        if "name" not in kwargs:
            kwargs["name"] = utils.generate_random_name("rally_port_")
        return self.client.create_port({"port": kwargs})["port"]

    def create_floating_ip(self, ext_network=None, int_network=None,
                           tenant_id=None, port_id=None, **kwargs):
        """Create Neutron floating IP.

        :param ext_network: floating network name or dict
        :param int_network: fixed network name or dict
        :param tenant_id str tenant id
        :param port_id: str port id
        :param **kwargs: for compatibility, not used here
        :returns: floating IP dict
        """
        if not tenant_id:
            raise ValueError("Missed tenant_id")

        net_id = None
        if type(ext_network) is dict:
            net_id = ext_network["id"]
        elif ext_network:
            ext_net = self.get_network(name=ext_network)
            if not ext_net["external"]:
                raise NetworkWrapperException("Network is not external: %s"
                                              % ext_network)
            net_id = ext_net["id"]
        else:
            ext_networks = self.external_networks
            if not ext_networks:
                raise NetworkWrapperException(
                    "Failed to allocate floating IP: "
                    "no external networks found")
            net_id = ext_networks[0]["id"]

        if not port_id:
            if type(int_network) is dict:
                port_id = self.create_port(int_network["id"])["id"]
            elif int_network:
                int_net = self.get_network(name=int_network)
                if int_net["external"]:
                    raise NetworkWrapperException("Network is external: %s"
                                                  % int_network)
                port_id = self.create_port(int_net["id"])["id"]
        kwargs = {"floatingip": {"floating_network_id": net_id},
                  "tenant_id": tenant_id,
                  "port_id": port_id}

        fip = self.client.create_floatingip(kwargs)["floatingip"]
        return {"id": fip["id"], "ip": fip["floating_ip_address"]}

    def delete_floating_ip(self, fip_id, **kwargs):
        """Delete floating IP.

        :param fip_id: int floating IP id
        :param **kwargs: for compatibility, not used here
        """
        self.client.delete_floatingip(fip_id)

    def supports_security_group(self):
        """Check whether security group is supported

        :return: result tuple
        :rtype: (bool, string)
        """
        extensions = self.client.list_extensions().get("extensions", [])
        use_sg = any(ext.get("alias") == "security-group"
                     for ext in extensions)
        if use_sg:
            return True, ""

        return False, _("neutron driver does not support security groups")


def wrap(clients, config=None):
    """Returns available network wrapper instance.

    :param clients: rally.osclients.Clients instance
    :param config: task config dict
    :returns: NetworkWrapper subclass instance
    """
    if hasattr(clients, "services"):
        services = clients.services()
    else:
        services = clients("services")

    if consts.Service.NEUTRON in services.values():
        return NeutronWrapper(clients, config)
    return NovaNetworkWrapper(clients, config)
