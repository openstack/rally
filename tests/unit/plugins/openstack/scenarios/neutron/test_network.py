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

import ddt
import mock

from rally.plugins.openstack.scenarios.neutron import network
from tests.unit import test

BASE = "rally.plugins.openstack.scenarios.neutron.network"


@ddt.ddt
class NeutronNetworksTestCase(test.ScenarioTestCase):

    @mock.patch("%s.CreateAndListNetworks._list_networks" % BASE)
    @mock.patch("%s.CreateAndListNetworks._create_network" % BASE)
    def test_create_and_list_networks(self,
                                      mock__create_network,
                                      mock__list_networks):
        scenario = network.CreateAndListNetworks(self.context)

        # Default options
        network_create_args = {}
        scenario.run(network_create_args=network_create_args)
        mock__create_network.assert_called_once_with(network_create_args)
        mock__list_networks.assert_called_once_with()

        mock__create_network.reset_mock()
        mock__list_networks.reset_mock()

        # Explicit network name is specified
        network_create_args = {"name": "given-name"}
        scenario.run(network_create_args=network_create_args)
        mock__create_network.assert_called_once_with(network_create_args)
        mock__list_networks.assert_called_once_with()

    @mock.patch("%s.CreateAndUpdateNetworks._update_network" % BASE)
    @mock.patch("%s.CreateAndUpdateNetworks._create_network" % BASE,
                return_value={
                    "network": {
                        "id": "network-id",
                        "name": "network-name",
                        "admin_state_up": False
                    }
                })
    def test_create_and_update_networks(self,
                                        mock__create_network,
                                        mock__update_network):
        scenario = network.CreateAndUpdateNetworks(self.context)

        network_update_args = {"name": "_updated", "admin_state_up": True}

        # Default options
        scenario.run(network_update_args=network_update_args)

        mock__create_network.assert_called_once_with({})

        mock__update_network.assert_has_calls(
            [mock.call(
                mock__create_network.return_value, network_update_args
            )])

        mock__create_network.reset_mock()
        mock__update_network.reset_mock()

        # Explicit network name is specified
        network_create_args = {
            "name": "network-name",
            "admin_state_up": False
        }

        scenario.run(network_create_args=network_create_args,
                     network_update_args=network_update_args)
        mock__create_network.assert_called_once_with(network_create_args)
        mock__update_network.assert_has_calls(
            [mock.call(mock__create_network.return_value,
                       network_update_args)])

    @mock.patch("%s.CreateAndDeleteNetworks._delete_network" % BASE)
    @mock.patch("%s.CreateAndDeleteNetworks._create_network" % BASE)
    def test_create_and_delete_networks(self,
                                        mock__create_network,
                                        mock__delete_network):
        scenario = network.CreateAndDeleteNetworks(self.context)

        # Default options
        network_create_args = {}
        scenario.run()
        mock__create_network.assert_called_once_with(network_create_args)
        self.assertTrue(mock__delete_network.call_count)

        mock__create_network.reset_mock()
        mock__delete_network.reset_mock()

        # Explicit network name is specified
        network_create_args = {"name": "given-name"}
        scenario.run(network_create_args=network_create_args)
        mock__create_network.assert_called_once_with(network_create_args)
        self.assertTrue(mock__delete_network.call_count)

    def test_create_and_list_subnets(self):
        network_create_args = {"router:external": True}
        subnet_create_args = {"allocation_pools": []}
        subnet_cidr_start = "default_cidr"
        subnets_per_network = 5
        net = mock.MagicMock()

        scenario = network.CreateAndListSubnets(self.context)
        scenario._get_or_create_network = mock.Mock(return_value=net)
        scenario._create_subnets = mock.Mock()
        scenario._list_subnets = mock.Mock()

        scenario.run(network_create_args=network_create_args,
                     subnet_create_args=subnet_create_args,
                     subnet_cidr_start=subnet_cidr_start,
                     subnets_per_network=subnets_per_network)

        scenario._get_or_create_network.assert_called_once_with(
            network_create_args)
        scenario._create_subnets.assert_called_once_with(
            net, subnet_create_args, subnet_cidr_start, subnets_per_network)

        scenario._list_subnets.assert_called_once_with()

    def test_create_and_update_subnets(self):
        network_create_args = {"router:external": True}
        subnet_create_args = {"allocation_pools": []}
        subnet_update_args = {"enabled_dhcp": True}
        subnet_cidr_start = "default_cidr"
        subnets_per_network = 5
        net = mock.MagicMock()
        subnets = [mock.MagicMock() for _ in range(subnets_per_network)]

        scenario = network.CreateAndUpdateSubnets(self.context)
        scenario._get_or_create_network = mock.Mock(return_value=net)
        scenario._create_subnets = mock.Mock(return_value=subnets)
        scenario._update_subnet = mock.Mock()

        scenario.run(subnet_update_args,
                     network_create_args=network_create_args,
                     subnet_create_args=subnet_create_args,
                     subnet_cidr_start=subnet_cidr_start,
                     subnets_per_network=subnets_per_network)

        scenario._get_or_create_network.assert_called_once_with(
            network_create_args)
        scenario._create_subnets.assert_called_once_with(
            net, subnet_create_args, subnet_cidr_start, subnets_per_network)
        scenario._update_subnet.assert_has_calls(
            [mock.call(s, subnet_update_args) for s in subnets])

    def test_create_and_delete_subnets(self):
        network_create_args = {"router:external": True}
        subnet_create_args = {"allocation_pools": []}
        subnet_cidr_start = "default_cidr"
        subnets_per_network = 5
        net = mock.MagicMock()
        subnets = [mock.MagicMock() for _ in range(subnets_per_network)]

        scenario = network.CreateAndDeleteSubnets(self.context)
        scenario._get_or_create_network = mock.Mock(return_value=net)
        scenario._create_subnets = mock.Mock(return_value=subnets)
        scenario._delete_subnet = mock.Mock()

        scenario.run(network_create_args=network_create_args,
                     subnet_create_args=subnet_create_args,
                     subnet_cidr_start=subnet_cidr_start,
                     subnets_per_network=subnets_per_network)

        scenario._get_or_create_network.assert_called_once_with(
            network_create_args)
        scenario._create_subnets.assert_called_once_with(
            net, subnet_create_args, subnet_cidr_start, subnets_per_network)
        scenario._delete_subnet.assert_has_calls(
            [mock.call(s) for s in subnets])

    def test_create_and_list_routers(self):
        network_create_args = {"router:external": True}
        subnet_create_args = {"allocation_pools": []}
        subnet_cidr_start = "default_cidr"
        subnets_per_network = 5
        router_create_args = {"admin_state_up": True}

        scenario = network.CreateAndListRouters(self.context)
        scenario._create_network_structure = mock.Mock()
        scenario._list_routers = mock.Mock()

        scenario.run(network_create_args=network_create_args,
                     subnet_create_args=subnet_create_args,
                     subnet_cidr_start=subnet_cidr_start,
                     subnets_per_network=subnets_per_network,
                     router_create_args=router_create_args)

        scenario._create_network_structure.assert_called_once_with(
            network_create_args, subnet_create_args, subnet_cidr_start,
            subnets_per_network, router_create_args)
        scenario._list_routers.assert_called_once_with()

    def test_create_and_update_routers(self):
        router_update_args = {"admin_state_up": False}
        network_create_args = {"router:external": True}
        subnet_create_args = {"allocation_pools": []}
        subnet_cidr_start = "default_cidr"
        subnets_per_network = 5
        router_create_args = {"admin_state_up": True}
        net = mock.MagicMock()
        subnets = [mock.MagicMock() for i in range(subnets_per_network)]
        routers = [mock.MagicMock() for i in range(subnets_per_network)]

        scenario = network.CreateAndUpdateRouters(self.context)
        scenario._create_network_structure = mock.Mock(
            return_value=(net, subnets, routers))
        scenario._update_router = mock.Mock()

        scenario.run(router_update_args,
                     network_create_args=network_create_args,
                     subnet_create_args=subnet_create_args,
                     subnet_cidr_start=subnet_cidr_start,
                     subnets_per_network=subnets_per_network,
                     router_create_args=router_create_args)

        scenario._create_network_structure.assert_called_once_with(
            network_create_args, subnet_create_args, subnet_cidr_start,
            subnets_per_network, router_create_args)

        update_calls = [mock.call(router, router_update_args)
                        for router in routers]
        scenario._update_router.assert_has_calls(update_calls)

    def test_create_and_delete_routers(self):
        network_create_args = {"router:external": True}
        subnet_create_args = {"allocation_pools": []}
        subnet_cidr_start = "default_cidr"
        subnets_per_network = 5
        router_create_args = {"admin_state_up": True}
        net = mock.MagicMock()
        subnets = [mock.MagicMock() for i in range(subnets_per_network)]
        routers = [mock.MagicMock() for i in range(subnets_per_network)]

        scenario = network.CreateAndDeleteRouters(self.context)
        scenario._create_network_structure = mock.Mock(
            return_value=(net, subnets, routers))
        scenario._remove_interface_router = mock.Mock()
        scenario._delete_router = mock.Mock()

        scenario.run(network_create_args=network_create_args,
                     subnet_create_args=subnet_create_args,
                     subnet_cidr_start=subnet_cidr_start,
                     subnets_per_network=subnets_per_network,
                     router_create_args=router_create_args)

        scenario._create_network_structure.assert_called_once_with(
            network_create_args, subnet_create_args, subnet_cidr_start,
            subnets_per_network, router_create_args)

        scenario._remove_interface_router.assert_has_calls([
            mock.call(subnets[i]["subnet"], routers[i]["router"])
            for i in range(subnets_per_network)])
        scenario._delete_router.assert_has_calls(
            [mock.call(router) for router in routers])

    def test_create_and_list_ports(self):
        port_create_args = {"allocation_pools": []}
        ports_per_network = 10
        network_create_args = {"router:external": True}
        net = mock.MagicMock()

        scenario = network.CreateAndListPorts(self.context)
        scenario._get_or_create_network = mock.Mock(return_value=net)
        scenario._create_port = mock.MagicMock()
        scenario._list_ports = mock.Mock()

        scenario.run(network_create_args=network_create_args,
                     port_create_args=port_create_args,
                     ports_per_network=ports_per_network)
        scenario._get_or_create_network.assert_called_once_with(
            network_create_args)
        scenario._create_port.assert_has_calls(
            [mock.call(net, port_create_args)
             for _ in range(ports_per_network)])

        scenario._list_ports.assert_called_once_with()

    def test_create_and_update_ports(self):
        port_update_args = {"admin_state_up": False},
        port_create_args = {"allocation_pools": []}
        ports_per_network = 10
        network_create_args = {"router:external": True}
        net = mock.MagicMock()
        ports = [mock.MagicMock() for _ in range(ports_per_network)]

        scenario = network.CreateAndUpdatePorts(self.context)
        scenario._get_or_create_network = mock.Mock(return_value=net)
        scenario._create_port = mock.Mock(side_effect=ports)
        scenario._update_port = mock.Mock()

        scenario.run(port_update_args,
                     network_create_args=network_create_args,
                     port_create_args=port_create_args,
                     ports_per_network=ports_per_network)
        scenario._get_or_create_network.assert_called_once_with(
            network_create_args)
        scenario._create_port.assert_has_calls(
            [mock.call(net, port_create_args)
             for _ in range(ports_per_network)])
        scenario._update_port.assert_has_calls(
            [mock.call(p, port_update_args) for p in ports])

    def test_create_and_delete_ports(self):
        port_create_args = {"allocation_pools": []}
        ports_per_network = 10
        network_create_args = {"router:external": True}
        net = mock.MagicMock()
        ports = [mock.MagicMock() for _ in range(ports_per_network)]

        scenario = network.CreateAndDeletePorts(self.context)
        scenario._get_or_create_network = mock.Mock(return_value=net)
        scenario._create_port = mock.Mock(side_effect=ports)
        scenario._delete_port = mock.Mock()

        scenario.run(network_create_args=network_create_args,
                     port_create_args=port_create_args,
                     ports_per_network=ports_per_network)
        scenario._get_or_create_network.assert_called_once_with(
            network_create_args)
        scenario._create_port.assert_has_calls(
            [mock.call(net, port_create_args)
             for _ in range(ports_per_network)])
        scenario._delete_port.assert_has_calls(
            [mock.call(p) for p in ports])

    @ddt.data(
        {"floating_network": "ext-net"},
        {"floating_network": "ext-net",
         "floating_ip_args": {"floating_ip_address": "1.1.1.1"}},
    )
    @ddt.unpack
    def test_create_and_list_floating_ips(self, floating_network=None,
                                          floating_ip_args=None):
        scenario = network.CeateAndListFloatingIps(self.context)
        floating_ip_args = floating_ip_args or {}
        scenario._create_floatingip = mock.Mock()
        scenario._list_floating_ips = mock.Mock()
        scenario.run(floating_network=floating_network,
                     floating_ip_args=floating_ip_args)
        scenario._create_floatingip.assert_called_once_with(
            floating_network, **floating_ip_args)
        scenario._list_floating_ips.assert_called_once_with()

    @ddt.data(
        {"floating_network": "ext-net"},
        {"floating_network": "ext-net",
         "floating_ip_args": {"floating_ip_address": "1.1.1.1"}},
    )
    @ddt.unpack
    def test_create_and_delete_floating_ips(self, floating_network=None,
                                            floating_ip_args=None):
        scenario = network.CreateAndDeleteFloatingIps(self.context)
        floating_ip_args = floating_ip_args or {}
        fip = {"floatingip": {"id": "floating-ip-id"}}
        scenario._create_floatingip = mock.Mock(return_value=fip)
        scenario._delete_floating_ip = mock.Mock()
        scenario.run(floating_network=floating_network,
                     floating_ip_args=floating_ip_args)
        scenario._create_floatingip.assert_called_once_with(
            floating_network, **floating_ip_args)
        scenario._delete_floating_ip.assert_called_once_with(
            scenario._create_floatingip.return_value["floatingip"])
