# Copyright 2013: Intel Inc.
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

from rally.benchmark.scenarios.neutron import utils
from tests.benchmark.scenarios import test_utils

from tests import test


NEUTRON_UTILS = "rally.benchmark.scenarios.neutron.utils."


class NeutronScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NeutronScenarioTestCase, self).setUp()
        self.network = mock.Mock()

    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions_time, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(NEUTRON_UTILS + "random.choice")
    def test_generate_neutron_name(self, mock_random_choice):
        mock_random_choice.return_value = "a"

        for length in [10, 20]:
            result = utils.NeutronScenario()._generate_neutron_name(length)
            self.assertEqual(result, utils.TEMP_TEMPLATE + "a" * length)

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_create_network(self, mock_clients):
        mock_clients("neutron").create_network.return_value = self.network
        args = {"network_name": "test_network_name",
                "arg1": "test_args1",
                "arg2": "test_args2"}
        expected_create_network_args = {"network": {
                                            "name": "test_network_name",
                                            "arg1": "test_args1",
                                            "arg2": "test_args2"}}
        neutron_scenario = utils.NeutronScenario()
        return_network = neutron_scenario._create_network(**args)
        mock_clients("neutron").create_network.assert_called_once_with(
            expected_create_network_args)
        self.assertEqual(self.network, return_network)
        self._test_atomic_action_timer(neutron_scenario.atomic_actions(),
                                       'neutron.create_network')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_list_networks(self, mock_clients):
        networks_list = []
        networks_dict = {"networks": networks_list}
        mock_clients("neutron").list_networks.return_value = networks_dict
        neutron_scenario = utils.NeutronScenario()
        return_networks_list = neutron_scenario._list_networks()
        self.assertEqual(networks_list, return_networks_list)
        self._test_atomic_action_timer(neutron_scenario.atomic_actions(),
                                       'neutron.list_networks')
