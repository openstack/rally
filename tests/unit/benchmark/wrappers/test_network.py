# Copyright 2014: Mirantis Inc.
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

from rally.benchmark.wrappers import network
from rally import consts
from tests.unit import test

SVC = "rally.benchmark.wrappers.network."


class NovaNetworkWrapperTestCase(test.TestCase):

    class Net(object):
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def get_wrapper(self, *skip_cidrs, **kwargs):
        mock_clients = mock.Mock()
        mock_clients.nova.return_value.networks.list.return_value = [
            self.Net(cidr=cidr) for cidr in skip_cidrs]
        return network.NovaNetworkWrapper(mock_clients, kwargs)

    def test__init__(self):
        skip_cidrs = ["foo_cidr", "bar_cidr"]
        service = self.get_wrapper(*skip_cidrs)
        self.assertEqual(service.skip_cidrs, skip_cidrs)
        service.client.networks.list.assert_called_once_with()

    @mock.patch("rally.benchmark.wrappers.network.generate_cidr")
    def test__generate_cidr(self, mock_cidr):
        skip_cidrs = [5, 7]
        cidrs = iter(range(7))
        mock_cidr.side_effect = lambda start_cidr: start_cidr + cidrs.next()
        service = self.get_wrapper(*skip_cidrs, start_cidr=3)
        self.assertEqual(service._generate_cidr(), 3)
        self.assertEqual(service._generate_cidr(), 4)
        self.assertEqual(service._generate_cidr(), 6)  # 5 is skipped
        self.assertEqual(service._generate_cidr(), 8)  # 7 is skipped
        self.assertEqual(service._generate_cidr(), 9)
        self.assertEqual(mock_cidr.mock_calls, [mock.call(start_cidr=3)] * 7)

    @mock.patch("rally.common.utils.generate_random_name",
                return_value="foo_name")
    def test_create_network(self, mock_name):
        service = self.get_wrapper()
        service.client.networks.create.side_effect = (
            lambda **kwargs: self.Net(id="foo_id", **kwargs))
        service._generate_cidr = mock.Mock(return_value="foo_cidr")
        net = service.create_network("foo_tenant", bar="spam")
        self.assertEqual(net, {"id": "foo_id",
                               "name": "foo_name",
                               "cidr": "foo_cidr",
                               "status": "ACTIVE",
                               "external": False,
                               "tenant_id": "foo_tenant"})
        mock_name.assert_called_once_with("rally_ctx_net_")
        service._generate_cidr.assert_called_once_with()
        service.client.networks.create.assert_called_once_with(
            tenant_id="foo_tenant", cidr="foo_cidr", label="foo_name")

    def test_delete_network(self):
        service = self.get_wrapper()
        service.client.networks.delete.return_value = "foo_deleted"
        self.assertEqual(service.delete_network({"id": "foo_id"}),
                         "foo_deleted")
        service.client.networks.delete.assert_called_once_with("foo_id")

    def test_list_networks(self):
        service = self.get_wrapper()
        service.client.networks.list.return_value = "foo_list"
        service.client.networks.list.reset_mock()
        self.assertEqual(service.list_networks(), "foo_list")
        service.client.networks.list.assert_called_once_with()


