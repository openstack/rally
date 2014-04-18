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

    @mock.patch(NEUTRON_NETWORKS + "._generate_neutron_name")
    @mock.patch(NEUTRON_NETWORKS + "._list_networks")
    @mock.patch(NEUTRON_NETWORKS + "._create_network")
    def test_create_and_list_networks(self, mock_create, mock_list,
                                      mock_random_name):
        neutron_scenario = network.NeutronNetworks()
        mock_random_name.return_value = "test-rally-network"
        neutron_scenario.create_and_list_networks()
        mock_create.assert_called_once_with("test-rally-network")
        mock_list.assert_called_once_with()
