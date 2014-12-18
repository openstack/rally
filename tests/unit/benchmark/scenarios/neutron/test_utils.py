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
from tests.unit import fakes
from tests.unit import test


NEUTRON_UTILS = "rally.benchmark.scenarios.neutron.utils."


class NeutronScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NeutronScenarioTestCase, self).setUp()
        self.network = mock.Mock()

    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = atomic_actions_time.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario._generate_random_name')
    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_create_network(self, mock_clients, mock_random_name):
        neutron_scenario = utils.NeutronScenario()
        explicit_name = "explicit_name"
        random_name = "random_name"
        mock_random_name.return_value = random_name
        mock_clients("neutron").create_network.return_value = self.network

        # Network name is specified
        network_data = {"name": explicit_name, "admin_state_up": False}
        expected_network_data = {"network": network_data}
        network = neutron_scenario._create_network(network_data)
        mock_clients("neutron").create_network.assert_called_once_with(
            expected_network_data)
        self.assertEqual(self.network, network)
        self._test_atomic_action_timer(neutron_scenario.atomic_actions(),
                                       'neutron.create_network')

        mock_clients("neutron").create_network.reset_mock()

        # Network name is random generated
        network_data = {"admin_state_up": False}
        expected_network_data["network"]["name"] = random_name
        network = neutron_scenario._create_network(network_data)
        mock_clients("neutron").create_network.assert_called_once_with(
            expected_network_data)

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_list_networks(self, mock_clients):
        scenario = utils.NeutronScenario()
        networks_list = []
        networks_dict = {"networks": networks_list}
        mock_clients("neutron").list_networks.return_value = networks_dict
        return_networks_list = scenario._list_networks()
        self.assertEqual(networks_list, return_networks_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.list_networks')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_update_network(self, mock_clients):
        scenario = utils.NeutronScenario()
        expected_network = {
            "network": {
                "name": "network-name_updated",
                "admin_state_up": False
            }
        }
        mock_clients("neutron").update_network.return_value = expected_network

        network = {"network": {"name": "network-name", "id": "network-id"}}
        network_update_args = {"name": "_updated", "admin_state_up": False}

        result_network = scenario._update_network(network, network_update_args)
        mock_clients("neutron").update_network.assert_called_once_with(
                                network["network"]["id"], expected_network)
        self.assertEqual(result_network, expected_network)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.update_network')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_delete_network(self, mock_clients):
        scenario = utils.NeutronScenario()

        network_create_args = {}
        network = scenario._create_network(network_create_args)
        scenario._delete_network(network)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.delete_network')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario._generate_random_name',
                return_value='test_subnet')
    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_create_subnet(self, mock_clients, mock_random_name):
        scenario = utils.NeutronScenario()
        network_id = 'fake-id'
        start_cidr = '192.168.0.0/24'

        network = {'network': {'id': network_id}}
        expected_subnet_data = {
            'subnet': {
                'network_id': network_id,
                'cidr': start_cidr,
                'ip_version': scenario.SUBNET_IP_VERSION,
                'name': mock_random_name.return_value
            }
        }

        # Default options
        subnet_data = {"network_id": network_id}
        scenario._create_subnet(network, subnet_data, start_cidr)
        mock_clients("neutron").create_subnet.assert_called_once_with(
            expected_subnet_data)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "neutron.create_subnet")

        mock_clients("neutron").create_subnet.reset_mock()

        # Custom options
        extras = {'cidr': '192.168.16.0/24', 'allocation_pools': []}
        subnet_data.update(extras)
        expected_subnet_data["subnet"].update(extras)
        scenario._create_subnet(network, subnet_data)
        mock_clients("neutron").create_subnet.assert_called_once_with(
            expected_subnet_data)

    @mock.patch(NEUTRON_UTILS + "NeutronScenario.clients")
    def test_list_subnets(self, mock_clients):
        subnets = [{"name": "fake1"}, {"name": "fake2"}]
        mock_clients("neutron").list_subnets.return_value = {
            "subnets": subnets
        }
        scenario = utils.NeutronScenario()
        result = scenario._list_subnets()
        self.assertEqual(subnets, result)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "neutron.list_subnets")

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_update_subnet(self, mock_clients):
        scenario = utils.NeutronScenario()
        expected_subnet = {
            "subnet": {
                "name": "subnet-name_updated",
                "enable_dhcp": False
            }
        }
        mock_clients("neutron").update_subnet.return_value = expected_subnet

        subnet = {"subnet": {"name": "subnet-name", "id": "subnet-id"}}
        subnet_update_args = {"name": "_updated", "enable_dhcp": False}

        result_subnet = scenario._update_subnet(subnet, subnet_update_args)
        mock_clients("neutron").update_subnet.assert_called_once_with(
                                subnet["subnet"]["id"], expected_subnet)
        self.assertEqual(result_subnet, expected_subnet)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.update_subnet')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_delete_subnet(self, mock_clients):
        scenario = utils.NeutronScenario()

        network = scenario._create_network({})
        subnet = scenario._create_subnet(network, {})
        scenario._delete_subnet(subnet)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.delete_subnet')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario._generate_random_name')
    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_create_router(self, mock_clients, mock_random_name):
        scenario = utils.NeutronScenario()
        router = mock.Mock()
        explicit_name = "explicit_name"
        random_name = "random_name"
        mock_random_name.return_value = random_name
        mock_clients("neutron").create_router.return_value = router

        # Default options
        result_router = scenario._create_router({})
        mock_clients("neutron").create_router.assert_called_once_with(
            {"router": {"name": random_name}})
        self.assertEqual(result_router, router)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.create_router')

        mock_clients("neutron").create_router.reset_mock()

        # Custom options
        router_data = {"name": explicit_name, "admin_state_up": True}
        result_router = scenario._create_router(router_data)
        mock_clients("neutron").create_router.assert_called_once_with(
            {"router": router_data})

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_list_routers(self, mock_clients):
        scenario = utils.NeutronScenario()
        routers = [mock.Mock()]
        mock_clients("neutron").list_routers.return_value = {
            "routers": routers}
        self.assertEqual(routers, scenario._list_routers())
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.list_routers')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_update_router(self, mock_clients):
        scenario = utils.NeutronScenario()
        expected_router = {
            "router": {
                "name": "router-name_updated",
                'admin_state_up': False
            }
        }
        mock_clients("neutron").update_router.return_value = expected_router

        router = {
            "router": {
                "id": "router-id",
                "name": "router-name",
                'admin_state_up': True
            }
        }
        router_update_args = {"name": "_updated", "admin_state_up": False}

        result_router = scenario._update_router(router, router_update_args)
        mock_clients("neutron").update_router.assert_called_once_with(
                                 router['router']['id'], expected_router)
        self.assertEqual(result_router, expected_router)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.update_router')

    def test_SUBNET_IP_VERSION(self):
        """Curent NeutronScenario implementation supports only IPv4."""
        self.assertEqual(utils.NeutronScenario.SUBNET_IP_VERSION, 4)

    @mock.patch(NEUTRON_UTILS + "NeutronScenario._generate_random_name")
    @mock.patch(NEUTRON_UTILS + "NeutronScenario.clients")
    def test_create_port(self, mock_clients, mock_rand_name):
        scenario = utils.NeutronScenario()

        net_id = "network-id"
        net = {"network": {"id": net_id}}
        rand_name = "random-name"
        mock_rand_name.return_value = rand_name
        expected_port_args = {
            "port": {
                "network_id": net_id,
                "name": rand_name
            }
        }

        # Defaults
        port_create_args = {}
        scenario._create_port(net, port_create_args)
        mock_clients("neutron"
                     ).create_port.assert_called_once_with(expected_port_args)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "neutron.create_port")

        mock_clients("neutron").create_port.reset_mock()

        # Custom options
        port_args = {"admin_state_up": True}
        expected_port_args["port"].update(port_args)
        scenario._create_port(net, port_args)
        mock_clients("neutron"
                     ).create_port.assert_called_once_with(expected_port_args)

    @mock.patch(NEUTRON_UTILS + "NeutronScenario.clients")
    def test_list_ports(self, mock_clients):
        scenario = utils.NeutronScenario()
        ports = [{"name": "port1"}, {"name": "port2"}]
        mock_clients("neutron").list_ports.return_value = {"ports": ports}
        self.assertEqual(ports, scenario._list_ports())
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "neutron.list_ports")

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_update_port(self, mock_clients):
        scenario = utils.NeutronScenario()
        expected_port = {
            "port": {
                "name": "port-name_updated",
                "admin_state_up": False,
                "device_id": "dummy_id",
                "device_owner": "dummy_owner"
            }
        }
        mock_clients("neutron").update_port.return_value = expected_port

        port = {
            "port": {
                "id": "port-id",
                "name": "port-name",
                "admin_state_up": True
            }
        }
        port_update_args = {
            "name": "_updated",
            "admin_state_up": False,
            "device_id": "dummy_id",
            "device_owner": "dummy_owner"
        }

        result_port = scenario._update_port(port, port_update_args)
        mock_clients("neutron").update_port.assert_called_once_with(
                                 port['port']['id'], expected_port)
        self.assertEqual(result_port, expected_port)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'neutron.update_port')

    @mock.patch(NEUTRON_UTILS + 'NeutronScenario.clients')
    def test_delete_port(self, mock_clients):
        scenario = utils.NeutronScenario()

        network = scenario._create_network({})
        port = scenario._create_port(network, {})
        scenario._delete_port(port)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "neutron.create_port")

    @mock.patch(NEUTRON_UTILS + "NeutronScenario._create_subnet",
                return_value={
                    "subnet": {
                        "name": "subnet-name",
                        "id": "subnet-id",
                        "enable_dhcp": False
                    }
                })
    @mock.patch(NEUTRON_UTILS + "NeutronScenario._create_network",
                return_value={
                    "network": {
                        "id": "fake-id"
                    }
                })
    def test_create_network_and_subnets(self,
                                        mock_create_network,
                                        mock_create_subnet):
        scenario = utils.NeutronScenario()
        network_create_args = {}
        subnet_create_args = {}
        subnets_per_network = 4

        mock_create_network.reset_mock()
        mock_create_subnet.reset_mock()

        # Default options
        scenario._create_network_and_subnets(
            network_create_args=network_create_args,
            subnet_create_args=subnet_create_args,
            subnets_per_network=subnets_per_network)

        mock_create_network.assert_called_once_with({})
        mock_create_subnet.assert_has_calls(
            [mock.call({"network": {"id": "fake-id"}},
                       {}, "1.0.0.0/24")] * subnets_per_network)

        mock_create_network.reset_mock()
        mock_create_subnet.reset_mock()

        # Custom options
        scenario._create_network_and_subnets(
            network_create_args=network_create_args,
            subnet_create_args={"allocation_pools": []},
            subnet_cidr_start="10.10.10.0/24",
            subnets_per_network=subnets_per_network)

        mock_create_network.assert_called_once_with({})
        mock_create_subnet.assert_has_calls(
            [mock.call({"network": {"id": "fake-id"}},
                       {"allocation_pools": []},
                       "10.10.10.0/24")] * subnets_per_network)

    @mock.patch(NEUTRON_UTILS + "network_wrapper.generate_cidr")
    def test_functional_create_network_and_subnets(self, mock_generate_cidr):
        scenario = utils.NeutronScenario(clients=fakes.FakeClients())
        network_create_args = {"name": "foo_network"}
        subnet_create_args = {}
        subnets_per_network = 5
        subnet_cidr_start = "1.1.1.0/24"

        cidrs = ["1.1.%d.0/24" % i for i in range(subnets_per_network)]
        cidrs_ = iter(cidrs)
        mock_generate_cidr.side_effect = lambda **kw: cidrs_.next()

        network, subnets = scenario._create_network_and_subnets(
            network_create_args,
            subnet_create_args,
            subnets_per_network,
            subnet_cidr_start)

        self.assertEqual(network["network"]["name"], "foo_network")

        # This checks both data (cidrs seem to be enough) and subnets number
        result_cidrs = sorted([s["subnet"]["cidr"] for s in subnets])
        self.assertEqual(cidrs, result_cidrs)
