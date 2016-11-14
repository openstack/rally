# Copyright 2014: Intel Inc.
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

import random

from rally.common.i18n import _
from rally.common import logging
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.wrappers import network as network_wrapper
from rally.task import atomic

LOG = logging.getLogger(__name__)


class NeutronScenario(scenario.OpenStackScenario):
    """Base class for Neutron scenarios with basic atomic actions."""

    SUBNET_IP_VERSION = 4
    # TODO(rkiran): modify in case LBaaS-v2 requires
    LB_METHOD = "ROUND_ROBIN"
    LB_PROTOCOL = "HTTP"
    LB_PROTOCOL_PORT = 80
    HM_TYPE = "PING"
    HM_MAX_RETRIES = 3
    HM_DELAY = 20
    HM_TIMEOUT = 10

    def _get_network_id(self, network, **kwargs):
        """Get Neutron network ID for the network name.

        param network: str, network name/id
        param kwargs: dict, network options
        returns: str, Neutron network-id
        """
        networks = self._list_networks(atomic_action=False)
        for net in networks:
            if (net["name"] == network) or (net["id"] == network):
                return net["id"]
        msg = (_("Network %s not found.") % network)
        raise exceptions.NotFoundException(message=msg)

    @atomic.action_timer("neutron.create_network")
    def _create_network(self, network_create_args):
        """Create neutron network.

        :param network_create_args: dict, POST /v2.0/networks request options
        :returns: neutron network dict
        """
        network_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_network(
            {"network": network_create_args})

    @atomic.optional_action_timer("neutron.list_networks")
    def _list_networks(self, **kwargs):
        """Return user networks list.

        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        :param kwargs: network list options
        """
        return self.clients("neutron").list_networks(**kwargs)["networks"]

    @atomic.action_timer("neutron.list_agents")
    def _list_agents(self, **kwargs):
        """Fetches agents.

        :param kwargs: neutron agent list options
        :returns: user agents list
        """
        return self.clients("neutron").list_agents(**kwargs)["agents"]

    @atomic.action_timer("neutron.update_network")
    def _update_network(self, network, network_update_args):
        """Update the network.

        This atomic function updates the network with network_update_args.

        :param network: Network object
        :param network_update_args: dict, POST /v2.0/networks update options
        :returns: updated neutron network dict
        """
        network_update_args["name"] = self.generate_random_name()
        body = {"network": network_update_args}
        return self.clients("neutron").update_network(
            network["network"]["id"], body)

    @atomic.action_timer("neutron.delete_network")
    def _delete_network(self, network):
        """Delete neutron network.

        :param network: Network object
        """
        self.clients("neutron").delete_network(network["id"])

    @atomic.action_timer("neutron.create_subnet")
    def _create_subnet(self, network, subnet_create_args, start_cidr=None):
        """Create neutron subnet.

        :param network: neutron network dict
        :param subnet_create_args: POST /v2.0/subnets request options
        :returns: neutron subnet dict
        """
        network_id = network["network"]["id"]

        if not subnet_create_args.get("cidr"):
            start_cidr = start_cidr or "10.2.0.0/24"
            subnet_create_args["cidr"] = (
                network_wrapper.generate_cidr(start_cidr=start_cidr))

        subnet_create_args["network_id"] = network_id
        subnet_create_args["name"] = self.generate_random_name()
        subnet_create_args.setdefault("ip_version", self.SUBNET_IP_VERSION)

        return self.clients("neutron").create_subnet(
            {"subnet": subnet_create_args})

    @atomic.action_timer("neutron.list_subnets")
    def _list_subnets(self):
        """Returns user subnetworks list."""
        return self.clients("neutron").list_subnets()["subnets"]

    @atomic.action_timer("neutron.update_subnet")
    def _update_subnet(self, subnet, subnet_update_args):
        """Update the neutron subnet.

        This atomic function updates the subnet with subnet_update_args.

        :param subnet: Subnet object
        :param subnet_update_args: dict, PUT /v2.0/subnets update options
        :returns: updated neutron subnet dict
        """
        subnet_update_args["name"] = self.generate_random_name()
        body = {"subnet": subnet_update_args}
        return self.clients("neutron").update_subnet(
            subnet["subnet"]["id"], body)

    @atomic.action_timer("neutron.delete_subnet")
    def _delete_subnet(self, subnet):
        """Delete neutron subnet

        :param subnet: Subnet object
        """
        self.clients("neutron").delete_subnet(subnet["subnet"]["id"])

    @atomic.action_timer("neutron.create_router")
    def _create_router(self, router_create_args, external_gw=False):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        router_create_args["name"] = self.generate_random_name()

        if external_gw:
            for network in self._list_networks():
                if network.get("router:external"):
                    external_network = network
                    gw_info = {"network_id": external_network["id"],
                               "enable_snat": True}
                    router_create_args.setdefault("external_gateway_info",
                                                  gw_info)

        return self.clients("neutron").create_router(
            {"router": router_create_args})

    @atomic.action_timer("neutron.list_routers")
    def _list_routers(self):
        """Returns user routers list."""
        return self.clients("neutron").list_routers()["routers"]

    @atomic.action_timer("neutron.delete_router")
    def _delete_router(self, router):
        """Delete neutron router

        :param router: Router object
        """
        self.clients("neutron").delete_router(router["router"]["id"])

    @atomic.action_timer("neutron.update_router")
    def _update_router(self, router, router_update_args):
        """Update the neutron router.

        This atomic function updates the router with router_update_args.

        :param router: dict, neutron router
        :param router_update_args: dict, PUT /v2.0/routers update options
        :returns: updated neutron router dict
        """
        router_update_args["name"] = self.generate_random_name()
        body = {"router": router_update_args}
        return self.clients("neutron").update_router(
            router["router"]["id"], body)

    @atomic.action_timer("neutron.create_port")
    def _create_port(self, network, port_create_args):
        """Create neutron port.

        :param network: neutron network dict
        :param port_create_args: POST /v2.0/ports request options
        :returns: neutron port dict
        """
        port_create_args["network_id"] = network["network"]["id"]
        port_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_port({"port": port_create_args})

    @atomic.action_timer("neutron.list_ports")
    def _list_ports(self):
        """Return user ports list."""
        return self.clients("neutron").list_ports()["ports"]

    @atomic.action_timer("neutron.update_port")
    def _update_port(self, port, port_update_args):
        """Update the neutron port.

        This atomic function updates port with port_update_args.

        :param port: dict, neutron port
        :param port_update_args: dict, PUT /v2.0/ports update options
        :returns: updated neutron port dict
        """
        port_update_args["name"] = self.generate_random_name()
        body = {"port": port_update_args}
        return self.clients("neutron").update_port(port["port"]["id"], body)

    @atomic.action_timer("neutron.delete_port")
    def _delete_port(self, port):
        """Delete neutron port.

        :param port: Port object
        """
        self.clients("neutron").delete_port(port["port"]["id"])

    @logging.log_deprecated_args(_("network_create_args is deprecated; "
                                   "use the network context instead"),
                                 "0.1.0", "network_create_args")
    def _get_or_create_network(self, network_create_args=None):
        """Get a network from context, or create a new one.

        This lets users either create networks with the 'network'
        context, provide existing networks with the 'existing_network'
        context, or let the scenario create a default network for
        them. Running this without one of the network contexts is
        deprecated.

        :param network_create_args: Deprecated way to provide network
                                    creation args; use the network
                                    context instead.
        :returns: Network dict
        """
        if "networks" in self.context["tenant"]:
            return {"network":
                    random.choice(self.context["tenant"]["networks"])}
        else:
            LOG.warning(_("Running this scenario without either the 'network' "
                          "or 'existing_network' context is deprecated"))
            return self._create_network(network_create_args or {})

    def _create_subnets(self, network,
                        subnet_create_args=None,
                        subnet_cidr_start=None,
                        subnets_per_network=1):
        """Create <count> new subnets in the given network.

        :param network: network to create subnets in
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        :returns: List of subnet dicts
        """
        return [self._create_subnet(network, subnet_create_args or {},
                                    subnet_cidr_start)
                for i in range(subnets_per_network)]

    def _create_network_and_subnets(self,
                                    network_create_args=None,
                                    subnet_create_args=None,
                                    subnets_per_network=1,
                                    subnet_cidr_start="1.0.0.0/24"):
        """Create network and subnets.

        :parm network_create_args: dict, POST /v2.0/networks request options
        :parm subnet_create_args: dict, POST /v2.0/subnets request options
        :parm subnets_per_network: int, number of subnets for one network
        :parm subnet_cidr_start: str, start value for subnets CIDR
        :returns: tuple of result network and subnets list
        """
        network = self._create_network(network_create_args or {})
        subnets = self._create_subnets(network, subnet_create_args,
                                       subnet_cidr_start, subnets_per_network)
        return network, subnets

    def _create_network_structure(self, network_create_args=None,
                                  subnet_create_args=None,
                                  subnet_cidr_start=None,
                                  subnets_per_network=None,
                                  router_create_args=None):
        """Create a network and a given number of subnets and routers.

        :param network_create_args: dict, POST /v2.0/networks request options
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        :param router_create_args: dict, POST /v2.0/routers request options
        :returns: tuple of (network, subnets, routers)
        """
        network = self._get_or_create_network(network_create_args)
        subnets = self._create_subnets(network, subnet_create_args,
                                       subnet_cidr_start,
                                       subnets_per_network)

        routers = []
        for subnet in subnets:
            router = self._create_router(router_create_args or {})
            self._add_interface_router(subnet["subnet"],
                                       router["router"])
            routers.append(router)

        return (network, subnets, routers)

    @atomic.action_timer("neutron.add_interface_router")
    def _add_interface_router(self, subnet, router):
        """Connect subnet to router.

        :param subnet: dict, neutron subnet
        :param router: dict, neutron router
        """
        self.clients("neutron").add_interface_router(
            router["id"], {"subnet_id": subnet["id"]})

    @atomic.action_timer("neutron.remove_interface_router")
    def _remove_interface_router(self, subnet, router):
        """Remove subnet from router

        :param subnet: dict, neutron subnet
        :param router: dict, neutron router
        """
        self.clients("neutron").remove_interface_router(
            router["id"], {"subnet_id": subnet["id"]})

    @atomic.optional_action_timer("neutron.create_pool")
    def _create_lb_pool(self, subnet_id, **pool_create_args):
        """Create LB pool(v1)

        :param subnet_id: str, neutron subnet-id
        :param pool_create_args: dict, POST /lb/pools request options
        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        :returns: dict, neutron lb pool
        """
        args = {"lb_method": self.LB_METHOD,
                "protocol": self.LB_PROTOCOL,
                "name": self.generate_random_name(),
                "subnet_id": subnet_id}
        args.update(pool_create_args)
        return self.clients("neutron").create_pool({"pool": args})

    def _create_v1_pools(self, networks, **pool_create_args):
        """Create LB pools(v1)

        :param networks: list, neutron networks
        :param pool_create_args: dict, POST /lb/pools request options
        :returns: list, neutron lb pools
        """
        subnets = []
        pools = []
        for net in networks:
            subnets.extend(net.get("subnets", []))
        with atomic.ActionTimer(self, "neutron.create_%s_pools" %
                                len(subnets)):
            for subnet_id in subnets:
                pools.append(self._create_lb_pool(
                    subnet_id, atomic_action=False, **pool_create_args))
        return pools

    @atomic.action_timer("neutron.list_pools")
    def _list_v1_pools(self, **kwargs):
        """Return user lb pool list(v1)."""
        return self.clients("neutron").list_pools(**kwargs)

    @atomic.action_timer("neutron.delete_pool")
    def _delete_v1_pool(self, pool):
        """Delete neutron pool.

        :param pool: Pool object
        """
        self.clients("neutron").delete_pool(pool["id"])

    @atomic.action_timer("neutron.update_pool")
    def _update_v1_pool(self, pool, **pool_update_args):
        """Update pool.

        This atomic function updates the pool with pool_update_args.

        :param pool: Pool object
        :param pool_update_args: dict, POST /lb/pools update options
        :returns: updated neutron pool dict
        """
        pool_update_args["name"] = self.generate_random_name()
        body = {"pool": pool_update_args}
        return self.clients("neutron").update_pool(pool["pool"]["id"], body)

    def _create_v1_vip(self, pool, **vip_create_args):
        """Create VIP(v1)

        :parm pool: dict, neutron lb-pool
        :parm vip_create_args: dict, POST /lb/vips request options
        :returns: dict, neutron lb vip
        """
        args = {"protocol": self.LB_PROTOCOL,
                "protocol_port": self.LB_PROTOCOL_PORT,
                "name": self.generate_random_name(),
                "pool_id": pool["pool"]["id"],
                "subnet_id": pool["pool"]["subnet_id"]}
        args.update(vip_create_args)
        return self.clients("neutron").create_vip({"vip": args})

    @atomic.action_timer("neutron.list_vips")
    def _list_v1_vips(self, **kwargs):
        """Return user lb vip list(v1)."""
        return self.clients("neutron").list_vips(**kwargs)

    @atomic.action_timer("neutron.delete_vip")
    def _delete_v1_vip(self, vip):
        """Delete neutron vip.

        :param vip: neutron Virtual IP object
        """
        self.clients("neutron").delete_vip(vip["id"])

    @atomic.action_timer("neutron.update_vip")
    def _update_v1_vip(self, vip, **vip_update_args):
        """Updates vip.

        This atomic function updates vip name and admin state

        :param vip: Vip object
        :param vip_update_args: dict, POST /lb/vips update options
        :returns: updated neutron vip dict
        """
        vip_update_args["name"] = self.generate_random_name()
        body = {"vip": vip_update_args}
        return self.clients("neutron").update_vip(vip["vip"]["id"], body)

    @atomic.action_timer("neutron.create_floating_ip")
    def _create_floatingip(self, floating_network, **floating_ip_args):
        """Create floating IP with floating_network.

        param: floating_network: str, external network to create floating IP
        param: floating_ip_args: dict, POST /floatingips create options
        returns: dict, neutron floating IP
        """
        floating_network_id = self._get_network_id(
            floating_network)
        args = {"floating_network_id": floating_network_id}
        args.update(floating_ip_args)
        return self.clients("neutron").create_floatingip({"floatingip": args})

    @atomic.action_timer("neutron.list_floating_ips")
    def _list_floating_ips(self, **kwargs):
        """Return floating IPs list."""
        return self.clients("neutron").list_floatingips(**kwargs)

    @atomic.action_timer("neutron.delete_floating_ip")
    def _delete_floating_ip(self, floating_ip):
        """Delete floating IP.

        :param: dict, floating IP object
        """
        return self.clients("neutron").delete_floatingip(floating_ip["id"])

    @atomic.optional_action_timer("neutron.create_healthmonitor")
    def _create_v1_healthmonitor(self, **healthmonitor_create_args):
        """Create LB healthmonitor.

        This atomic function creates healthmonitor with the provided
        healthmonitor_create_args.

        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        :param healthmonitor_create_args: dict, POST /lb/healthmonitors
        :returns: neutron healthmonitor dict
        """
        args = {"type": self.HM_TYPE,
                "delay": self.HM_DELAY,
                "max_retries": self.HM_MAX_RETRIES,
                "timeout": self.HM_TIMEOUT}
        args.update(healthmonitor_create_args)
        return self.clients("neutron").create_health_monitor(
            {"health_monitor": args})

    @atomic.action_timer("neutron.list_healthmonitors")
    def _list_v1_healthmonitors(self, **kwargs):
        """List LB healthmonitors.

        This atomic function lists all helthmonitors.

        :param kwargs: optional parameters
        :returns: neutron lb healthmonitor list
        """
        return self.clients("neutron").list_health_monitors(**kwargs)

    @atomic.action_timer("neutron.delete_healthmonitor")
    def _delete_v1_healthmonitor(self, healthmonitor):
        """Delete neutron healthmonitor.

        :param healthmonitor: neutron healthmonitor dict
        """
        self.clients("neutron").delete_health_monitor(healthmonitor["id"])

    @atomic.action_timer("neutron.update_healthmonitor")
    def _update_v1_healthmonitor(self, healthmonitor,
                                 **healthmonitor_update_args):
        """Update neutron healthmonitor.

        :param healthmonitor: neutron lb healthmonitor dict
        :param healthmonitor_update_args: POST /lb/healthmonitors
        update options
        :returns: updated neutron lb healthmonitor dict
        """
        body = {"health_monitor": healthmonitor_update_args}
        return self.clients("neutron").update_health_monitor(
            healthmonitor["health_monitor"]["id"], body)

    @atomic.action_timer("neutron.create_security_group")
    def _create_security_group(self, **security_group_create_args):
        """Create Neutron security-group.

        param: security_group_create_args: dict, POST /v2.0/security-groups
                                          request options
        return: dict, neutron security-group
        """
        security_group_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_security_group(
            {"security_group": security_group_create_args})

    @atomic.action_timer("neutron.delete_security_group")
    def _delete_security_group(self, security_group):
        """Delete Neutron security group.

        param: security_group: dict, neutron security_group
        """
        return self.clients("neutron").delete_security_group(
            security_group["security_group"]["id"])

    @atomic.action_timer("neutron.list_security_groups")
    def _list_security_groups(self, **kwargs):
        """Return list of Neutron security groups."""
        return self.clients("neutron").list_security_groups(**kwargs)

    @atomic.action_timer("neutron.update_security_group")
    def _update_security_group(self, security_group,
                               **security_group_update_args):
        """Update Neutron security-group.

        param: security_group: dict, neutron security_group
        param: security_group_update_args: dict, POST /v2.0/security-groups
                                           update options
        return: dict, updated neutron security-group
        """
        security_group_update_args["name"] = self.generate_random_name()
        body = {"security_group": security_group_update_args}
        return self.clients("neutron").update_security_group(
            security_group["security_group"]["id"], body)
