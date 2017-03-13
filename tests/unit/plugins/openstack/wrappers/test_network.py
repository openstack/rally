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

from rally.common import utils
from rally import consts
from rally.plugins.openstack.wrappers import network
from tests.unit import test

from neutronclient.common import exceptions as neutron_exceptions

SVC = "rally.plugins.openstack.wrappers.network."


class Owner(utils.RandomNameGeneratorMixin):
    task = {"uuid": "task-uuid"}


class NeutronWrapperTestCase(test.TestCase):
    def setUp(self):
        self.owner = Owner()
        self.owner.generate_random_name = mock.Mock()
        super(NeutronWrapperTestCase, self).setUp()

    def get_wrapper(self, *skip_cidrs, **kwargs):
        return network.NeutronWrapper(mock.Mock(), self.owner, config=kwargs)

    def test_SUBNET_IP_VERSION(self):
        self.assertEqual(network.NeutronWrapper.SUBNET_IP_VERSION, 4)

    @mock.patch("rally.plugins.openstack.wrappers.network.generate_cidr")
    def test__generate_cidr(self, mock_generate_cidr):
        cidrs = iter(range(5))
        mock_generate_cidr.side_effect = (
            lambda start_cidr: start_cidr + next(cidrs)
        )
        service = self.get_wrapper(start_cidr=3)
        self.assertEqual(service._generate_cidr(), 3)
        self.assertEqual(service._generate_cidr(), 4)
        self.assertEqual(service._generate_cidr(), 5)
        self.assertEqual(service._generate_cidr(), 6)
        self.assertEqual(service._generate_cidr(), 7)
        self.assertEqual(mock_generate_cidr.mock_calls,
                         [mock.call(start_cidr=3)] * 5)

    def test_external_networks(self):
        wrap = self.get_wrapper()
        wrap.client.list_networks.return_value = {"networks": "foo_networks"}
        self.assertEqual(wrap.external_networks, "foo_networks")
        wrap.client.list_networks.assert_called_once_with(
            **{"router:external": True})

    def test_get_network(self):
        wrap = self.get_wrapper()
        neutron_net = {"id": "foo_id",
                       "name": self.owner.generate_random_name.return_value,
                       "tenant_id": "foo_tenant",
                       "status": "foo_status",
                       "router:external": "foo_external",
                       "subnets": "foo_subnets"}
        expected_net = {"id": "foo_id",
                        "name": self.owner.generate_random_name.return_value,
                        "tenant_id": "foo_tenant",
                        "status": "foo_status",
                        "external": "foo_external",
                        "router_id": None,
                        "subnets": "foo_subnets"}
        wrap.client.show_network.return_value = {"network": neutron_net}
        net = wrap.get_network(net_id="foo_id")
        self.assertEqual(net, expected_net)
        wrap.client.show_network.assert_called_once_with("foo_id")

        wrap.client.show_network.side_effect = (
            neutron_exceptions.NeutronClientException)
        self.assertRaises(network.NetworkWrapperException, wrap.get_network,
                          net_id="foo_id")

        wrap.client.list_networks.return_value = {"networks": [neutron_net]}
        net = wrap.get_network(name="foo_name")
        self.assertEqual(net, expected_net)
        wrap.client.list_networks.assert_called_once_with(name="foo_name")

        wrap.client.list_networks.return_value = {"networks": []}
        self.assertRaises(network.NetworkWrapperException, wrap.get_network,
                          name="foo_name")

    def test_create_v1_pool(self):
        subnet = "subnet_id"
        tenant = "foo_tenant"
        service = self.get_wrapper()
        expected_pool = {"pool": {
            "id": "pool_id",
            "name": self.owner.generate_random_name.return_value,
            "subnet_id": subnet,
            "tenant_id": tenant}}
        service.client.create_pool.return_value = expected_pool
        resultant_pool = service.create_v1_pool(tenant, subnet)
        service.client.create_pool.assert_called_once_with({
            "pool": {"lb_method": "ROUND_ROBIN",
                     "subnet_id": subnet,
                     "tenant_id": tenant,
                     "protocol": "HTTP",
                     "name": self.owner.generate_random_name.return_value}})
        self.assertEqual(resultant_pool, expected_pool)

    def test_create_network(self):
        service = self.get_wrapper()
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": self.owner.generate_random_name.return_value,
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant")
        service.client.create_network.assert_called_once_with({
            "network": {"tenant_id": "foo_tenant",
                        "name": self.owner.generate_random_name.return_value}})
        self.assertEqual(net,
                         {"id": "foo_id",
                          "name": self.owner.generate_random_name.return_value,
                          "status": "foo_status",
                          "external": False,
                          "tenant_id": "foo_tenant",
                          "router_id": None,
                          "subnets": []})

    def test_create_network_with_subnets(self):
        subnets_num = 4
        service = self.get_wrapper()
        subnets_cidrs = iter(range(subnets_num))
        subnets_ids = iter(range(subnets_num))
        service._generate_cidr = mock.Mock(
            side_effect=lambda: "cidr-%d" % next(subnets_cidrs))
        service.client.create_subnet = mock.Mock(
            side_effect=lambda i: {
                "subnet": {"id": "subnet-%d" % next(subnets_ids)}})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": self.owner.generate_random_name.return_value,
                        "status": "foo_status"}}

        net = service.create_network("foo_tenant", subnets_num=subnets_num)

        service.client.create_network.assert_called_once_with({
            "network": {"tenant_id": "foo_tenant",
                        "name": self.owner.generate_random_name.return_value}})
        self.assertEqual(net,
                         {"id": "foo_id",
                          "name": self.owner.generate_random_name.return_value,
                          "status": "foo_status",
                          "external": False,
                          "router_id": None,
                          "tenant_id": "foo_tenant",
                          "subnets": ["subnet-%d" % i
                                      for i in range(subnets_num)]})
        self.assertEqual(
            service.client.create_subnet.mock_calls,
            [mock.call({"subnet":
                        {"name": self.owner.generate_random_name.return_value,
                         "enable_dhcp": True,
                         "network_id": "foo_id",
                         "tenant_id": "foo_tenant",
                         "ip_version": service.SUBNET_IP_VERSION,
                         "dns_nameservers": ["8.8.8.8", "8.8.4.4"],
                         "cidr": "cidr-%d" % i}})
             for i in range(subnets_num)])

    def test_create_network_with_router(self):
        service = self.get_wrapper()
        service.create_router = mock.Mock(return_value={"id": "foo_router"})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": self.owner.generate_random_name.return_value,
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant", add_router=True)
        self.assertEqual(net,
                         {"id": "foo_id",
                          "name": self.owner.generate_random_name.return_value,
                          "status": "foo_status",
                          "external": False,
                          "tenant_id": "foo_tenant",
                          "router_id": "foo_router",
                          "subnets": []})
        service.create_router.assert_called_once_with(external=True,
                                                      tenant_id="foo_tenant")

    def test_create_network_with_router_and_subnets(self):
        subnets_num = 4
        service = self.get_wrapper()
        service._generate_cidr = mock.Mock(return_value="foo_cidr")
        service.create_router = mock.Mock(return_value={"id": "foo_router"})
        service.client.create_subnet = mock.Mock(
            return_value={"subnet": {"id": "foo_subnet"}})
        service.client.create_network.return_value = {
            "network": {"id": "foo_id",
                        "name": self.owner.generate_random_name.return_value,
                        "status": "foo_status"}}
        net = service.create_network("foo_tenant", add_router=True,
                                     subnets_num=subnets_num,
                                     dns_nameservers=["foo_nameservers"])
        self.assertEqual(net,
                         {"id": "foo_id",
                          "name": self.owner.generate_random_name.return_value,
                          "status": "foo_status",
                          "external": False,
                          "tenant_id": "foo_tenant",
                          "router_id": "foo_router",
                          "subnets": ["foo_subnet"] * subnets_num})
        service.create_router.assert_called_once_with(external=True,
                                                      tenant_id="foo_tenant")
        self.assertEqual(
            service.client.create_subnet.mock_calls,
            [mock.call({"subnet":
                        {"name": self.owner.generate_random_name.return_value,
                         "enable_dhcp": True,
                         "network_id": "foo_id",
                         "tenant_id": "foo_tenant",
                         "ip_version": service.SUBNET_IP_VERSION,
                         "dns_nameservers": ["foo_nameservers"],
                         "cidr": "foo_cidr"}})] * subnets_num)
        self.assertEqual(service.client.add_interface_router.mock_calls,
                         [mock.call("foo_router", {"subnet_id": "foo_subnet"})
                          for i in range(subnets_num)])

    @mock.patch("rally.plugins.openstack.wrappers.network.NeutronWrapper"
                ".supports_extension", return_value=(False, ""))
    def test_delete_network(self, mock_neutron_wrapper_supports_extension):
        service = self.get_wrapper()
        service.client.list_ports.return_value = {"ports": []}
        service.client.delete_network.return_value = "foo_deleted"
        result = service.delete_network({"id": "foo_id", "router_id": None,
                                         "subnets": []})
        self.assertEqual(result, "foo_deleted")
        self.assertEqual(service.client.remove_gateway_router.mock_calls, [])
        self.assertEqual(
            service.client.remove_interface_router.mock_calls, [])
        self.assertEqual(service.client.delete_router.mock_calls, [])
        self.assertEqual(service.client.delete_subnet.mock_calls, [])
        service.client.delete_network.assert_called_once_with("foo_id")

    def test_delete_v1_pool(self):
        service = self.get_wrapper()
        pool = {"pool": {"id": "pool-id"}}
        service.delete_v1_pool(pool["pool"]["id"])
        service.client.delete_pool.assert_called_once_with("pool-id")

    @mock.patch("rally.plugins.openstack.wrappers.network.NeutronWrapper"
                ".supports_extension", return_value=(True, ""))
    def test_delete_network_with_dhcp_and_router_and_ports_and_subnets(
            self, mock_neutron_wrapper_supports_extension):

        service = self.get_wrapper()
        agents = ["foo_agent", "bar_agent"]
        subnets = ["foo_subnet", "bar_subnet"]
        ports = [{"id": "foo_port", "device_owner": "network:router_interface",
                  "device_id": "rounttter"},
                 {"id": "bar_port", "device_owner": "network:dhcp"}]
        service.client.list_dhcp_agent_hosting_networks.return_value = (
            {"agents": [{"id": agent_id} for agent_id in agents]})
        service.client.list_ports.return_value = ({"ports": ports})
        service.client.delete_network.return_value = "foo_deleted"

        result = service.delete_network(
            {"id": "foo_id", "router_id": "foo_router", "subnets": subnets,
             "lb_pools": []})

        self.assertEqual(result, "foo_deleted")
        self.assertEqual(
            service.client.remove_network_from_dhcp_agent.mock_calls,
            [mock.call(agent_id, "foo_id") for agent_id in agents])
        self.assertEqual(service.client.remove_gateway_router.mock_calls,
                         [mock.call("foo_router")])
        service.client.delete_port.assert_called_once_with(ports[1]["id"])
        service.client.remove_interface_router.assert_called_once_with(
            ports[0]["device_id"], {"port_id": ports[0]["id"]})
        self.assertEqual(service.client.delete_subnet.mock_calls,
                         [mock.call(subnet_id) for subnet_id in subnets])
        service.client.delete_network.assert_called_once_with("foo_id")

        mock_neutron_wrapper_supports_extension.assert_called_once_with(
            "dhcp_agent_scheduler")

    def test_list_networks(self):
        service = self.get_wrapper()
        service.client.list_networks.return_value = {"networks": "foo_nets"}
        self.assertEqual(service.list_networks(), "foo_nets")
        service.client.list_networks.assert_called_once_with()

    @mock.patch(SVC + "NeutronWrapper.external_networks")
    def test_create_floating_ip(self, mock_neutron_wrapper_external_networks):
        wrap = self.get_wrapper()
        wrap.create_port = mock.Mock(return_value={"id": "port_id"})
        wrap.client.create_floatingip = mock.Mock(
            return_value={"floatingip": {"id": "fip_id",
                                         "floating_ip_address": "fip_ip"}})

        self.assertRaises(ValueError, wrap.create_floating_ip)

        mock_neutron_wrapper_external_networks.__get__ = lambda *args: []
        self.assertRaises(network.NetworkWrapperException,
                          wrap.create_floating_ip, tenant_id="foo_tenant")

        mock_neutron_wrapper_external_networks.__get__ = (
            lambda *args: [{"id": "ext_id"}]
        )
        fip = wrap.create_floating_ip(tenant_id="foo_tenant",
                                      port_id="port_id")
        self.assertEqual(fip, {"id": "fip_id", "ip": "fip_ip"})

        wrap.get_network = mock.Mock(
            return_value={"id": "foo_net", "external": True})
        wrap.create_floating_ip(tenant_id="foo_tenant", ext_network="ext_net",
                                port_id="port_id")

        wrap.get_network = mock.Mock(
            return_value={"id": "foo_net", "external": False})
        wrap.create_floating_ip(tenant_id="foo_tenant", port_id="port_id")

        self.assertRaises(network.NetworkWrapperException,
                          wrap.create_floating_ip, tenant_id="foo_tenant",
                          ext_network="ext_net")

    def test_delete_floating_ip(self):
        wrap = self.get_wrapper()
        wrap.delete_floating_ip("fip_id")
        wrap.delete_floating_ip("fip_id", ignored_kwarg="bar")
        self.assertEqual(wrap.client.delete_floatingip.mock_calls,
                         [mock.call("fip_id")] * 2)

    @mock.patch(SVC + "NeutronWrapper.external_networks")
    def test_create_router(self, mock_neutron_wrapper_external_networks):
        wrap = self.get_wrapper()
        wrap.client.create_router.return_value = {"router": "foo_router"}
        mock_neutron_wrapper_external_networks.__get__ = (
            lambda *args: [{"id": "ext_id"}]
        )

        router = wrap.create_router()
        wrap.client.create_router.assert_called_once_with(
            {"router": {"name": self.owner.generate_random_name.return_value}})
        self.assertEqual(router, "foo_router")

        router = wrap.create_router(external=True, foo="bar")
        wrap.client.create_router.assert_called_with(
            {"router": {"name": self.owner.generate_random_name.return_value,
                        "external_gateway_info": {
                            "network_id": "ext_id",
                            "enable_snat": True},
                        "foo": "bar"}})

    def test_create_port(self):
        wrap = self.get_wrapper()
        wrap.client.create_port.return_value = {"port": "foo_port"}

        port = wrap.create_port("foo_net")
        wrap.client.create_port.assert_called_once_with(
            {"port": {"network_id": "foo_net",
                      "name": self.owner.generate_random_name.return_value}})
        self.assertEqual(port, "foo_port")

        port = wrap.create_port("foo_net", foo="bar")
        wrap.client.create_port.assert_called_with(
            {"port": {"network_id": "foo_net",
                      "name": self.owner.generate_random_name.return_value,
                      "foo": "bar"}})

    def test_supports_extension(self):
        wrap = self.get_wrapper()
        wrap.client.list_extensions.return_value = (
            {"extensions": [{"alias": "extension"}]})
        self.assertTrue(wrap.supports_extension("extension")[0])

        wrap.client.list_extensions.return_value = (
            {"extensions": [{"alias": "extension"}]})
        self.assertFalse(wrap.supports_extension("dummy-group")[0])

        wrap.client.list_extensions.return_value = {}
        self.assertFalse(wrap.supports_extension("extension")[0])


