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

        # Empty options are specified
        network_data = {}
        neutron_scenario.create_and_list_networks(network_data=network_data)
        mock_create.assert_called_once_with(network_data)
        mock_list.assert_called_once_with()

        mock_create.reset_mock()
        mock_list.reset_mock()

        # Explicit network name is specified
        network_data = {"name": "given-name"}
        neutron_scenario.create_and_list_networks(network_data=network_data)
        mock_create.assert_called_once_with(network_data)
        mock_list.assert_called_once_with()

    @mock.patch(NEUTRON_NETWORKS + "._generate_random_name")
    @mock.patch(NEUTRON_NETWORKS + "._list_subnets")
    @mock.patch(NEUTRON_NETWORKS + "._create_subnet")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_list_subnets(self,
                                     mock_create_network,
                                     mock_create_subnet,
                                     mock_list,
                                     mock_random_name):
        scenario = network.NeutronNetworks()
        mock_random_name.return_value = "random-name"
        mock_create_network.return_value = {"network": {"id": "fake-id"}}

        # Empty options
        scenario.create_and_list_subnets()
        mock_create_network.assert_called_once_with({})
        mock_create_subnet.assert_called_once_with(
            {"network": {"id": "fake-id"}}, {})
        mock_list.assert_called_once_with()

        mock_create_network.reset_mock()
        mock_create_subnet.reset_mock()
        mock_list.reset_mock()

        # Extra options are specified
        subnets_num = 4
        scenario.create_and_list_subnets(network_data={"name": "given-name"},
                                         subnet_data={"allocation_pools": []},
                                         subnets_per_network=subnets_num)
        mock_create_network.assert_called_once_with({"name": "given-name"})
        self.assertEqual(mock_create_subnet.mock_calls,
                         [mock.call({"network": {"id": "fake-id"}},
                                    {"allocation_pools": []})] * subnets_num)
        mock_list.assert_called_once_with()
