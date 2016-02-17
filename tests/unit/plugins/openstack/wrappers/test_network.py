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
from rally import exceptions
from rally.plugins.openstack.wrappers import network
from tests.unit import test

from neutronclient.common import exceptions as neutron_exceptions
from novaclient import exceptions as nova_exceptions

SVC = "rally.plugins.openstack.wrappers.network."


class Owner(utils.RandomNameGeneratorMixin):
    task = {"uuid": "task-uuid"}


class NovaNetworkWrapperTestCase(test.TestCase):

    class Net(object):
        def __init__(self, **kwargs):
            if "tenant_id" in kwargs:
                kwargs["project_id"] = kwargs.pop("tenant_id")
            self.__dict__.update(kwargs)

    def setUp(self):
        self.owner = Owner()
        self.owner.generate_random_name = mock.Mock()
        super(NovaNetworkWrapperTestCase, self).setUp()

    def get_wrapper(self, *skip_cidrs, **kwargs):
        mock_clients = mock.Mock()
        mock_clients.nova.return_value.networks.list.return_value = [
            self.Net(cidr=cidr) for cidr in skip_cidrs]
        return network.NovaNetworkWrapper(mock_clients, self.owner,
                                          config=kwargs)

    def test__init__(self):
        skip_cidrs = ["foo_cidr", "bar_cidr"]
        service = self.get_wrapper(*skip_cidrs)
        self.assertEqual(service.skip_cidrs, skip_cidrs)
        service.client.networks.list.assert_called_once_with()

    @mock.patch("rally.plugins.openstack.wrappers.network.generate_cidr")
    def test__generate_cidr(self, mock_generate_cidr):
        skip_cidrs = [5, 7]
        cidrs = iter(range(7))
        mock_generate_cidr.side_effect = (
            lambda start_cidr: start_cidr + next(cidrs)
        )
        service = self.get_wrapper(*skip_cidrs, start_cidr=3)
        self.assertEqual(service._generate_cidr(), 3)
        self.assertEqual(service._generate_cidr(), 4)
        self.assertEqual(service._generate_cidr(), 6)  # 5 is skipped
        self.assertEqual(service._generate_cidr(), 8)  # 7 is skipped
        self.assertEqual(service._generate_cidr(), 9)
        self.assertEqual(mock_generate_cidr.mock_calls,
                         [mock.call(start_cidr=3)] * 7)

    def test_create_network(self):
        service = self.get_wrapper()
        service.client.networks.create.side_effect = (
            lambda **kwargs: self.Net(id="foo_id", **kwargs))
        service._generate_cidr = mock.Mock(return_value="foo_cidr")
        net = service.create_network("foo_tenant",
                                     network_create_args={"fakearg": "fake"},
                                     bar="spam")
        self.assertEqual(net,
                         {"id": "foo_id",
                          "name": self.owner.generate_random_name.return_value,
                          "cidr": "foo_cidr",
                          "status": "ACTIVE",
                          "external": False,
                          "tenant_id": "foo_tenant"})
        service._generate_cidr.assert_called_once_with()
        service.client.networks.create.assert_called_once_with(
            project_id="foo_tenant", cidr="foo_cidr",
            label=self.owner.generate_random_name.return_value,
            fakearg="fake")

    def test_delete_network(self):
        service = self.get_wrapper()
        service.client.networks.delete.return_value = "foo_deleted"
        self.assertEqual(service.delete_network({"id": "foo_id"}),
                         "foo_deleted")
        service.client.networks.disassociate.assert_called_once_with(
            "foo_id", disassociate_host=False, disassociate_project=True)
        service.client.networks.delete.assert_called_once_with("foo_id")

    def test_list_networks(self):
        service = self.get_wrapper()
        service.client.networks.list.reset_mock()
        service.client.networks.list.return_value = [
            self.Net(id="foo_id", project_id="foo_tenant", cidr="foo_cidr",
                     label="foo_label"),
            self.Net(id="bar_id", project_id="bar_tenant", cidr="bar_cidr",
                     label="bar_label")]
        expected = [
            {"id": "foo_id", "cidr": "foo_cidr", "name": "foo_label",
             "status": "ACTIVE", "external": False, "tenant_id": "foo_tenant"},
            {"id": "bar_id", "cidr": "bar_cidr", "name": "bar_label",
             "status": "ACTIVE", "external": False, "tenant_id": "bar_tenant"}]
        self.assertEqual(expected, service.list_networks())
        service.client.networks.list.assert_called_once_with()

    def test__get_floating_ip(self):
        wrap = self.get_wrapper()
        wrap.client.floating_ips.get.return_value = mock.Mock(id="foo_id",
                                                              ip="foo_ip")
        fip = wrap._get_floating_ip("fip_id")
        wrap.client.floating_ips.get.assert_called_once_with("fip_id")
        self.assertEqual(fip, "foo_id")

        wrap.client.floating_ips.get.side_effect = (
            nova_exceptions.NotFound(""))
        self.assertIsNone(wrap._get_floating_ip("fip_id"))

        self.assertRaises(exceptions.GetResourceNotFound,
                          wrap._get_floating_ip, "fip_id", do_raise=True)

    def test_create_floating_ip(self):
        wrap = self.get_wrapper()
        wrap.client.floating_ips.create.return_value = mock.Mock(id="foo_id",
                                                                 ip="foo_ip")
        fip = wrap.create_floating_ip(ext_network="bar_net", bar="spam")
        self.assertEqual(fip, {"ip": "foo_ip", "id": "foo_id"})
        wrap.client.floating_ips.create.assert_called_once_with("bar_net")

        net = mock.Mock()
        net.name = "foo_net"
        wrap.client.floating_ip_pools.list.return_value = [net]
        fip = wrap.create_floating_ip()
        self.assertEqual(fip, {"ip": "foo_ip", "id": "foo_id"})
        wrap.client.floating_ips.create.assert_called_with("foo_net")

    def test_delete_floating_ip(self):
        wrap = self.get_wrapper()
        fip_found = iter(range(3))

        def get_fip(*args, **kwargs):
            for i in fip_found:
                return "fip_id"
            raise exceptions.GetResourceNotFound(resource="")
        wrap._get_floating_ip = mock.Mock(side_effect=get_fip)

        wrap.delete_floating_ip("fip_id")
        wrap.client.floating_ips.delete.assert_called_once_with("fip_id")
        self.assertFalse(wrap._get_floating_ip.called)

        wrap.delete_floating_ip("fip_id", wait=True)
        self.assertEqual(
            [mock.call("fip_id", do_raise=True)] * 4,
            wrap._get_floating_ip.mock_calls)

    def test_supports_extension(self):
        wrap = self.get_wrapper()
        self.assertFalse(wrap.supports_extension("extension")[0])
        self.assertTrue(wrap.supports_extension("security-group")[0])


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
        ports = ["foo_port", "bar_port"]
        service.client.list_dhcp_agent_hosting_networks.return_value = (
            {"agents": [{"id": agent_id} for agent_id in agents]})
        service.client.list_ports.return_value = (
            {"ports": [{"id": port_id} for port_id in ports]})
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
        self.assertEqual(
            service.client.remove_interface_router.mock_calls,
            [mock.call("foo_router", {"subnet_id": subnet_id})
             for subnet_id in subnets])
        self.assertEqual(service.client.delete_router.mock_calls,
                         [mock.call("foo_router")])
        self.assertEqual(service.client.delete_port.mock_calls,
                         [mock.call(port_id) for port_id in ports])
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
        fip = wrap.create_floating_ip(tenant_id="foo_tenant")
        self.assertEqual(fip, {"id": "fip_id", "ip": "fip_ip"})

        wrap.get_network = mock.Mock(
            return_value={"id": "foo_net", "external": True})
        wrap.create_floating_ip(tenant_id="foo_tenant", ext_network="ext_net")

        wrap.get_network = mock.Mock(
            return_value={"id": "foo_net", "external": False})
        wrap.create_floating_ip(tenant_id="foo_tenant")

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

        mock_clients.services.return_value = {"foo": "bar"}
        wrapper = network.wrap(mock_clients, owner, config)
        self.assertIsInstance(wrapper, network.NovaNetworkWrapper)
        self.assertEqual(wrapper.owner, owner)
        self.assertEqual(wrapper.config, config)
