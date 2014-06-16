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

import mock

from rally.benchmark.scenarios.neutron import network
from tests import test

NEUTRON_NETWORKS = "rally.benchmark.scenarios.neutron.network.NeutronNetworks"


class NeutronNetworksTestCase(test.TestCase):

    @mock.patch(NEUTRON_NETWORKS + "._list_networks")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_list_networks(self, mock_create, mock_list):
        neutron_scenario = network.NeutronNetworks()

        # Default options
        network_create_args = {}
        neutron_scenario.create_and_list_networks(
            network_create_args=network_create_args)
        mock_create.assert_called_once_with(network_create_args)
        mock_list.assert_called_once_with()

        mock_create.reset_mock()
        mock_list.reset_mock()

        # Explicit network name is specified
        network_create_args = {"name": "given-name"}
        neutron_scenario.create_and_list_networks(
            network_create_args=network_create_args)
        mock_create.assert_called_once_with(network_create_args)
        mock_list.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._list_subnets")
    @mock.patch(NEUTRON_NETWORKS + "._create_subnet")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    @mock.patch(NEUTRON_NETWORKS + ".SUBNET_CIDR_START",
                new_callable=mock.PropertyMock(return_value="default_cidr"))
    def test_create_and_list_subnets(self,
                                     mock_cidr_start,
                                     mock_create_network,
                                     mock_create_subnet,
                                     mock_list):
        scenario = network.NeutronNetworks()
        mock_create_network.return_value = {"network": {"id": "fake-id"}}
        subnets_per_network = 4

        self.assertRaises(TypeError, scenario.create_and_list_subnets)

        mock_create_network.reset_mock()
        mock_create_subnet.reset_mock()
        mock_list.reset_mock()

        # Default options
        scenario.create_and_list_subnets(
            subnets_per_network=subnets_per_network)
        mock_create_network.assert_called_once_with({})
        self.assertEqual(mock_create_subnet.mock_calls,
                         [mock.call({"network": {"id": "fake-id"}},
                                    {})] * subnets_per_network)
        mock_list.assert_called_once_with()
        self.assertEqual(scenario.SUBNET_CIDR_START, "default_cidr")

        mock_create_network.reset_mock()
        mock_create_subnet.reset_mock()
        mock_list.reset_mock()

        # Custom options
        scenario.create_and_list_subnets(
            subnet_create_args={"allocation_pools": []},
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network)
        self.assertEqual(scenario.SUBNET_CIDR_START, "custom_cidr")
        mock_create_network.assert_called_once_with({})
        self.assertEqual(
            mock_create_subnet.mock_calls,
            [mock.call({"network": {"id": "fake-id"}},
                       {"allocation_pools": []})] * subnets_per_network)
        mock_list.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._list_routers")
    @mock.patch(NEUTRON_NETWORKS + "._create_router")
    @mock.patch(NEUTRON_NETWORKS + "._create_subnet")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    @mock.patch(NEUTRON_NETWORKS + ".clients")
    def test_create_and_list_routers(self,
                                     mock_clients,
                                     mock_create_network,
                                     mock_create_subnet,
                                     mock_create_router,
                                     mock_list):
        scenario = network.NeutronNetworks()
        subnets_per_network = 4
        mock_clients("neutron").add_interface_router = mock.Mock()

        net = {"network": {"id": "network-id"}}
        mock_create_network.return_value = net

        subnet = {"subnet": {"name": "subnet-name", "id": "subnet-id"}}
        mock_create_subnet.return_value = subnet

        router = {"router": {"name": "router-name", "id": "router-id"}}
        mock_create_router.return_value = router

        # Default options
        scenario.create_and_list_routers(
            subnets_per_network=subnets_per_network)
        mock_create_network.assert_called_once_with({})
        self.assertEqual(
            mock_create_subnet.mock_calls,
            [mock.call(net, {})] * subnets_per_network)
        self.assertEqual(
            mock_create_router.mock_calls,
            [mock.call({})] * subnets_per_network)
        self.assertEqual(
            mock_clients("neutron").add_interface_router.mock_calls,
            [mock.call(router["router"]["id"],
                       {"subnet_id": subnet["subnet"]["id"]})
             ] * subnets_per_network)

        mock_create_network.reset_mock()
        mock_create_subnet.reset_mock()
        mock_create_router.reset_mock()
        mock_clients("neutron").add_interface_router.reset_mock()
        mock_list.reset_mock()

        # Custom options
        subnet_create_args = {"allocation_pools": []}
        router_create_args = {"admin_state_up": False}
        scenario.create_and_list_routers(
            subnet_create_args=subnet_create_args,
            subnet_cidr_start="custom_cidr",
            subnets_per_network=subnets_per_network,
            router_create_args=router_create_args)
        self.assertEqual(scenario.SUBNET_CIDR_START, "custom_cidr")
        mock_create_network.assert_called_once_with({})
        self.assertEqual(
            mock_create_subnet.mock_calls, [
                mock.call({"network": {"id": "network-id"}},
                          subnet_create_args)
            ] * subnets_per_network)
        self.assertEqual(
            mock_create_router.mock_calls, [
                mock.call(router_create_args)
            ] * subnets_per_network)
        self.assertEqual(
            mock_clients("neutron").add_interface_router.mock_calls, [
                mock.call(router["router"]["id"],
                          {"subnet_id": subnet["subnet"]["id"]})
            ] * subnets_per_network)

        mock_list.assert_called_once_with()