class NeutronWrapperTestCase(test.TestCase):
    def get_wrapper(self, *skip_cidrs, **kwargs):
        return network.NeutronWrapper(mock.Mock(), kwargs)

    def test_SUBNET_IP_VERSION(self):
        self.assertEqual(network.NeutronWrapper.SUBNET_IP_VERSION, 4)

    @mock.patch("rally.benchmark.wrappers.network.generate_cidr")
    def test__generate_cidr(self, mock_cidr):
        cidrs = iter(range(5))
        mock_cidr.side_effect = lambda start_cidr: start_cidr + cidrs.next()
        service = self.get_wrapper(start_cidr=3)
        self.assertEqual(service._generate_cidr(), 3)
        self.assertEqual(service._generate_cidr(), 4)
        self.assertEqual(service._generate_cidr(), 5)
        self.assertEqual(service._generate_cidr(), 6)
        self.assertEqual(service._generate_cidr(), 7)
        self.assertEqual(mock_cidr.mock_calls, [mock.call(start_cidr=3)] * 5)

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_network(self, mock_name):
        mock_name.return_value = "foo_name"
        service = self.get_wrapper()
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": "foo_name",
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant")
        mock_name.assert_called_once_with("rally_ctx_net_")
        service.client.create_network.assert_called_once_with({
            "network": {"tenant_id": "foo_tenant", "name": "foo_name"}})
        self.assertEqual(net, {"id": "foo_id",
                               "name": "foo_name",
                               "status": "foo_status",
                               "external": False,
                               "tenant_id": "foo_tenant",
                               "router_id": None,
                               "subnets": []})

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_network_with_subnets(self, mock_name):
        subnets_num = 4
        mock_name.return_value = "foo_name"
        service = self.get_wrapper()
        subnets_cidrs = iter(range(subnets_num))
        subnets_ids = iter(range(subnets_num))
        service._generate_cidr = mock.Mock(
            side_effect=lambda: "cidr-%d" % subnets_cidrs.next())
        service.client.create_subnet = mock.Mock(
            side_effect=lambda i: {
                "subnet": {"id": "subnet-%d" % subnets_ids.next()}})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": "foo_name",
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant", subnets_num=subnets_num)
        service.client.create_network.assert_called_once_with({
            "network": {"tenant_id": "foo_tenant", "name": "foo_name"}})
        self.assertEqual(net, {"id": "foo_id",
                               "name": "foo_name",
                               "status": "foo_status",
                               "external": False,
                               "router_id": None,
                               "tenant_id": "foo_tenant",
                               "subnets": ["subnet-%d" % i
                                           for i in range(subnets_num)]})
        self.assertEqual(
            service.client.create_subnet.mock_calls,
            [mock.call({"subnet": {"name": "foo_name",
                                   "enable_dhcp": True,
                                   "network_id": "foo_id",
                                   "tenant_id": "foo_tenant",
                                   "ip_version": service.SUBNET_IP_VERSION,
                                   "cidr": "cidr-%d" % i}})
             for i in range(subnets_num)])

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_network_with_router(self, mock_name):
        mock_name.return_value = "foo_name"
        service = self.get_wrapper()
        service.list_networks = mock.Mock(return_value=[])
        service.client.create_router = mock.Mock(
            return_value={"router": {"id": "foo_router"}})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": "foo_name",
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant", add_router=True)
        self.assertEqual(net, {"id": "foo_id",
                               "name": "foo_name",
                               "status": "foo_status",
                               "external": False,
                               "tenant_id": "foo_tenant",
                               "router_id": "foo_router",
                               "subnets": []})
        service.client.create_router.assert_called_once_with(
            {"router": {"tenant_id": "foo_tenant", "name": "foo_name"}})

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_network_with_router_external(self, mock_name):
        mock_name.return_value = "foo_name"
        service = self.get_wrapper()
        service.list_networks = mock.Mock(
            return_value=[{"router:external": True, "id": "bar_id"}])
        service.client.create_router = mock.Mock(
            return_value={"router": {"id": "foo_router"}})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": "foo_name",
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant", add_router=True)
        self.assertEqual(net, {"id": "foo_id",
                               "name": "foo_name",
                               "status": "foo_status",
                               "external": False,
                               "tenant_id": "foo_tenant",
                               "router_id": "foo_router",
                               "subnets": []})
        service.client.create_router.assert_called_once_with(
            {"router": {"tenant_id": "foo_tenant", "name": "foo_name",
                        "external_gateway_info": {"network_id": "bar_id",
                                                  "enable_snat": True}}})

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_network_with_router_and_subnets(self, mock_name):
        subnets_num = 4
        mock_name.return_value = "foo_name"
        service = self.get_wrapper()
        service._generate_cidr = mock.Mock(return_value="foo_cidr")
        service.list_networks = mock.Mock(return_value=[])
        service.client.create_subnet = mock.Mock(
            return_value={"subnet": {"id": "foo_subnet"}})
        service.client.create_router = mock.Mock(
            return_value={"router": {"id": "foo_router"}})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": "foo_name",
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant", add_router=True,
                                     subnets_num=subnets_num)
        self.assertEqual(net, {"id": "foo_id",
                               "name": "foo_name",
                               "status": "foo_status",
                               "external": False,
                               "tenant_id": "foo_tenant",
                               "router_id": "foo_router",
                               "subnets": ["foo_subnet"] * subnets_num})
        service.client.create_router.assert_called_once_with(
            {"router": {"tenant_id": "foo_tenant", "name": "foo_name"}})
        self.assertEqual(
            service.client.create_subnet.mock_calls,
            [mock.call({"subnet": {"name": "foo_name",
                                   "enable_dhcp": True,
                                   "network_id": "foo_id",
                                   "tenant_id": "foo_tenant",
                                   "ip_version": service.SUBNET_IP_VERSION,
                                   "cidr": "foo_cidr"}})] * subnets_num)
        self.assertEqual(service.client.add_interface_router.mock_calls,
                         [mock.call("foo_router", {"subnet_id": "foo_subnet"})
                          for i in range(subnets_num)])

    def test_delete_network(self):
        service = self.get_wrapper()
        service.client.list_dhcp_agent_hosting_networks.return_value = (
            {"agents": []})
        service.client.delete_network.return_value = "foo_deleted"
        result = service.delete_network({"id": "foo_id", "router_id": None,
                                         "subnets": []})
        self.assertEqual(result, "foo_deleted")
        self.assertEqual(
            service.client.remove_network_from_dhcp_agent.mock_calls, [])
        self.assertEqual(service.client.remove_gateway_router.mock_calls, [])
        self.assertEqual(
            service.client.remove_interface_router.mock_calls, [])
        self.assertEqual(service.client.delete_router.mock_calls, [])
        self.assertEqual(service.client.delete_subnet.mock_calls, [])
        service.client.delete_network.assert_called_once_with("foo_id")

    def test_delete_network_with_dhcp_and_router_and_subnets(self):
        service = self.get_wrapper()
        agents = ["foo_agent", "bar_agent"]
        subnets = ["foo_subnet", "bar_subnet"]
        service.client.list_dhcp_agent_hosting_networks.return_value = (
            {"agents": [{"id": agent_id} for agent_id in agents]})
        service.client.delete_network.return_value = "foo_deleted"
        result = service.delete_network(
            {"id": "foo_id", "router_id": "foo_router", "subnets": subnets})
        self.assertEqual(result, "foo_deleted")
        self.assertEqual(
            service.client.remove_network_from_dhcp_agent.mock_calls,
            [mock.call(agent_id, "foo_id") for agent_id in agents])
        self.assertEqual(service.client.remove_gateway_router.mock_calls,
                         [mock.call("foo_router")])
        self.assertEqual(
            service.client.remove_interface_router.mock_calls,
            [mock.call("foo_router", {"subnet_id": subnet_id})
             for subnet_id in subnets])
        self.assertEqual(service.client.delete_router.mock_calls,
                         [mock.call("foo_router")])
        self.assertEqual(service.client.delete_subnet.mock_calls,
                         [mock.call(subnet_id) for subnet_id in subnets])
        service.client.delete_network.assert_called_once_with("foo_id")

    def test_list_networks(self):
        service = self.get_wrapper()
        service.client.list_networks.return_value = {"networks": "foo_nets"}
        self.assertEqual(service.list_networks(), "foo_nets")
        service.client.list_networks.assert_called_once_with()


