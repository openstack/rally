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

from oslo_utils import uuidutils as uid

from rally.benchmark.scenarios import base
from rally.common import log as logging
from rally.plugins.openstack.wrappers import network as network_wrapper

LOG = logging.getLogger(__name__)


class NeutronScenario(base.Scenario):
    """Base class for Neutron scenarios with basic atomic actions."""

    RESOURCE_NAME_PREFIX = "rally_net_"
    RESOURCE_NAME_LENGTH = 16
    SUBNET_IP_VERSION = 4

    @base.atomic_action_timer("neutron.create_network")
    def _create_network(self, network_create_args):
        """Create neutron network.

        :param network_create_args: dict, POST /v2.0/networks request options
        :returns: neutron network dict
        """
        network_create_args.setdefault("name", self._generate_random_name())
        return self.clients("neutron").create_network(
            {"network": network_create_args})

    @base.atomic_action_timer("neutron.list_networks")
    def _list_networks(self):
        """Return user networks list."""
        return self.clients("neutron").list_networks()["networks"]

    @base.atomic_action_timer("neutron.update_network")
    def _update_network(self, network, network_update_args):
        """Update the network name and admin state.

        This atomic function updates network name by
        appending the existing name and admin state with network_update_args.

        :param network: Network object
        :param network_update_args: dict, POST /v2.0/networks update options
        :returns: updated neutron network dict
        """
        suffix = network_update_args.get(
            "name", self._generate_random_name("_"))
        admin_state_up = network_update_args.get("admin_state_up", True)
        body = {
            "network": {
                "name": network["network"]["name"] + suffix,
                "admin_state_up": admin_state_up
            }
        }
        return self.clients("neutron").update_network(
            network["network"]["id"], body)

    @base.atomic_action_timer("neutron.delete_network")
    def _delete_network(self, network):
        """Delete neutron network.

        :param network: Network object
        """
        self.clients("neutron").delete_network(network["id"])

    @base.atomic_action_timer("neutron.create_subnet")
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
        subnet_create_args.setdefault(
            "name", self._generate_random_name("rally_subnet_"))
        subnet_create_args.setdefault("ip_version", self.SUBNET_IP_VERSION)

        return self.clients("neutron").create_subnet(
            {"subnet": subnet_create_args})

    @base.atomic_action_timer("neutron.list_subnets")
    def _list_subnets(self):
        """Returns user subnetworks list."""
        return self.clients("neutron").list_subnets()["subnets"]

    @base.atomic_action_timer("neutron.update_subnet")
    def _update_subnet(self, subnet, subnet_update_args):
        """Update the neutron subnet name and DHCP status.

        This atomic function updates subnet name by
        appending the existing name and DHCP status with subnet_update_args.

        :param subnet: Subnet object
        :param subnet_update_args: dict, PUT /v2.0/subnets update options
        :returns: updated neutron subnet dict
        """
        suffix = subnet_update_args.get(
            "name", self._generate_random_name("_"))
        enable_dhcp = subnet_update_args.get("enable_dhcp", True)
        body = {
            "subnet": {
                "name": subnet["subnet"]["name"] + suffix,
                "enable_dhcp": enable_dhcp
            }
        }
        return self.clients("neutron").update_subnet(
            subnet["subnet"]["id"], body)

    @base.atomic_action_timer("neutron.delete_subnet")
    def _delete_subnet(self, subnet):
        """Delete neutron subnet

        :param subnet: Subnet object
        """
        self.clients("neutron").delete_subnet(subnet["subnet"]["id"])

    @base.atomic_action_timer("neutron.create_router")
    def _create_router(self, router_create_args, external_gw=False):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        router_create_args.setdefault(
            "name", self._generate_random_name("rally_router_"))

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

    @base.atomic_action_timer("neutron.list_routers")
    def _list_routers(self):
        """Returns user routers list."""
        return self.clients("neutron").list_routers()["routers"]

    @base.atomic_action_timer("neutron.delete_router")
    def _delete_router(self, router):
        """Delete neutron router

        :param router: Router object
        """
        self.clients("neutron").delete_router(router["router"]["id"])

    @base.atomic_action_timer("neutron.update_router")
    def _update_router(self, router, router_update_args):
        """Update the neutron router name and admin state.

        This atomic function updates router name by
        appending the existing name and admin state with router_update_args.

        :param router: dict, neutron router
        :param router_update_args: dict, PUT /v2.0/routers update options
        :returns: updated neutron router dict
        """
        suffix = router_update_args.get(
            "name", self._generate_random_name("_"))
        admin_state = router_update_args.get("admin_state_up", True)
        body = {
            "router": {
                "name": router["router"]["name"] + suffix,
                "admin_state_up": admin_state
            }
        }
        return self.clients("neutron").update_router(
            router["router"]["id"], body)

    @base.atomic_action_timer("neutron.create_port")
    def _create_port(self, network, port_create_args):
        """Create neutron port.

        :param network: neutron network dict
        :param port_create_args: POST /v2.0/ports request options
        :returns: neutron port dict
        """
        port_create_args["network_id"] = network["network"]["id"]
        port_create_args.setdefault(
            "name", self._generate_random_name("rally_port_"))
        return self.clients("neutron").create_port({"port": port_create_args})

    @base.atomic_action_timer("neutron.list_ports")
    def _list_ports(self):
        """Return user ports list."""
        return self.clients("neutron").list_ports()["ports"]

    @base.atomic_action_timer("neutron.update_port")
    def _update_port(self, port, port_update_args):
        """Update the neutron port name, admin state, device id and owner.

        This atomic function updates port name by
        appending the existing name, admin state, device id and
        device owner with port_update_args.

        :param port: dict, neutron port
        :param port_update_args: dict, PUT /v2.0/ports update options
        :returns: updated neutron port dict
        """
        suffix = port_update_args.get(
            "name", self._generate_random_name("_"))
        admin_state = port_update_args.get("admin_state_up", True)
        device_owner = port_update_args.get("device_owner", "compute:nova")
        device_id = port_update_args.get("device_id", uid.generate_uuid())
        body = {
            "port": {
                "name": port["port"]["name"] + suffix,
                "admin_state_up": admin_state,
                "device_id": device_id,
                "device_owner": device_owner
            }
        }
        return self.clients("neutron").update_port(port["port"]["id"], body)

    @base.atomic_action_timer("neutron.delete_port")
    def _delete_port(self, port):
        """Delete neutron port.

        :param port: Port object
        """
        self.clients("neutron").delete_port(port["port"]["id"])

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
        subnets = []
        network = self._create_network(network_create_args or {})

        for i in range(subnets_per_network):
            subnet = self._create_subnet(network, subnet_create_args or {},
                                         subnet_cidr_start)
            subnets.append(subnet)
        return network, subnets

    @base.atomic_action_timer("neutron.add_interface_router")
    def _add_interface_router(self, subnet, router):
        """Connect subnet to router.

        :param subnet: dict, neutron subnet
        :param router: dict, neutron router
        """
        self.clients("neutron").add_interface_router(
            router["id"], {"subnet_id": subnet["id"]})

    @base.atomic_action_timer("neutron.remove_interface_router")
    def _remove_interface_router(self, subnet, router):
        """Remove subnet from router

        :param subnet: dict, neutron subnet
        :param router: dict, neutron router
        """
        self.clients("neutron").remove_interface_router(
            router["id"], {"subnet_id": subnet["id"]})
