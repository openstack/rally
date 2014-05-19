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
from rally.benchmark.scenarios import utils as scenario_utils


class NeutronScenario(base.Scenario):
    """This class should contain base operations for benchmarking neutron,
       most of them are creating/deleting resources.
    """

    RESOURCE_NAME_PREFIX = "rally_net_"
    SUBNET_IP_VERSION = 4
    SUBNET_CIDR_PATTERN = "192.168.%d.0/24"

    _subnet_cidrs = {}

    @classmethod
    def _generate_subnet_cidr(cls, network_id):
        """Generates next subnet CIDR for given network,
           without IP overlapping.
        """
        if network_id in cls._subnet_cidrs:
            cidr_no = cls._subnet_cidrs[network_id]
            if cidr_no > 255:
                # NOTE(amaretskiy): consider whether max number of
                #                   255 subnets per network is enough.
                raise ValueError(
                    "can not generate more than 255 subnets CIDRs "
                    "per one network due to IP pattern limitation")
        else:
            cidr_no = 0

        cls._subnet_cidrs[network_id] = cidr_no + 1
        return cls.SUBNET_CIDR_PATTERN % cidr_no

    @scenario_utils.atomic_action_timer('neutron.create_network')
    def _create_network(self, network_data):
        """Creates neutron network.

        :param network_data: options for API v2.0 networks POST request
        :returns: neutron network dict
        """
        network_data.setdefault("name", self._generate_random_name())
        return self.clients("neutron").create_network({
                "network": network_data})

    @scenario_utils.atomic_action_timer('neutron.list_networks')
    def _list_networks(self):
        """Returns user networks list."""
        return self.clients("neutron").list_networks()['networks']

    @scenario_utils.atomic_action_timer('neutron.create_subnet')
    def _create_subnet(self, network, subnet_data):
        """Creates neutron subnet.

        :param network: neutron network dict
        :param subnet_data: options for API v2.0 subnets POST request
        :returns: neutron subnet dict
        """
        network_id = network["network"]["id"]
        subnet_data["network_id"] = network_id
        subnet_data.setdefault("cidr",
                               self._generate_subnet_cidr(network_id))
        subnet_data.setdefault("ip_version", self.SUBNET_IP_VERSION)

        return self.clients("neutron").create_subnet({"subnet": subnet_data})

    @scenario_utils.atomic_action_timer('neutron.list_subnets')
    def _list_subnets(self):
        """Returns user subnetworks list."""
        return self.clients("neutron").list_subnets()["subnets"]
