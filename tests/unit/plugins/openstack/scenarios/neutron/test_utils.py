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

import ddt
import mock

from rally import exceptions
from rally.plugins.openstack.scenarios.neutron import utils
from tests.unit import test

NEUTRON_UTILS = "rally.plugins.openstack.scenarios.neutron.utils"


@ddt.ddt
class NeutronScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(NeutronScenarioTestCase, self).setUp()
        self.network = mock.Mock()
        self.scenario = utils.NeutronScenario(self.context)

        self.random_name = "random_name"
        self.scenario.generate_random_name = mock.Mock(
            return_value=self.random_name)

    def test__get_network_id(self):
        networks = [{"id": "foo-id", "name": "foo-network"},
                    {"id": "bar-id", "name": "bar-network"}]
        network_id = "foo-id"

        # Valid network-name
        network = "foo-network"
        self.scenario._list_networks = mock.Mock(return_value=networks)
        resultant_network_id = self.scenario._get_network_id(network)
        self.assertEqual(network_id, resultant_network_id)
        self.scenario._list_networks.assert_called_once_with()

        self.scenario._list_networks.reset_mock()

        # Valid network-id
        network = "foo-id"
        resultant_network_id = self.scenario._get_network_id(network)
        self.assertEqual(network_id, resultant_network_id)
        self.scenario._list_networks.assert_called_once_with()
        self.scenario._list_networks.reset_mock()

        # Invalid network-name
        network = "absent-network"
        self.assertRaises(exceptions.NotFoundException,
                          self.scenario._get_network_id, network)
        self.scenario._list_networks.assert_called_once_with()

    def test_create_network(self):
        self.clients("neutron").create_network.return_value = self.network

        network_data = {"admin_state_up": False}
        expected_network_data = {"network": network_data}
        network = self.scenario._create_network(network_data)
        self.assertEqual(self.network, network)
        self.clients("neutron").create_network.assert_called_once_with(
            expected_network_data)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_network")

    def test_list_networks(self):
        networks_list = []
        networks_dict = {"networks": networks_list}
        self.clients("neutron").list_networks.return_value = networks_dict

        # without atomic action
        return_networks_list = self.scenario._list_networks()
        self.assertEqual(networks_list, return_networks_list)

        # with atomic action
        return_networks_list = self.scenario._list_networks()
        self.assertEqual(networks_list, return_networks_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_networks", count=2)

    def test_show_network(self):
        network = {
            "network": {
                "id": "fake-id",
                "name": "fake-name",
                "admin_state_up": False
            }
        }

        return_network = self.scenario._show_network(network)
        self.assertEqual(self.clients("neutron").show_network.return_value,
                         return_network)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.show_network")

    def test_show_router(self):
        router = {
            "router": {
                "id": "fake-id",
                "name": "fake-name",
                "admin_state_up": False
            }
        }

        return_router = self.scenario._show_router(router)
        self.assertEqual(self.clients("neutron").show_router.return_value,
                         return_router)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.show_router")

    def test_update_network(self):
        expected_network = {
            "network": {
                "name": self.scenario.generate_random_name.return_value,
                "admin_state_up": False,
                "fakearg": "fake"
            }
        }
        self.clients("neutron").update_network.return_value = expected_network

        network = {"network": {"name": "network-name", "id": "network-id"}}
        network_update_args = {"name": "foo",
                               "admin_state_up": False,
                               "fakearg": "fake"}

        result_network = self.scenario._update_network(network,
                                                       network_update_args)
        self.clients("neutron").update_network.assert_called_once_with(
            network["network"]["id"], expected_network)
        self.assertEqual(expected_network, result_network)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_network")

    def test_delete_network(self):
        network_create_args = {}
        network = self.scenario._create_network(network_create_args)
        self.scenario._delete_network(network)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_network")

    @mock.patch("%s.network_wrapper" % NEUTRON_UTILS)
    def test_create_subnet(self, mock_network_wrapper):
        network_id = "fake-id"
        start_cidr = "192.168.0.0/24"
        mock_network_wrapper.generate_cidr.return_value = "192.168.0.0/24"

        network = {"network": {"id": network_id}}
        expected_subnet_data = {
            "subnet": {
                "network_id": network_id,
                "cidr": start_cidr,
                "ip_version": self.scenario.SUBNET_IP_VERSION,
                "name": self.scenario.generate_random_name.return_value
            }
        }

        # Default options
        subnet_data = {"network_id": network_id}
        self.scenario._create_subnet(network, subnet_data, start_cidr)
        self.clients("neutron").create_subnet.assert_called_once_with(
            expected_subnet_data)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_subnet")

        self.clients("neutron").create_subnet.reset_mock()

        # Custom options
        extras = {"cidr": "192.168.16.0/24", "allocation_pools": []}
        mock_network_wrapper.generate_cidr.return_value = "192.168.16.0/24"
        subnet_data.update(extras)
        expected_subnet_data["subnet"].update(extras)
        self.scenario._create_subnet(network, subnet_data)
        self.clients("neutron").create_subnet.assert_called_once_with(
            expected_subnet_data)

    def test_list_subnets(self):
        subnets = [{"name": "fake1"}, {"name": "fake2"}]
        self.clients("neutron").list_subnets.return_value = {
            "subnets": subnets
        }
        result = self.scenario._list_subnets()
        self.assertEqual(subnets, result)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_subnets")

    def test_show_subnet(self):
        subnet = {"subnet": {"name": "fake-name", "id": "fake-id"}}

        result_subnet = self.scenario._show_subnet(subnet)
        self.assertEqual(self.clients("neutron").show_subnet.return_value,
                         result_subnet)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.show_subnet")

    def test_update_subnet(self):
        expected_subnet = {
            "subnet": {
                "name": self.scenario.generate_random_name.return_value,
                "enable_dhcp": False,
                "fakearg": "fake"
            }
        }
        self.clients("neutron").update_subnet.return_value = expected_subnet

        subnet = {"subnet": {"name": "subnet-name", "id": "subnet-id"}}
        subnet_update_args = {"name": "foo", "enable_dhcp": False,
                              "fakearg": "fake"}

        result_subnet = self.scenario._update_subnet(subnet,
                                                     subnet_update_args)
        self.clients("neutron").update_subnet.assert_called_once_with(
            subnet["subnet"]["id"], expected_subnet)
        self.assertEqual(expected_subnet, result_subnet)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_subnet")

    def test_delete_subnet(self):
        network = self.scenario._create_network({})
        subnet = self.scenario._create_subnet(network, {})
        self.scenario._delete_subnet(subnet)

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_subnet")

    def test_create_router(self):
        router = mock.Mock()
        self.clients("neutron").create_router.return_value = router

        # Default options
        result_router = self.scenario._create_router({})
        self.clients("neutron").create_router.assert_called_once_with({
            "router": {
                "name": self.scenario.generate_random_name.return_value
            }
        })
        self.assertEqual(result_router, router)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_router")

    def test_create_router_with_ext_gw(self):
        router = mock.Mock()
        external_network = [{"id": "ext-net", "router:external": True}]
        self.scenario._list_networks = mock.Mock(return_value=external_network)
        self.clients("neutron").create_router.return_value = router
        self.clients("neutron").list_extensions.return_value = {
            "extensions": [{"alias": "ext-gw-mode"}]}

        # External_gw options
        gw_info = {"network_id": external_network[0]["id"],
                   "enable_snat": True}
        router_data = {
            "name": self.scenario.generate_random_name.return_value,
            "external_gateway_info": gw_info
        }
        result_router = self.scenario._create_router({}, external_gw=True)
        self.clients("neutron").create_router.assert_called_once_with(
            {"router": router_data})
        self.assertEqual(result_router, router)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "neutron.create_router")

    def test_create_router_with_ext_gw_but_no_ext_net(self):
        router = mock.Mock()
        external_network = [{"id": "ext-net", "router:external": False}]
        self.scenario._list_networks = mock.Mock(return_value=external_network)
        self.clients("neutron").create_router.return_value = router
        self.clients("neutron").list_extensions.return_value = {
            "extensions": [{"alias": "ext-gw-mode"}]}

        # External_gw options with no external networks in list_networks()
        result_router = self.scenario._create_router({}, external_gw=True)
        self.clients("neutron").create_router.assert_called_once_with({
            "router": {"name": self.scenario.generate_random_name.return_value}
        })
        self.assertEqual(result_router, router)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_router")

    def test_create_router_with_ext_gw_but_no_ext_gw_mode_extension(self):
        router = mock.Mock()
        external_network = [{"id": "ext-net", "router:external": True}]
        self.scenario._list_networks = mock.Mock(return_value=external_network)
        self.clients("neutron").create_router.return_value = router
        self.clients("neutron").list_extensions.return_value = {
            "extensions": []}

        # External_gw options
        gw_info = {"network_id": external_network[0]["id"]}
        router_data = {
            "name": self.scenario.generate_random_name.return_value,
            "external_gateway_info": gw_info
        }
        result_router = self.scenario._create_router({}, external_gw=True)
        self.clients("neutron").create_router.assert_called_once_with(
            {"router": router_data})
        self.assertEqual(result_router, router)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "neutron.create_router")

    def test_create_router_explicit(self):
        router = mock.Mock()
        self.clients("neutron").create_router.return_value = router

        # Custom options
        router_data = {"name": "explicit_name", "admin_state_up": True}
        result_router = self.scenario._create_router(router_data)
        self.clients("neutron").create_router.assert_called_once_with(
            {"router": router_data})
        self.assertEqual(result_router, router)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_router")

    def test_list_routers(self):
        routers = [mock.Mock()]
        self.clients("neutron").list_routers.return_value = {
            "routers": routers}
        self.assertEqual(routers, self.scenario._list_routers())
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_routers")

    def test_list_agents(self):
        agents = [mock.Mock()]
        self.clients("neutron").list_agents.return_value = {
            "agents": agents}
        self.assertEqual(agents, self.scenario._list_agents())
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_agents")

    def test_update_router(self):
        expected_router = {
            "router": {
                "name": self.scenario.generate_random_name.return_value,
                "admin_state_up": False,
                "fakearg": "fake"
            }
        }
        self.clients("neutron").update_router.return_value = expected_router

        router = {
            "router": {
                "id": "router-id",
                "name": "router-name",
                "admin_state_up": True
            }
        }
        router_update_args = {"name": "foo",
                              "admin_state_up": False,
                              "fakearg": "fake"}

        result_router = self.scenario._update_router(router,
                                                     router_update_args)
        self.clients("neutron").update_router.assert_called_once_with(
            router["router"]["id"], expected_router)
        self.assertEqual(expected_router, result_router)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_router")

    def test_delete_router(self):
        router = self.scenario._create_router({})
        self.scenario._delete_router(router)
        self.clients("neutron").delete_router.assert_called_once_with(
            router["router"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_router")

    def test_remove_interface_router(self):
        subnet = {"name": "subnet-name", "id": "subnet-id"}
        router_data = {"id": 1}
        router = self.scenario._create_router(router_data)
        self.scenario._add_interface_router(subnet, router)
        self.scenario._remove_interface_router(subnet, router)
        mock_remove_router = self.clients("neutron").remove_interface_router
        mock_remove_router.assert_called_once_with(
            router["id"], {"subnet_id": subnet["id"]})
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.remove_interface_router")

    def test_add_gateway_router(self):
        ext_net = {
            "network": {
                "name": "extnet-name",
                "id": "extnet-id"
            }
        }
        router = {
            "router": {
                "name": "router-name",
                "id": "router-id"
            }
        }
        enable_snat = "fake_snat"
        gw_info = {"network_id": ext_net["network"]["id"],
                   "enable_snat": enable_snat}
        self.clients("neutron").list_extensions.return_value = {
            "extensions": [{"alias": "ext-gw-mode"}]}

        self.scenario._add_gateway_router(router, ext_net, enable_snat)
        self.clients("neutron").add_gateway_router.assert_called_once_with(
            router["router"]["id"], gw_info)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.add_gateway_router")

    def test_add_gateway_router_without_ext_gw_mode_extension(self):
        ext_net = {
            "network": {
                "name": "extnet-name",
                "id": "extnet-id"
            }
        }
        router = {
            "router": {
                "name": "router-name",
                "id": "router-id"
            }
        }
        enable_snat = "fake_snat"
        gw_info = {"network_id": ext_net["network"]["id"]}
        self.clients("neutron").list_extensions.return_value = {
            "extensions": {}}

        self.scenario._add_gateway_router(router, ext_net, enable_snat)
        self.clients("neutron").add_gateway_router.assert_called_once_with(
            router["router"]["id"], gw_info)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.add_gateway_router")

    def test_remove_gateway_router(self):
        router = {
            "router": {
                "name": "router-name",
                "id": "router-id"
            }
        }
        self.scenario._remove_gateway_router(router)
        self.clients("neutron").remove_gateway_router.assert_called_once_with(
            router["router"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.remove_gateway_router")

    def test_SUBNET_IP_VERSION(self):
        """Curent NeutronScenario implementation supports only IPv4."""
        self.assertEqual(4, utils.NeutronScenario.SUBNET_IP_VERSION)

    def test_create_port(self):
        net_id = "network-id"
        net = {"network": {"id": net_id}}
        expected_port_args = {
            "port": {
                "network_id": net_id,
                "name": self.scenario.generate_random_name.return_value
            }
        }

        # Defaults
        port_create_args = {}
        self.scenario._create_port(net, port_create_args)
        self.clients("neutron"
                     ).create_port.assert_called_once_with(expected_port_args)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_port")

        self.clients("neutron").create_port.reset_mock()

        # Custom options
        port_args = {"admin_state_up": True}
        expected_port_args["port"].update(port_args)
        self.scenario._create_port(net, port_args)
        self.clients("neutron"
                     ).create_port.assert_called_once_with(expected_port_args)

    def test_list_ports(self):
        ports = [{"name": "port1"}, {"name": "port2"}]
        self.clients("neutron").list_ports.return_value = {"ports": ports}
        self.assertEqual(ports, self.scenario._list_ports())
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_ports")

    def test_show_port(self):
        expect_port = {
            "port": {
                "id": "port-id",
                "name": "port-name",
                "admin_state_up": True
            }
        }
        self.clients("neutron").show_port.return_value = expect_port
        self.assertEqual(expect_port, self.scenario._show_port(expect_port))
        self.clients("neutron").show_port.assert_called_once_with(
            expect_port["port"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.show_port")

    def test_update_port(self):
        expected_port = {
            "port": {
                "admin_state_up": False,
                "fakearg": "fake",
                "name": self.scenario.generate_random_name.return_value
            }
        }
        self.clients("neutron").update_port.return_value = expected_port

        port = {
            "port": {
                "id": "port-id",
                "name": "port-name",
                "admin_state_up": True
            }
        }
        port_update_args = {
            "admin_state_up": False,
            "fakearg": "fake"
        }

        result_port = self.scenario._update_port(port, port_update_args)
        self.clients("neutron").update_port.assert_called_once_with(
            port["port"]["id"], expected_port)
        self.assertEqual(expected_port, result_port)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_port")

    def test_delete_port(self):
        network = self.scenario._create_network({})
        port = self.scenario._create_port(network, {})
        self.scenario._delete_port(port)

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_port")

    @ddt.data(
        {"context": {"tenant": {"networks":
                                [mock.MagicMock(), mock.MagicMock()]}}},
        {"network_create_args": {"fakearg": "fake"},
         "context": {"tenant": {"networks":
                                [mock.MagicMock(), mock.MagicMock()]}}})
    @ddt.unpack
    @mock.patch("random.choice", side_effect=lambda l: l[0])
    def test_get_or_create_network(self, mock_random_choice,
                                   network_create_args=None, context=None):
        self.scenario.context = context
        self.scenario._create_network = mock.Mock(
            return_value={"network": mock.Mock()})

        network = self.scenario._get_or_create_network(network_create_args)

        # ensure that the return value is the proper type either way
        self.assertIn("network", network)

        if "networks" in context["tenant"]:
            self.assertEqual(network,
                             {"network": context["tenant"]["networks"][0]})
            self.assertFalse(self.scenario._create_network.called)
        else:
            self.assertEqual(network,
                             self.scenario._create_network.return_value)
            self.scenario._create_network.assert_called_once_with(
                network_create_args or {})

    @mock.patch("%s.NeutronScenario._create_subnet" % NEUTRON_UTILS)
    @mock.patch("%s.NeutronScenario._create_network" % NEUTRON_UTILS)
    def test_create_network_and_subnets(self,
                                        mock__create_network,
                                        mock__create_subnet):
        mock__create_network.return_value = {"network": {"id": "fake-id"}}
        mock__create_subnet.return_value = {
            "subnet": {
                "name": "subnet-name",
                "id": "subnet-id",
                "enable_dhcp": False
            }
        }

        network_create_args = {}
        subnet_create_args = {}
        subnets_per_network = 4

        # Default options
        self.scenario._create_network_and_subnets(
            network_create_args=network_create_args,
            subnet_create_args=subnet_create_args,
            subnets_per_network=subnets_per_network)

        mock__create_network.assert_called_once_with({})
        mock__create_subnet.assert_has_calls(
            [mock.call({"network": {"id": "fake-id"}},
                       {}, "1.0.0.0/24")] * subnets_per_network)

        mock__create_network.reset_mock()
        mock__create_subnet.reset_mock()

        # Custom options
        self.scenario._create_network_and_subnets(
            network_create_args=network_create_args,
            subnet_create_args={"allocation_pools": []},
            subnet_cidr_start="10.10.10.0/24",
            subnets_per_network=subnets_per_network)

        mock__create_network.assert_called_once_with({})
        mock__create_subnet.assert_has_calls(
            [mock.call({"network": {"id": "fake-id"}},
                       {"allocation_pools": []},
                       "10.10.10.0/24")] * subnets_per_network)

    def test_list_floating_ips(self):
        fips_list = [{"id": "floating-ip-id"}]
        fips_dict = {"floatingips": fips_list}
        self.clients("neutron").list_floatingips.return_value = fips_dict
        self.assertEqual(self.scenario._list_floating_ips(),
                         self.clients("neutron").list_floatingips.return_value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_floating_ips")

    def test_delete_floating_ip(self):
        fip = {"floatingip": {"id": "fake-id"}}
        self.scenario._delete_floating_ip(fip["floatingip"])
        self.clients("neutron").delete_floatingip.assert_called_once_with(
            fip["floatingip"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_floating_ip")

    @ddt.data(
        {},
        {"router_create_args": {"admin_state_up": False}},
        {"network_create_args": {"router:external": True},
         "subnet_create_args": {"allocation_pools": []},
         "subnet_cidr_start": "default_cidr",
         "subnets_per_network": 3,
         "router_create_args": {"admin_state_up": False}})
    @ddt.unpack
    def test_create_network_structure(self, network_create_args=None,
                                      subnet_create_args=None,
                                      subnet_cidr_start=None,
                                      subnets_per_network=None,
                                      router_create_args=None):
        network = mock.MagicMock()

        router_create_args = router_create_args or {}

        subnets = []
        routers = []
        router_create_calls = []
        for i in range(subnets_per_network or 1):
            subnets.append(mock.MagicMock())
            routers.append(mock.MagicMock())
            router_create_calls.append(mock.call(router_create_args))

        self.scenario._create_network = mock.Mock(return_value=network)
        self.scenario._create_subnets = mock.Mock(return_value=subnets)
        self.scenario._create_router = mock.Mock(side_effect=routers)
        self.scenario._add_interface_router = mock.Mock()

        actual = self.scenario._create_network_structure(network_create_args,
                                                         subnet_create_args,
                                                         subnet_cidr_start,
                                                         subnets_per_network,
                                                         router_create_args)
        self.assertEqual((network, subnets, routers), actual)
        self.scenario._create_network.assert_called_once_with(
            network_create_args or {})
        self.scenario._create_subnets.assert_called_once_with(
            network,
            subnet_create_args,
            subnet_cidr_start,
            subnets_per_network)
        self.scenario._create_router.assert_has_calls(router_create_calls)

        add_iface_calls = [mock.call(subnets[i]["subnet"],
                                     routers[i]["router"])
                           for i in range(subnets_per_network or 1)]
        self.scenario._add_interface_router.assert_has_calls(add_iface_calls)

    def test_delete_v1_pool(self):
        pool = {"pool": {"id": "fake-id"}}
        self.scenario._delete_v1_pool(pool["pool"])
        self.clients("neutron").delete_pool.assert_called_once_with(
            pool["pool"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_pool")

    def test_update_pool(self):
        expected_pool = {
            "pool": {
                "name": self.scenario.generate_random_name.return_value,
                "admin_state_up": False,
                "fakearg": "fake"
            }
        }
        self.clients("neutron").update_pool.return_value = expected_pool

        pool = {"pool": {"name": "pool-name", "id": "pool-id"}}
        pool_update_args = {"name": "foo",
                            "admin_state_up": False,
                            "fakearg": "fake"}

        result_pool = self.scenario._update_v1_pool(pool, **pool_update_args)
        self.assertEqual(expected_pool, result_pool)
        self.clients("neutron").update_pool.assert_called_once_with(
            pool["pool"]["id"], expected_pool)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_pool")

    def test_list_v1_pools(self):
        pools_list = []
        pools_dict = {"pools": pools_list}
        self.clients("neutron").list_pools.return_value = pools_dict
        return_pools_dict = self.scenario._list_v1_pools()
        self.assertEqual(pools_dict, return_pools_dict)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_pools")

    def test_list_v1_vips(self):
        vips_list = []
        vips_dict = {"vips": vips_list}
        self.clients("neutron").list_vips.return_value = vips_dict
        return_vips_dict = self.scenario._list_v1_vips()
        self.assertEqual(vips_dict, return_vips_dict)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_vips")

    def test_delete_v1_vip(self):
        vip = {"vip": {"id": "fake-id"}}
        self.scenario._delete_v1_vip(vip["vip"])
        self.clients("neutron").delete_vip.assert_called_once_with(
            vip["vip"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_vip")

    def test_update_v1_vip(self):
        expected_vip = {
            "vip": {
                "name": self.scenario.generate_random_name.return_value,
                "admin_state_up": False
            }
        }
        self.clients("neutron").update_vip.return_value = expected_vip

        vip = {"vip": {"name": "vip-name", "id": "vip-id"}}
        vip_update_args = {"name": "foo", "admin_state_up": False}

        result_vip = self.scenario._update_v1_vip(vip, **vip_update_args)
        self.assertEqual(expected_vip, result_vip)
        self.clients("neutron").update_vip.assert_called_once_with(
            vip["vip"]["id"], expected_vip)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_vip")

    @mock.patch("%s.NeutronScenario.generate_random_name" % NEUTRON_UTILS)
    def test_create_security_group(self, mock_generate_random_name):
        security_group_create_args = {"description": "Fake security group"}
        expected_security_group = {
            "security_group": {
                "id": "fake-id",
                "name": self.scenario.generate_random_name.return_value,
                "description": "Fake security group"
            }
        }
        self.clients("neutron").create_security_group = mock.Mock(
            return_value=expected_security_group)

        security_group_data = {
            "security_group":
                {"name": "random_name",
                 "description": "Fake security group"}
        }
        resultant_security_group = self.scenario._create_security_group(
            **security_group_create_args)
        self.assertEqual(expected_security_group, resultant_security_group)
        self.clients("neutron").create_security_group.assert_called_once_with(
            security_group_data)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_security_group")

    def test_list_security_groups(self):
        security_groups_list = [{"id": "security-group-id"}]
        security_groups_dict = {"security_groups": security_groups_list}
        self.clients("neutron").list_security_groups = mock.Mock(
            return_value=security_groups_dict)
        self.assertEqual(
            self.scenario._list_security_groups(),
            self.clients("neutron").list_security_groups.return_value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_security_groups")

    def test_show_security_group(self):
        security_group = {"security_group": {"id": "fake-id"}}
        result = self.scenario._show_security_group(security_group)
        self.assertEqual(
            result,
            self.clients("neutron").show_security_group.return_value)
        self.clients("neutron").show_security_group.assert_called_once_with(
            security_group["security_group"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.show_security_group")

    def test_delete_security_group(self):
        security_group = {"security_group": {"id": "fake-id"}}
        self.scenario._delete_security_group(security_group)
        self.clients("neutron").delete_security_group.assert_called_once_with(
            security_group["security_group"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_security_group")

    def test_update_security_group(self):
        security_group = {
            "security_group": {
                "id": "security-group-id",
                "description": "Not updated"
            }
        }
        expected_security_group = {
            "security_group": {
                "id": "security-group-id",
                "name": self.scenario.generate_random_name.return_value,
                "description": "Updated"
            }
        }

        self.clients("neutron").update_security_group = mock.Mock(
            return_value=expected_security_group)
        result_security_group = self.scenario._update_security_group(
            security_group, description="Updated")
        self.clients("neutron").update_security_group.assert_called_once_with(
            security_group["security_group"]["id"],
            {"security_group": {
                "description": "Updated",
                "name": self.scenario.generate_random_name.return_value}}
        )
        self.assertEqual(expected_security_group, result_security_group)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_security_group")

    def test_create_security_group_rule(self):
        security_group_rule_args = {"description": "Fake Rule"}
        expected_security_group_rule = {
            "security_group_rule": {
                "id": "fake-id",
                "security_group_id": "security-group-id",
                "direction": "ingress",
                "description": "Fake Rule"
            }
        }
        client = self.clients("neutron")
        client.create_security_group_rule = mock.Mock(
            return_value=expected_security_group_rule)

        security_group_rule_data = {
            "security_group_rule":
                {"security_group_id": "security-group-id",
                 "direction": "ingress",
                 "description": "Fake Rule"}
        }
        result_security_group_rule = self.scenario._create_security_group_rule(
            "security-group-id", **security_group_rule_args)
        self.assertEqual(expected_security_group_rule,
                         result_security_group_rule)
        client.create_security_group_rule.assert_called_once_with(
            security_group_rule_data)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_security_group_rule")

    def test_list_security_group_rules(self):
        security_group_rules_list = [{"id": "security-group-rule-id"}]
        security_group_rules_dict = {
            "security_group_rules": security_group_rules_list}

        self.clients("neutron").list_security_group_rules = mock.Mock(
            return_value=security_group_rules_dict)
        self.assertEqual(
            self.scenario._list_security_group_rules(),
            self.clients("neutron").list_security_group_rules.return_value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_security_group_rules")

    def test_show_security_group_rule(self):
        return_rule = self.scenario._show_security_group_rule(1)
        self.assertEqual(
            self.clients("neutron").show_security_group_rule.return_value,
            return_rule)

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.show_security_group_rule")

    def test_delete_security_group_rule(self):
        self.scenario._delete_security_group_rule(1)
        clients = self.clients("neutron")
        clients.delete_security_group_rule.assert_called_once_with(1)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_security_group_rule")

    @ddt.data(
        {"networks": [{"subnets": "subnet-id"}]},
        {"pool_create_args": None, "networks": [{"subnets": ["subnet-id"]}]},
        {"pool_create_args": {}, "networks": [{"subnets": ["subnet-id"]}]},
        {"pool_create_args": {"name": "given-name"},
            "networks": [{"subnets": ["subnet-id"]}]},
    )
    @ddt.unpack
    def test__create_v1_pools(self, networks, pool_create_args=None):
        pool_create_args = pool_create_args or {}
        pool = {"pool": {"id": "pool-id"}}
        self.scenario._create_lb_pool = mock.Mock(return_value=pool)
        resultant_pools = self.scenario._create_v1_pools(
            networks=networks, **pool_create_args)
        if networks:
            subnets = []
            [subnets.extend(net["subnets"]) for net in networks]
            self.scenario._create_lb_pool.assert_has_calls(
                [mock.call(subnet,
                           **pool_create_args) for subnet in subnets])
            self.assertEqual([pool] * len(subnets), resultant_pools)

    @ddt.data(
        {"subnet_id": "foo-id"},
        {"pool_create_args": None, "subnet_id": "foo-id"},
        {"pool_create_args": {}, "subnet_id": "foo-id"},
        {"pool_create_args": {"name": "given-name"},
         "subnet_id": "foo-id"},
        {"subnet_id": "foo-id"}
    )
    @ddt.unpack
    def test__create_lb_pool(self, subnet_id=None,
                             pool_create_args=None):
        pool = {"pool": {"id": "pool-id"}}
        pool_create_args = pool_create_args or {}
        if pool_create_args.get("name") is None:
            self.generate_random_name = mock.Mock(return_value="random_name")
        self.clients("neutron").create_pool.return_value = pool
        args = {"lb_method": "ROUND_ROBIN", "protocol": "HTTP",
                "name": "random_name", "subnet_id": subnet_id}
        args.update(pool_create_args)
        expected_pool_data = {"pool": args}
        resultant_pool = self.scenario._create_lb_pool(
            subnet_id=subnet_id,
            **pool_create_args)
        self.assertEqual(pool, resultant_pool)
        self.clients("neutron").create_pool.assert_called_once_with(
            expected_pool_data)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "neutron.create_pool")

    @ddt.data(
        {},
        {"vip_create_args": {}},
        {"vip_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test__create_v1_vip(self, vip_create_args=None):
        vip = {"vip": {"id": "vip-id"}}
        pool = {"pool": {"id": "pool-id", "subnet_id": "subnet-id"}}
        vip_create_args = vip_create_args or {}
        if vip_create_args.get("name") is None:
            self.scenario.generate_random_name = mock.Mock(
                return_value="random_name")
        self.clients("neutron").create_vip.return_value = vip
        args = {"protocol_port": 80, "protocol": "HTTP", "name": "random_name",
                "subnet_id": pool["pool"]["subnet_id"],
                "pool_id": pool["pool"]["id"]}
        args.update(vip_create_args)
        expected_vip_data = {"vip": args}
        resultant_vip = self.scenario._create_v1_vip(pool, **vip_create_args)
        self.assertEqual(vip, resultant_vip)
        self.clients("neutron").create_vip.assert_called_once_with(
            expected_vip_data)

    @ddt.data(
        {},
        {"floating_ip_args": {}},
        {"floating_ip_args": {"floating_ip_address": "1.0.0.1"}},
    )
    @ddt.unpack
    def test__create_floating_ip(self, floating_ip_args=None):
        floating_network = "floating"
        fip = {"floatingip": {"id": "fip-id"}}
        network_id = "net-id"
        floating_ip_args = floating_ip_args or {}
        self.clients("neutron").create_floatingip.return_value = fip
        mock_get_network_id = self.scenario._get_network_id = mock.Mock()
        mock_get_network_id.return_value = network_id
        args = {"floating_network_id": network_id,
                "description": "random_name"}
        args.update(floating_ip_args)
        expected_fip_data = {"floatingip": args}
        resultant_fip = self.scenario._create_floatingip(
            floating_network, **floating_ip_args)
        self.assertEqual(fip, resultant_fip)
        self.clients("neutron").create_floatingip.assert_called_once_with(
            expected_fip_data)
        mock_get_network_id.assert_called_once_with(floating_network)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_floating_ip")

    @mock.patch("%s.LOG.info" % NEUTRON_UTILS)
    def test__create_floating_ip_in_pre_newton_openstack(self, mock_log_info):
        floating_network = "floating"
        fip = {"floatingip": {"id": "fip-id"}}
        network_id = "net-id"
        self.clients("neutron").create_floatingip.return_value = fip
        mock_get_network_id = self.scenario._get_network_id = mock.Mock()
        mock_get_network_id.return_value = network_id

        from neutronclient.common import exceptions as n_exceptions
        e = n_exceptions.BadRequest("Unrecognized attribute(s) 'description'")
        self.clients("neutron").create_floatingip.side_effect = e

        a_e = self.assertRaises(n_exceptions.BadRequest,
                                self.scenario._create_floatingip,
                                floating_network)
        self.assertEqual(e, a_e)
        self.assertTrue(mock_log_info.called)

        expected_fip_data = {"floatingip": {"floating_network_id": network_id,
                                            "description": "random_name"}}
        self.clients("neutron").create_floatingip.assert_called_once_with(
            expected_fip_data)
        mock_get_network_id.assert_called_once_with(floating_network)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_floating_ip")

    @ddt.data(
        {},
        {"healthmonitor_create_args": {}},
        {"healthmonitor_create_args": {"type": "TCP"}},
    )
    @ddt.unpack
    def test__create_v1_healthmonitor(self,
                                      healthmonitor_create_args=None):
        hm = {"health_monitor": {"id": "hm-id"}}
        healthmonitor_create_args = healthmonitor_create_args or {}
        self.clients("neutron").create_health_monitor.return_value = hm
        args = {"type": "PING", "delay": 20,
                "timeout": 10, "max_retries": 3}
        args.update(healthmonitor_create_args)
        expected_hm_data = {"health_monitor": args}
        resultant_hm = self.scenario._create_v1_healthmonitor(
            **healthmonitor_create_args)
        self.assertEqual(hm, resultant_hm)
        self.clients("neutron").create_health_monitor.assert_called_once_with(
            expected_hm_data)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_healthmonitor")

    def test_list_v1_healthmonitors(self):
        hm_list = []
        hm_dict = {"health_monitors": hm_list}
        self.clients("neutron").list_health_monitors.return_value = hm_dict
        return_hm_dict = self.scenario._list_v1_healthmonitors()
        self.assertEqual(hm_dict, return_hm_dict)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_healthmonitors")

    def test_delete_v1_healthmonitor(self):
        healthmonitor = {"health_monitor": {"id": "fake-id"}}
        self.scenario._delete_v1_healthmonitor(healthmonitor["health_monitor"])
        self.clients("neutron").delete_health_monitor.assert_called_once_with(
            healthmonitor["health_monitor"]["id"])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_healthmonitor")

    def test_update_healthmonitor(self):
        expected_hm = {"health_monitor": {"admin_state_up": False}}
        mock_update = self.clients("neutron").update_health_monitor
        mock_update.return_value = expected_hm
        hm = {"health_monitor": {"id": "pool-id"}}
        healthmonitor_update_args = {"admin_state_up": False}
        result_hm = self.scenario._update_v1_healthmonitor(
            hm, **healthmonitor_update_args)
        self.assertEqual(expected_hm, result_hm)
        mock_update.assert_called_once_with(
            hm["health_monitor"]["id"], expected_hm)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_healthmonitor")

    def test_update_loadbalancer_resource(self):
        lb = {"id": "1", "provisioning_status": "READY"}
        new_lb = {"id": "1", "provisioning_status": "ACTIVE"}
        self.clients("neutron").show_loadbalancer.return_value = {
            "loadbalancer": new_lb}

        return_lb = self.scenario.update_loadbalancer_resource(lb)

        self.clients("neutron").show_loadbalancer.assert_called_once_with(
            lb["id"])
        self.assertEqual(new_lb, return_lb)

    def test_update_loadbalancer_resource_not_found(self):
        from neutronclient.common import exceptions as n_exceptions
        lb = {"id": "1", "provisioning_status": "READY"}
        self.clients("neutron").show_loadbalancer.side_effect = (
            n_exceptions.NotFound)

        self.assertRaises(exceptions.GetResourceNotFound,
                          self.scenario.update_loadbalancer_resource,
                          lb)
        self.clients("neutron").show_loadbalancer.assert_called_once_with(
            lb["id"])

    def test_update_loadbalancer_resource_failure(self):
        from neutronclient.common import exceptions as n_exceptions
        lb = {"id": "1", "provisioning_status": "READY"}
        self.clients("neutron").show_loadbalancer.side_effect = (
            n_exceptions.Forbidden)

        self.assertRaises(exceptions.GetResourceFailure,
                          self.scenario.update_loadbalancer_resource,
                          lb)
        self.clients("neutron").show_loadbalancer.assert_called_once_with(
            lb["id"])

    def test__create_lbaasv2_loadbalancer(self):
        neutronclient = self.clients("neutron")
        create_args = {"name": "s_rally", "vip_subnet_id": "1",
                       "fake": "fake"}
        new_lb = {"id": "1", "provisioning_status": "ACTIVE"}

        self.scenario.generate_random_name = mock.Mock(
            return_value="s_rally")
        self.mock_wait_for_status.mock.return_value = new_lb

        return_lb = self.scenario._create_lbaasv2_loadbalancer(
            "1", fake="fake")

        neutronclient.create_loadbalancer.assert_called_once_with(
            {"loadbalancer": create_args})
        self.assertEqual(new_lb, return_lb)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_lbaasv2_loadbalancer")

    def test__list_lbaasv2_loadbalancers(self):
        value = {"loadbalancer": [{"id": "1", "name": "s_rally"}]}
        self.clients("neutron").list_loadbalancers.return_value = value

        return_value = self.scenario._list_lbaasv2_loadbalancers(
            True, fake="fake")

        (self.clients("neutron").list_loadbalancers
         .assert_called_once_with(True, fake="fake"))
        self.assertEqual(value, return_value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_lbaasv2_loadbalancers")

    def test__create_bgpvpn(self, atomic_action=True):
        bv = {"bgpvpn": {"id": "bgpvpn-id"}}
        self.admin_clients("neutron").create_bgpvpn.return_value = bv
        self.scenario.generate_random_name = mock.Mock(
            return_value="random_name")
        expected_bv_data = {"bgpvpn": {"name": "random_name"}}
        resultant_bv = self.scenario._create_bgpvpn()
        self.assertEqual(bv, resultant_bv)
        self.admin_clients("neutron").create_bgpvpn.assert_called_once_with(
            expected_bv_data)
        if atomic_action:
            self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                           "neutron.create_bgpvpn")

    def test_delete_bgpvpn(self):
        bgpvpn_create_args = {}
        bgpvpn = self.scenario._create_bgpvpn(**bgpvpn_create_args)
        self.scenario._delete_bgpvpn(bgpvpn)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_bgpvpn")

    def test__list_bgpvpns(self):
        bgpvpns_list = []
        bgpvpns_dict = {"bgpvpns": bgpvpns_list}
        self.admin_clients("neutron").list_bgpvpns.return_value = bgpvpns_dict
        return_bgpvpns_list = self.scenario._list_bgpvpns()
        self.assertEqual(bgpvpns_list, return_bgpvpns_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_bgpvpns")

    @ddt.data(
        {},
        {"bgpvpn_update_args": {"update_name": True}},
        {"bgpvpn_update_args": {"update_name": False}},
    )
    @ddt.unpack
    def test__update_bgpvpn(self, bgpvpn_update_args=None):
        expected_bgpvpn = {"bgpvpn": {}}
        bgpvpn_update_data = bgpvpn_update_args or {}
        if bgpvpn_update_data.get("update_name"):
            expected_bgpvpn = {"bgpvpn": {"name": "updated_name"}}
        self.admin_clients(
            "neutron").update_bgpvpn.return_value = expected_bgpvpn
        self.scenario.generate_random_name = mock.Mock(
            return_value="updated_name")
        bgpvpn = {"bgpvpn": {"name": "bgpvpn-name", "id": "bgpvpn-id"}}
        result_bgpvpn = self.scenario._update_bgpvpn(bgpvpn,
                                                     **bgpvpn_update_data)
        self.admin_clients("neutron").update_bgpvpn.assert_called_once_with(
            bgpvpn["bgpvpn"]["id"], expected_bgpvpn)
        self.assertEqual(expected_bgpvpn, result_bgpvpn)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.update_bgpvpn")

    def test__create_bgpvpn_network_assoc(self):
        network_id = "network_id"
        bgpvpn_id = "bgpvpn_id"
        value = {"network_association": {
            "network_id": network_id,
            "id": bgpvpn_id}}
        self.clients(
            "neutron").create_bgpvpn_network_assoc.return_value = value
        network = {"id": network_id}
        bgpvpn = {"bgpvpn": {"id": bgpvpn_id}}
        return_value = self.scenario._create_bgpvpn_network_assoc(bgpvpn,
                                                                  network)
        netassoc = {"network_id": network["id"]}
        self.clients(
            "neutron").create_bgpvpn_network_assoc.assert_called_once_with(
            bgpvpn_id, {"network_association": netassoc})
        self.assertEqual(return_value, value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_bgpvpn_network_assoc")

    def test__create_router_network_assoc(self):
        router_id = "router_id"
        bgpvpn_id = "bgpvpn_id"
        value = {"router_association": {
            "router_id": router_id,
            "id": "asso_id"}}
        self.clients("neutron").create_bgpvpn_router_assoc.return_value = value
        router = {"id": router_id}
        bgpvpn = {"bgpvpn": {"id": bgpvpn_id}}
        return_value = self.scenario._create_bgpvpn_router_assoc(bgpvpn,
                                                                 router)
        router_assoc = {"router_id": router["id"]}
        self.clients(
            "neutron").create_bgpvpn_router_assoc.assert_called_once_with(
            bgpvpn_id, {"router_association": router_assoc})
        self.assertEqual(return_value, value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.create_bgpvpn_router_assoc")

    def test__delete_bgpvpn_network_assoc(self):
        bgpvpn_assoc_args = {}
        asso_id = "aaaa-bbbb"
        network_assoc = {"network_association": {"id": asso_id}}
        bgpvpn = self.scenario._create_bgpvpn(**bgpvpn_assoc_args)
        self.scenario._delete_bgpvpn_network_assoc(bgpvpn, network_assoc)
        self.clients(
            "neutron").delete_bgpvpn_network_assoc.assert_called_once_with(
            bgpvpn["bgpvpn"]["id"], asso_id)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_bgpvpn_network_assoc")

    def test__delete_bgpvpn_router_assoc(self):
        bgpvpn_assoc_args = {}
        asso_id = "aaaa-bbbb"
        router_assoc = {"router_association": {"id": asso_id}}
        bgpvpn = self.scenario._create_bgpvpn(**bgpvpn_assoc_args)
        self.scenario._delete_bgpvpn_router_assoc(bgpvpn, router_assoc)
        self.clients(
            "neutron").delete_bgpvpn_router_assoc.assert_called_once_with(
            bgpvpn["bgpvpn"]["id"], asso_id)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.delete_bgpvpn_router_assoc")

    def test__list_bgpvpn_network_assocs(self):
        value = {"network_associations": []}
        bgpvpn_id = "bgpvpn-id"
        bgpvpn = {"bgpvpn": {"id": bgpvpn_id}}
        self.clients("neutron").list_bgpvpn_network_assocs.return_value = value
        return_asso_list = self.scenario._list_bgpvpn_network_assocs(bgpvpn)
        self.clients(
            "neutron").list_bgpvpn_network_assocs.assert_called_once_with(
            bgpvpn_id)
        self.assertEqual(value, return_asso_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_bgpvpn_network_assocs")

    def test__list_bgpvpn_router_assocs(self):
        value = {"router_associations": []}
        bgpvpn_id = "bgpvpn-id"
        bgpvpn = {"bgpvpn": {"id": bgpvpn_id}}
        self.clients("neutron").list_bgpvpn_router_assocs.return_value = value
        return_asso_list = self.scenario._list_bgpvpn_router_assocs(bgpvpn)
        self.clients(
            "neutron").list_bgpvpn_router_assocs.assert_called_once_with(
            bgpvpn_id)
        self.assertEqual(value, return_asso_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "neutron.list_bgpvpn_router_assocs")


class NeutronScenarioFunctionalTestCase(test.FakeClientsScenarioTestCase):

    @mock.patch("%s.network_wrapper.generate_cidr" % NEUTRON_UTILS)
    def test_functional_create_network_and_subnets(self, mock_generate_cidr):
        scenario = utils.NeutronScenario(context=self.context)
        network_create_args = {}
        subnet_create_args = {}
        subnets_per_network = 5
        subnet_cidr_start = "1.1.1.0/24"

        cidrs = ["1.1.%d.0/24" % i for i in range(subnets_per_network)]
        cidrs_ = iter(cidrs)
        mock_generate_cidr.side_effect = lambda **kw: next(cidrs_)

        network, subnets = scenario._create_network_and_subnets(
            network_create_args,
            subnet_create_args,
            subnets_per_network,
            subnet_cidr_start)

        # This checks both data (cidrs seem to be enough) and subnets number
        result_cidrs = sorted([s["subnet"]["cidr"] for s in subnets])
        self.assertEqual(cidrs, result_cidrs)
