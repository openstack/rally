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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.neutron import utils


class NeutronNetworks(utils.NeutronScenario):

    @base.scenario(context={"cleanup": ["neutron"]})
    def create_and_list_networks(self, network_data=None):
        """Tests creating a network and then listing all networks.

        This scenario is a very useful tool to measure
        the "neutron net-list" command performance.

        If you have only 1 user in your context, you will
        add 1 network on every iteration. So you will have more
        and more networks and will be able to measure the
        performance of the "neutron net-list" command depending on
        the number of networks owned by users.

        :param network_data: dict, network options
        """
        self._create_network(network_data or {})
        self._list_networks()

    @base.scenario(context={"cleanup": ["neutron"]})
    def create_and_list_subnets(self,
                                network_data=None,
                                subnet_data=None,
                                subnets_per_network=1):
        """Tests creating a network, a given number of subnets
        and then list subnets.

        :param network_data: dict, network options
        :param subnet_data: dict, subnet options
        :param subnets_per_network: int, number of subnets for one network
        """

        network = self._create_network(network_data or {})
        for i in range(subnets_per_network):
            self._create_subnet(network, subnet_data or {})

        self._list_subnets()
