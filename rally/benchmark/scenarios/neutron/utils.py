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
import string

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils


TEMP_TEMPLATE = "rally_n_"


class NeutronScenario(base.Scenario):
    """This class should contain base operations for benchmarking neutron,
       most of them are creating/deleting resources.
    """

    def _generate_neutron_name(self, length=10):
        """Generate random name for neutron resources."""

        rand_part = ''.join(random.choice(
                            string.lowercase) for i in range(length))
        return TEMP_TEMPLATE + rand_part

    @scenario_utils.atomic_action_timer('neutron.create_network')
    def _create_network(self, network_name, **kwargs):
        """Creates neutron network with random name.

        :param network_name: the name of network
        :param **kwargs: Other optional parameters to create networks like
                        "tenant_id", "shared".
        :return: neutron network instance
        """

        kwargs.setdefault("name", network_name)
        return self.clients("neutron").create_network({"network": kwargs})

    @scenario_utils.atomic_action_timer('neutron.list_networks')
    def _list_networks(self):
        """Returns user networks list."""
        return self.clients("neutron").list_networks()['networks']
