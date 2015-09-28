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

NEUTRON_NETWORKS = ("rally.plugins.openstack.scenarios.neutron.network"
                    ".NeutronNetworks")


@ddt.ddt
class NeutronNetworksTestCase(test.ScenarioTestCase):

    @mock.patch(NEUTRON_NETWORKS + "._list_networks")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_list_networks(self, mock__create_network,
                                      mock__list_networks):
        neutron_scenario = network.NeutronNetworks(self.context)

        # Default options
        network_create_args = {}
        neutron_scenario.create_and_list_networks(
            network_create_args=network_create_args)
        mock__create_network.assert_called_once_with(network_create_args)
        mock__list_networks.assert_called_once_with()

        mock__create_network.reset_mock()
        mock__list_networks.reset_mock()

        # Explicit network name is specified
        network_create_args = {"name": "given-name"}
        neutron_scenario.create_and_list_networks(
            network_create_args=network_create_args)
        mock__create_network.assert_called_once_with(network_create_args)
        mock__list_networks.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._update_network")
    @mock.patch(NEUTRON_NETWORKS + "._create_network", return_value={
        "network": {
            "id": "network-id",
            "name": "network-name",
            "admin_state_up": False
        }
    })
    def test_create_and_update_networks(self,
                                        mock__create_network,
                                        mock__update_network):
        scenario = network.NeutronNetworks(self.context)

        network_update_args = {"name": "_updated", "admin_state_up": True}

        # Default options
        scenario.create_and_update_networks(
            network_update_args=network_update_args)

        mock__create_network.assert_called_once_with({})

        mock__update_network.assert_has_calls(
            [mock.call(
                mock__create_network.return_value, network_update_args
            )])

        mock__create_network.reset_mock()
        mock__update_network.reset_mock()

        # Explicit network name is specified
        network_create_args = {"name": "network-name", "admin_state_up": False}

        scenario.create_and_update_networks(
            network_create_args=network_create_args,
            network_update_args=network_update_args)
        mock__create_network.assert_called_once_with(network_create_args)
        mock__update_network.assert_has_calls(
            [mock.call(mock__create_network.return_value,
                       network_update_args)])

    @mock.patch(NEUTRON_NETWORKS + "._delete_network")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_delete_networks(self, mock__create_network,
                                        mock__delete_network):
        neutron_scenario = network.NeutronNetworks(self.context)

        # Default options
        network_create_args = {}
        neutron_scenario.create_and_delete_networks()
        mock__create_network.assert_called_once_with(network_create_args)
        self.assertEqual(1, mock__delete_network.call_count)

        mock__create_network.reset_mock()
        mock__delete_network.reset_mock()

        # Explicit network name is specified
        network_create_args = {"name": "given-name"}
        neutron_scenario.create_and_delete_networks(
            network_create_args=network_create_args)
        mock__create_network.assert_called_once_with(network_create_args)
        self.assertEqual(1, mock__delete_network.call_count)

    @mock.patch(NEUTRON_NETWORKS + "._list_subnets")
    @mock.patch(NEUTRON_NETWORKS + "._create_network_and_subnets")
    def test_create_and_list_subnets(self,
                                     mock__create_network_and_subnets,
                                     mock__list_subnets):
        scenario = network.NeutronNetworks(self.context)
        subnets_per_network = 4
        subnet_cidr_start = "default_cidr"

        # Default options
        scenario.create_and_list_subnets(
            subnets_per_network=subnets_per_network,
            subnet_cidr_start=subnet_cidr_start)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {}, subnets_per_network,
                       subnet_cidr_start)])
        mock__list_subnets.assert_called_once_with()

        mock__create_network_and_subnets.reset_mock()
        mock__list_subnets.reset_mock()

        # Custom options
        scenario.create_and_list_subnets(
            subnet_create_args={"allocation_pools": []},
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {"allocation_pools": []},
                       subnets_per_network, "custom_cidr")])
        mock__list_subnets.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._update_subnet")
    @mock.patch(NEUTRON_NETWORKS + "._create_network_and_subnets")
    def test_create_and_update_subnets(self,
                                       mock__create_network_and_subnets,
                                       mock__update_subnet):
        scenario = network.NeutronNetworks(self.context)
        subnets_per_network = 1
        subnet_cidr_start = "default_cidr"
        net = {
            "network": {
                "id": "network-id"
            }
        }
        subnet = {
            "subnet": {
                "name": "subnet-name",
                "id": "subnet-id",
                "enable_dhcp": False
            }
        }
        mock__create_network_and_subnets.return_value = (net, [subnet])
        subnet_update_args = {"name": "_updated", "enable_dhcp": True}

        # Default options
        scenario.create_and_update_subnets(
            subnet_update_args=subnet_update_args,
            subnet_cidr_start=subnet_cidr_start,
            subnets_per_network=subnets_per_network)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {}, subnets_per_network, subnet_cidr_start)])
        mock__update_subnet.assert_has_calls(
            [mock.call(subnet, subnet_update_args)])

        mock__create_network_and_subnets.reset_mock()
        mock__update_subnet.reset_mock()

        # Custom options
        subnet_cidr_start = "custom_cidr"
        scenario.create_and_update_subnets(
            subnet_update_args=subnet_update_args,
            subnet_create_args={"allocation_pools": []},
            subnet_cidr_start=subnet_cidr_start,
            subnets_per_network=subnets_per_network)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {"allocation_pools": []}, subnets_per_network,
                       subnet_cidr_start)])
        mock__update_subnet.assert_has_calls(
            [mock.call(subnet, subnet_update_args)])

    @mock.patch(NEUTRON_NETWORKS + "._delete_subnet")
    @mock.patch(NEUTRON_NETWORKS + "._create_network_and_subnets")
    def test_create_and_delete_subnets(self,
                                       mock__create_network_and_subnets,
                                       mock__delete_subnet):
        scenario = network.NeutronNetworks(self.context)
        net = {
            "network": {
                "id": "network-id"
            }
        }
        subnet = {
            "subnet": {
                "name": "subnet-name",
                "id": "subnet-id",
                "enable_dhcp": False
            }
        }
        mock__create_network_and_subnets.return_value = (net, [subnet])
        subnets_per_network = 1
        subnet_cidr_start = "default_cidr"

        # Default options
        scenario.create_and_delete_subnets(
            subnets_per_network=subnets_per_network,
            subnet_cidr_start=subnet_cidr_start)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {}, subnets_per_network,
                       subnet_cidr_start)])

        mock__delete_subnet.assert_has_calls([mock.call(subnet)])

        mock__create_network_and_subnets.reset_mock()
        mock__delete_subnet.reset_mock()

        # Custom options
        subnet_cidr_start = "custom_cidr"
        scenario.create_and_delete_subnets(
            subnet_create_args={"allocation_pools": []},
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {"allocation_pools": []}, subnets_per_network,
                       subnet_cidr_start)])
        mock__delete_subnet.assert_has_calls([mock.call(subnet)])

    @mock.patch(NEUTRON_NETWORKS + "._list_routers")
    @mock.patch(NEUTRON_NETWORKS + "._create_router")
    @mock.patch(NEUTRON_NETWORKS + "._create_network_and_subnets")
    def test_create_and_list_routers(self,
                                     mock__create_network_and_subnets,
                                     mock__create_router,
                                     mock__list_routers):
        scenario = network.NeutronNetworks(self.context)
        subnets_per_network = 1
        subnet_cidr_start = "default_cidr"

        net = {
            "network": {
                "id": "network-id"
            }
        }
        subnet = {
            "subnet": {
                "name": "subnet-name",
                "id": "subnet-id",
                "enable_dhcp": False
            }
        }
        mock__create_network_and_subnets.return_value = (net, [subnet])
        self.clients("neutron").add_interface_router = mock.Mock()
        router = {
            "router": {
                "name": "router-name",
                "id": "router-id"
            }
        }
        mock__create_router.return_value = router

        # Default options
        scenario.create_and_list_routers(
            subnet_cidr_start=subnet_cidr_start,
            subnets_per_network=subnets_per_network)
        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {}, subnets_per_network, subnet_cidr_start)])

        mock__create_router.assert_has_calls(
            [mock.call({})] * subnets_per_network)

        self.clients("neutron").add_interface_router.assert_has_calls(
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock__create_network_and_subnets.reset_mock()
        mock__create_router.reset_mock()

        self.clients("neutron").add_interface_router.reset_mock()
        mock__list_routers.reset_mock()

        # Custom options
        subnet_cidr_start = "custom_cidr"
        subnet_create_args = {"allocation_pools": []}
        router_create_args = {"admin_state_up": False}
        scenario.create_and_list_routers(
            subnet_create_args=subnet_create_args,
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network,
            router_create_args=router_create_args)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, subnet_create_args, subnets_per_network,
             subnet_cidr_start)])

        mock__create_router.assert_has_calls(
            [mock.call(router_create_args)] * subnets_per_network)
        self.clients("neutron").add_interface_router.assert_has_calls(
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock__list_routers.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._update_router")
    @mock.patch(NEUTRON_NETWORKS + "._create_router")
    @mock.patch(NEUTRON_NETWORKS + "._create_network_and_subnets")
    def test_create_and_update_routers(self,
                                       mock__create_network_and_subnets,
                                       mock__create_router,
                                       mock__update_router):
        scenario = network.NeutronNetworks(self.context)
        subnets_per_network = 1
        subnet_cidr_start = "default_cidr"

        net = {
            "network": {
                "id": "network-id"
            }
        }
        subnet = {
            "subnet": {
                "name": "subnet-name",
                "id": "subnet-id",
                "enable_dhcp": False
            }
        }
        router = {
            "router": {
                "name": "router-name",
                "id": "router-id"
            }
        }
        router_update_args = {
            "name": "_updated",
            "admin_state_up": False
        }
        mock__create_router.return_value = router
        mock__create_network_and_subnets.return_value = (net, [subnet])
        self.clients("neutron").add_interface_router = mock.Mock()

        # Default options
        scenario.create_and_update_routers(
            router_update_args=router_update_args,
            subnet_cidr_start=subnet_cidr_start,
            subnets_per_network=subnets_per_network)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {}, subnets_per_network, subnet_cidr_start)])

        mock__create_router.assert_has_calls(
            [mock.call({})] * subnets_per_network)
        self.clients("neutron").add_interface_router.assert_has_calls(
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock__update_router.assert_has_calls(
            [mock.call(router, router_update_args)
             ] * subnets_per_network)

        mock__create_network_and_subnets.reset_mock()
        mock__create_router.reset_mock()
        self.clients("neutron").add_interface_router.reset_mock()
        mock__update_router.reset_mock()

        # Custom options
        subnet_cidr_start = "custom_cidr"
        subnet_create_args = {"allocation_pools": []}
        router_create_args = {"admin_state_up": False}
        scenario.create_and_update_routers(
            router_update_args=router_update_args,
            subnet_create_args=subnet_create_args,
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network,
            router_create_args=router_create_args)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, subnet_create_args, subnets_per_network,
             subnet_cidr_start)])

        mock__create_router.assert_has_calls(
            [mock.call(router_create_args)] * subnets_per_network)
        self.clients("neutron").add_interface_router.assert_has_calls(
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock__update_router.assert_has_calls(
            [mock.call(router, router_update_args)
             ] * subnets_per_network)

    @mock.patch(NEUTRON_NETWORKS + "._delete_router")
    @mock.patch(NEUTRON_NETWORKS + "._create_router")
    @mock.patch(NEUTRON_NETWORKS + "._create_network_and_subnets")
    def test_create_and_delete_routers(self,
                                       mock__create_network_and_subnets,
                                       mock__create_router,
                                       mock__delete_router):
        scenario = network.NeutronNetworks(self.context)
        subnets_per_network = 1
        subnet_cidr_start = "default_cidr"

        net = {
            "network": {
                "id": "network-id"
            }
        }
        subnet = {
            "subnet": {
                "name": "subnet-name",
                "id": "subnet-id",
                "enable_dhcp": False
            }
        }
        router = {
            "router": {
                "name": "router-name",
                "id": "router-id"
            }
        }

        mock__create_router.return_value = router
        mock__create_network_and_subnets.return_value = (net, [subnet])
        self.clients("neutron").add_interface_router = mock.Mock()

        # Default options
        scenario.create_and_delete_routers(
            subnet_cidr_start=subnet_cidr_start,
            subnets_per_network=subnets_per_network)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, {}, subnets_per_network, subnet_cidr_start)])

        mock__create_router.assert_has_calls(
            [mock.call({})] * subnets_per_network)
        self.clients("neutron").add_interface_router.assert_has_calls(
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock__delete_router.assert_has_calls(
            [mock.call(router)] * subnets_per_network)

        mock__create_network_and_subnets.reset_mock()
        mock__create_router.reset_mock()
        self.clients("neutron").add_interface_router.reset_mock()
        mock__delete_router.reset_mock()

        # Custom options
        subnet_cidr_start = "custom_cidr"
        subnet_create_args = {"allocation_pools": []}
        router_create_args = {"admin_state_up": False}
        scenario.create_and_delete_routers(
            subnet_create_args=subnet_create_args,
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network,
            router_create_args=router_create_args)

        mock__create_network_and_subnets.assert_has_calls(
            [mock.call({}, subnet_create_args, subnets_per_network,
             subnet_cidr_start)])

        mock__create_router.assert_has_calls(
            [mock.call(router_create_args)] * subnets_per_network)
        self.clients("neutron").add_interface_router.assert_has_calls(
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock__delete_router.assert_has_calls(
            [mock.call(router)] * subnets_per_network)

    @mock.patch(NEUTRON_NETWORKS + "._generate_random_name")
    @mock.patch(NEUTRON_NETWORKS + "._list_ports")
    @mock.patch(NEUTRON_NETWORKS + "._create_port")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_list_ports(self,
                                   mock__create_network,
                                   mock__create_port,
                                   mock__list_ports,
                                   mock__generate_random_name):
        scenario = network.NeutronNetworks(self.context)
        mock__generate_random_name.return_value = "random-name"
        net = {"network": {"id": "fake-id"}}
        mock__create_network.return_value = net
        ports_per_network = 10

        self.assertRaises(TypeError, scenario.create_and_list_ports)

        mock__create_network.reset_mock()

        # Defaults
        scenario.create_and_list_ports(ports_per_network=ports_per_network)
        mock__create_network.assert_called_once_with({})
        self.assertEqual(mock__create_port.mock_calls,
                         [mock.call(net, {})] * ports_per_network)
        mock__list_ports.assert_called_once_with()

        mock__create_network.reset_mock()
        mock__create_port.reset_mock()
        mock__list_ports.reset_mock()

        # Custom options
        scenario.create_and_list_ports(
            network_create_args={"name": "given-name"},
            port_create_args={"allocation_pools": []},
            ports_per_network=ports_per_network)
        mock__create_network.assert_called_once_with({"name": "given-name"})
        self.assertEqual(
            mock__create_port.mock_calls,
            [mock.call(net, {"allocation_pools": []})] * ports_per_network)
        mock__list_ports.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._generate_random_name")
    @mock.patch(NEUTRON_NETWORKS + "._update_port")
    @mock.patch(NEUTRON_NETWORKS + "._create_port", return_value={
        "port": {
            "name": "port-name",
            "id": "port-id",
            "admin_state_up": True
        }
    })
    @mock.patch(NEUTRON_NETWORKS + "._create_network", return_value={
        "network": {"id": "fake-id"}})
    def test_create_and_update_ports(self,
                                     mock__create_network,
                                     mock__create_port,
                                     mock__update_port,
                                     mock__generate_random_name):
        scenario = network.NeutronNetworks(self.context)
        mock__generate_random_name.return_value = "random-name"
        ports_per_network = 10

        port_update_args = {
            "name": "_updated",
            "admin_state_up": False
        }

        # Defaults
        scenario.create_and_update_ports(
            port_update_args=port_update_args,
            ports_per_network=ports_per_network)
        mock__create_network.assert_called_once_with({})

        mock__create_port.assert_has_calls(
            [mock.call({"network": {"id": "fake-id"}},
                       {})] * ports_per_network)
        mock__update_port.assert_has_calls(
            [mock.call(mock__create_port.return_value, port_update_args)
             ] * ports_per_network)

        mock__create_network.reset_mock()
        mock__create_port.reset_mock()
        mock__update_port.reset_mock()

        # Custom options
        scenario.create_and_update_ports(
            port_update_args=port_update_args,
            network_create_args={"name": "given-name"},
            port_create_args={"allocation_pools": []},
            ports_per_network=ports_per_network)
        mock__create_network.assert_called_once_with({"name": "given-name"})
        mock__create_port.assert_has_calls(
            [mock.call({"network": {"id": "fake-id"}},
                       {"allocation_pools": []})] * ports_per_network)
        mock__update_port.assert_has_calls(
            [mock.call(mock__create_port.return_value, port_update_args)
             ] * ports_per_network)

    @mock.patch(NEUTRON_NETWORKS + "._generate_random_name")
    @mock.patch(NEUTRON_NETWORKS + "._delete_port")
    @mock.patch(NEUTRON_NETWORKS + "._create_port")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_delete_ports(self,
                                     mock__create_network,
                                     mock__create_port,
                                     mock__delete_port,
                                     mock__generate_random_name):
        scenario = network.NeutronNetworks(self.context)
        mock__generate_random_name.return_value = "random-name"
        net = {"network": {"id": "fake-id"}}
        mock__create_network.return_value = net
        ports_per_network = 10

        self.assertRaises(TypeError, scenario.create_and_delete_ports)

        mock__create_network.reset_mock()

        # Default options
        scenario.create_and_delete_ports(ports_per_network=ports_per_network)
        mock__create_network.assert_called_once_with({})
        self.assertEqual(mock__create_port.mock_calls,
                         [mock.call(net, {})] * ports_per_network)
        self.assertEqual(mock__delete_port.mock_calls,
                         [mock.call(mock__create_port())] * ports_per_network)

        mock__create_network.reset_mock()
        mock__create_port.reset_mock()
        mock__delete_port.reset_mock()

        # Custom options
        scenario.create_and_delete_ports(
            network_create_args={"name": "given-name"},
            port_create_args={"allocation_pools": []},
            ports_per_network=ports_per_network)
        mock__create_network.assert_called_once_with({"name": "given-name"})
        self.assertEqual(
            mock__create_port.mock_calls,
            [mock.call(net, {"allocation_pools": []})] * ports_per_network)
        self.assertEqual(
            mock__delete_port.mock_calls,
            [mock.call(mock__create_port.return_value)] * ports_per_network)

    @ddt.data(
        {"floating_network": "ext-net"},
        {"floating_network": "ext-net",
         "floating_ip_args": {"floating_ip_address": "1.1.1.1"}},
    )
    @ddt.unpack
    def test_create_and_list_floating_ips(self, floating_network=None,
                                          floating_ip_args=None):
        scenario = network.NeutronNetworks()
        floating_ip_args = floating_ip_args or {}
        scenario._create_floatingip = mock.Mock()
        scenario._list_floating_ips = mock.Mock()
        scenario.create_and_list_floating_ips(
            floating_network=floating_network,
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
        scenario = network.NeutronNetworks()
        floating_ip_args = floating_ip_args or {}
        fip = {"floatingip": {"id": "floating-ip-id"}}
        scenario._create_floatingip = mock.Mock(return_value=fip)
        scenario._delete_floating_ip = mock.Mock()
        scenario.create_and_delete_floating_ips(
            floating_network=floating_network,
            floating_ip_args=floating_ip_args)
        scenario._create_floatingip.assert_called_once_with(
            floating_network, **floating_ip_args)
        scenario._delete_floating_ip.assert_called_once_with(
            scenario._create_floatingip.return_value["floatingip"])