class FunctionsTestCase(test.TestCase):

    def test_generate_cidr(self):
        with mock.patch("rally.plugins.openstack.wrappers.network.cidr_incr",
                        iter(range(1, 4))):
            self.assertEqual(network.generate_cidr(), "10.2.1.0/24")
            self.assertEqual(network.generate_cidr(), "10.2.2.0/24")
            self.assertEqual(network.generate_cidr(), "10.2.3.0/24")

        with mock.patch("rally.plugins.openstack.wrappers.network.cidr_incr",
                        iter(range(1, 4))):
            start_cidr = "1.1.0.0/26"
            self.assertEqual(network.generate_cidr(start_cidr), "1.1.0.64/26")
            self.assertEqual(network.generate_cidr(start_cidr), "1.1.0.128/26")
            self.assertEqual(network.generate_cidr(start_cidr), "1.1.0.192/26")

    def test_wrap(self):
        mock_clients = mock.Mock()
        mock_clients.nova().networks.list.return_value = []
        config = {"fakearg": "fake"}
        owner = Owner()

        mock_clients.services.return_value = {"foo": consts.Service.NEUTRON}
        wrapper = network.wrap(mock_clients, owner, config)
        self.assertIsInstance(wrapper, network.NeutronWrapper)
        self.assertEqual(wrapper.owner, owner)
        self.assertEqual(wrapper.config, config)
