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

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils
from rally import consts
from rally import exceptions
from rally.task import utils as task_utils

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

    def __init__(self, clients, owner, config=None):
        """Returns available network wrapper instance.

        :param clients: rally.osclients.Clients instance
        :param owner: The object that owns resources created by this
                      wrapper instance. It will be used to generate
                      random names, so must implement
                      rally.common.utils.RandomNameGeneratorMixin
        :param config: The configuration of the network
                       wrapper. Currently only one config option is
                       recognized, 'start_cidr', and only for Nova
                       network.
        :returns: NetworkWrapper subclass instance
        """
        if hasattr(clients, self.SERVICE_IMPL):
            self.client = getattr(clients, self.SERVICE_IMPL)()
        else:
            self.client = clients(self.SERVICE_IMPL)
        self.config = config or {}
        self.owner = owner
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
    def supports_extension(self):
        """Checks whether a network extension is supported."""


class NovaNetworkWrapper(NetworkWrapper):
    SERVICE_IMPL = consts.Service.NOVA

    def __init__(self, *args, **kwargs):
        super(NovaNetworkWrapper, self).__init__(*args, **kwargs)
        self.skip_cidrs = [n.cidr for n in self.client.networks.list()]

    def _generate_cidr(self):
        cidr = generate_cidr(start_cidr=self.start_cidr)
        while cidr in self.skip_cidrs:
            cidr = generate_cidr(start_cidr=self.start_cidr)
        return cidr

    def _marshal_network_object(self, net_obj):
        """Convert a Network object to a dict.

        This helps keep return values from the NovaNetworkWrapper
        compatible with those from NeutronWrapper.

        :param net_obj: The Network object to convert to a dict
        """
        return {"id": net_obj.id,
                "cidr": net_obj.cidr,
                "name": net_obj.label,
                "status": "ACTIVE",
                "external": False,
                "tenant_id": net_obj.project_id}

    def create_network(self, tenant_id, **kwargs):
        """Create network.

        :param tenant_id: str, tenant ID
        :param **kwargs: Additional keyword arguments. Only
                         ``network_create_args`` is honored; other
                         arguments are accepted for compatibility, but
                         are not used here. ``network_create_args``
                         can be used to provide additional arbitrary
                         network creation arguments.
        :returns: dict, network data
        """
        cidr = self._generate_cidr()
        label = self.owner.generate_random_name()
        network_create_args = kwargs.get("network_create_args", {})
        network = self.client.networks.create(
            project_id=tenant_id, cidr=cidr, label=label,
            **network_create_args)
        return self._marshal_network_object(network)

    def delete_network(self, network):
        self.client.networks.disassociate(network["id"],
                                          disassociate_host=False,
                                          disassociate_project=True)
        return self.client.networks.delete(network["id"])

    def list_networks(self):
        return [self._marshal_network_object(n)
                for n in self.client.networks.list()]

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
        task_utils.wait_for_status(
            fip_id,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=lambda i: self._get_floating_ip(i, do_raise=True))

    def supports_extension(self, extension):
        """Check whether a Nova-network extension is supported

        :param extension: str Nova network extension
        :returns: result tuple. Always (True, "") for secgroups in nova-network
        :rtype: (bool, string)
        """
        # TODO(rkiran): Add other extensions whenever necessary
        if extension == "security-group":
            return True, ""

        return False, _("Nova driver does not support %s") % (extension)


