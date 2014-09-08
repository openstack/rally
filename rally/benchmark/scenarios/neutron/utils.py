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

import netaddr

from rally.benchmark.scenarios import base
from rally.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class NeutronScenario(base.Scenario):
    """This class should contain base operations for benchmarking neutron."""

    RESOURCE_NAME_PREFIX = "rally_net_"
    SUBNET_IP_VERSION = 4
    SUBNET_CIDR_START = "1.1.0.0/30"
    _cidr = 0

    def _generate_subnet_cidr(self, subnets_per_network):
        """Generate next subnet CIDR for network, without IP overlapping.

        We should know total number of subnets for proper aloocation
        non-overlapped subnets

        :param subnets_per_networks: total number of subnets to be allocated
        :returns: str, next available subnet CIDR
        """
        i = self.context()["iteration"]
        cidr = netaddr.IPNetwork(self.SUBNET_CIDR_START)
        cidr = str(cidr.next(subnets_per_network * i + self._cidr))
        LOG.debug("CIDR generated: %s" % cidr)
        self._cidr += 1
        return cidr

    @base.atomic_action_timer('neutron.create_network')
    def _create_network(self, network_create_args):
        """Create neutron network.

        :param network_create_args: dict, POST /v2.0/networks request options
        :returns: neutron network dict
        """
        network_create_args.setdefault("name", self._generate_random_name())
        return self.clients("neutron"
                            ).create_network({"network": network_create_args})

    @base.atomic_action_timer('neutron.list_networks')
    def _list_networks(self):
        """Return user networks list."""
        return self.clients("neutron").list_networks()['networks']

    @base.atomic_action_timer('neutron.delete_network')
    def _delete_network(self, network):
        """Delete neutron network.

        :param network: Network object
        """
        self.clients("neutron").delete_network(network['id'])

    @base.atomic_action_timer('neutron.create_subnet')
    def _create_subnet(self, network, subnets_per_network, subnet_create_args):
        """Create neutron subnet.

        We should know total number of subnets per network for proper
        aloocation of non-overlapped subnets

        :param network: neutron network dict
        :param subnets_per_network: number of subnets per network
        :param subnet_create_args: POST /v2.0/subnets request options
        :returns: neutron subnet dict
        """
        network_id = network["network"]["id"]
        subnet_create_args["network_id"] = network_id
        subnet_create_args.setdefault(
            "name", self._generate_random_name("rally_subnet_"))
        subnet_create_args.setdefault(
            "cidr", self._generate_subnet_cidr(subnets_per_network))
        subnet_create_args.setdefault(
            "ip_version", self.SUBNET_IP_VERSION)

        return self.clients("neutron"
                            ).create_subnet({"subnet": subnet_create_args})

    @base.atomic_action_timer('neutron.list_subnets')
    def _list_subnets(self):
        """Returns user subnetworks list."""
        return self.clients("neutron").list_subnets()["subnets"]

    @base.atomic_action_timer('neutron.delete_subnet')
    def _delete_subnet(self, subnet):
        """Delete neutron subnet

        :param subnet: Subnet object
        """
        self.clients("neutron").delete_subnet(subnet['subnet']['id'])

    @base.atomic_action_timer('neutron.create_router')
    def _create_router(self, router_create_args):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        router_create_args.setdefault(
            "name", self._generate_random_name("rally_router_"))
        return self.clients("neutron"
                            ).create_router({"router": router_create_args})

    @base.atomic_action_timer('neutron.list_routers')
    def _list_routers(self):
        """Returns user routers list."""
        return self.clients("neutron").list_routers()["routers"]

    @base.atomic_action_timer('neutron.create_port')
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

    @base.atomic_action_timer('neutron.list_ports')
    def _list_ports(self):
        """Return user ports list."""
        return self.clients("neutron").list_ports()["ports"]

    @base.atomic_action_timer('neutron.delete_port')
    def _delete_port(self, port):
        """Delete neutron port.

        :param port: Port object
        """
        self.clients("neutron").delete_port(port['port']['id'])