class FunctionsTestCase(test.TestCase):

    def test_generate_cidr(self):
        with mock.patch("rally.benchmark.wrappers.network.cidr_incr",
                        iter(range(1, 4))):
            self.assertEqual(network.generate_cidr(), "1.1.0.64/26")
            self.assertEqual(network.generate_cidr(), "1.1.0.128/26")
            self.assertEqual(network.generate_cidr(), "1.1.0.192/26")

        with mock.patch("rally.benchmark.wrappers.network.cidr_incr",
                        iter(range(1, 4))):
            start_cidr = "1.1.0.0/24"
            self.assertEqual(network.generate_cidr(start_cidr), "1.1.1.0/24")
            self.assertEqual(network.generate_cidr(start_cidr), "1.1.2.0/24")
            self.assertEqual(network.generate_cidr(start_cidr), "1.1.3.0/24")

    def test_wrap(self):
        mock_clients = mock.Mock()
        mock_clients.nova().networks.list.return_value = []

        mock_clients.services.return_value = {"foo": consts.Service.NEUTRON}
        self.assertIsInstance(network.wrap(mock_clients, {}),
                              network.NeutronWrapper)

        mock_clients.services.return_value = {"foo": "bar"}
        self.assertIsInstance(network.wrap(mock_clients, {}),
                              network.NovaNetworkWrapper)