class NeutronWrapper(NetworkWrapper):
    SERVICE_IMPL = consts.Service.NEUTRON
    SUBNET_IP_VERSION = 4
    LB_METHOD = "ROUND_ROBIN"
    LB_PROTOCOL = "HTTP"

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
        kwargs["name"] = self.owner.generate_random_name()

        if external and "external_gateway_info" not in kwargs:
            for net in self.external_networks:
                kwargs["external_gateway_info"] = {
                    "network_id": net["id"], "enable_snat": True}
        return self.client.create_router({"router": kwargs})["router"]

    def create_v1_pool(self, tenant_id, subnet_id, **kwargs):
        """Create LB Pool (v1).

        :param tenant_id: str, pool tenant id
        :param subnet_id: str, neutron subnet-id
        :param **kwargs: extra options
        :returns: neutron lb-pool dict
        """
        pool_args = {
            "pool": {
                "tenant_id": tenant_id,
                "name": self.owner.generate_random_name(),
                "subnet_id": subnet_id,
                "lb_method": kwargs.get("lb_method", self.LB_METHOD),
                "protocol": kwargs.get("protocol", self.LB_PROTOCOL)
            }
        }
        return self.client.create_pool(pool_args)

    def _generate_cidr(self):
        # TODO(amaretskiy): Generate CIDRs unique for network, not cluster
        return generate_cidr(start_cidr=self.start_cidr)

    def create_network(self, tenant_id, **kwargs):
        """Create network.

        The following keyword arguments are accepted:

        * add_router: Create an external router and add an interface to each
                      subnet created. Default: False
        * subnets_num: Number of subnets to create per network. Default: 0
        * dns_nameservers: Nameservers for each subnet. Default:
                           8.8.8.8, 8.8.4.4
        * network_create_args: Additional network creation arguments.

        :param tenant_id: str, tenant ID
        :param kwargs: Additional options, left open-ended for compatbilitiy.
                       See above for recognized keyword args.
        :returns: dict, network data
        """
        network_args = {"network": kwargs.get("network_create_args", {})}
        network_args["network"].update({
            "tenant_id": tenant_id,
            "name": self.owner.generate_random_name()})
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
                    "name": self.owner.generate_random_name(),
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

    def delete_v1_pool(self, pool_id):
        """Delete LB Pool (v1)

        :param pool_id: str, Lb-Pool-id
        """
        self.client.delete_pool(pool_id)

    def delete_network(self, network):
        if self.supports_extension("dhcp_agent_scheduler")[0]:
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
        kwargs["name"] = self.owner.generate_random_name()
        return self.client.create_port({"port": kwargs})["port"]

    def create_floating_ip(self, ext_network=None,
                           tenant_id=None, port_id=None, **kwargs):
        """Create Neutron floating IP.

        :param ext_network: floating network name or dict
        :param tenant_id: str tenant id
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

        kwargs = {"floatingip": {"floating_network_id": net_id},
                  "tenant_id": tenant_id}
        if port_id:
            kwargs["port_id"] = port_id

        fip = self.client.create_floatingip(kwargs)["floatingip"]
        return {"id": fip["id"], "ip": fip["floating_ip_address"]}

    def delete_floating_ip(self, fip_id, **kwargs):
        """Delete floating IP.

        :param fip_id: int floating IP id
        :param **kwargs: for compatibility, not used here
        """
        self.client.delete_floatingip(fip_id)

    def supports_extension(self, extension):
        """Check whether a neutron extension is supported

        :param extension: str, neutron extension
        :returns: result tuple
        :rtype: (bool, string)
        """
        extensions = self.client.list_extensions().get("extensions", [])
        if any(ext.get("alias") == extension for ext in extensions):
            return True, ""

        return False, _("Neutron driver does not support %s") % (extension)


def wrap(clients, owner, config=None):
    """Returns available network wrapper instance.

    :param clients: rally.osclients.Clients instance
    :param owner: The object that owns resources created by this
                  wrapper instance. It will be used to generate random
                  names, so must implement
                  rally.common.utils.RandomNameGeneratorMixin
    :param config: The configuration of the network wrapper. Currently
                   only one config option is recognized, 'start_cidr',
                   and only for Nova network.
    :returns: NetworkWrapper subclass instance
    """
    if hasattr(clients, "services"):
        services = clients.services()
    else:
        services = clients("services")

    if consts.Service.NEUTRON in services.values():
        return NeutronWrapper(clients, owner, config=config)
    return NovaNetworkWrapper(clients, owner, config=config)
