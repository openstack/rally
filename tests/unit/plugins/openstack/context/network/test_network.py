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

import ddt
import mock
import netaddr

from rally.plugins.openstack.context.network import networks as network_context
from tests.unit import test

NET = "rally.plugins.openstack.wrappers.network."


@ddt.ddt
class NetworkTestCase(test.TestCase):
    def get_context(self, **kwargs):
        return {"task": {"uuid": "foo_task"},
                "admin": {"credential": "foo_admin"},
                "config": {"network": kwargs},
                "users": [{"id": "foo_user", "tenant_id": "foo_tenant"},
                          {"id": "bar_user", "tenant_id": "bar_tenant"}],
                "tenants": {"foo_tenant": {"networks": [{"id": "foo_net"}]},
                            "bar_tenant": {"networks": [{"id": "bar_net"}]}}}

    def test_START_CIDR_DFLT(self):
        netaddr.IPNetwork(network_context.Network.DEFAULT_CONFIG["start_cidr"])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap", return_value="foo_service")
    def test__init__default(self, mock_wrap, mock_clients):
        context = network_context.Network(self.get_context())
        self.assertEqual(context.config["networks_per_tenant"], 1)
        self.assertEqual(context.config["start_cidr"],
                         network_context.Network.DEFAULT_CONFIG["start_cidr"])
        self.assertIsNone(context.config["dns_nameservers"])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap", return_value="foo_service")
    def test__init__explicit(self, mock_wrap, mock_clients):
        context = network_context.Network(
            self.get_context(start_cidr="foo_cidr", networks_per_tenant=42,
                             network_create_args={"fakearg": "fake"},
                             dns_nameservers=["1.2.3.4", "5.6.7.8"]))
        self.assertEqual(context.config["networks_per_tenant"], 42)
        self.assertEqual(context.config["start_cidr"], "foo_cidr")
        self.assertDictEqual(context.config["network_create_args"],
                             {"fakearg": "fake"})
        self.assertEqual(context.config["dns_nameservers"],
                         ("1.2.3.4", "5.6.7.8"))

    @ddt.data({},
              {"dns_nameservers": []},
              {"dns_nameservers": ["1.2.3.4", "5.6.7.8"]})
    @ddt.unpack
    @mock.patch(NET + "wrap")
    @mock.patch("rally.plugins.openstack.context.network.networks.utils")
    @mock.patch("rally.osclients.Clients")
    def test_setup(self, mock_clients, mock_utils, mock_wrap, **dns_kwargs):
        mock_utils.iterate_per_tenants.return_value = [
            ("foo_user", "foo_tenant"),
            ("bar_user", "bar_tenant")]
        mock_create = mock.Mock(side_effect=lambda t, **kw: t + "-net")
        mock_utils.generate_random_name = mock.Mock()
        mock_wrap.return_value = mock.Mock(create_network=mock_create)
        nets_per_tenant = 2
        net_context = network_context.Network(
            self.get_context(networks_per_tenant=nets_per_tenant,
                             network_create_args={"fakearg": "fake"},
                             **dns_kwargs))

        net_context.setup()

        if "dns_nameservers" in dns_kwargs:
            dns_kwargs["dns_nameservers"] = tuple(
                dns_kwargs["dns_nameservers"])
        create_calls = [
            mock.call(tenant, add_router=True,
                      subnets_num=1, network_create_args={"fakearg": "fake"},
                      **dns_kwargs)
            for user, tenant in mock_utils.iterate_per_tenants.return_value]
        mock_create.assert_has_calls(create_calls)

        mock_utils.iterate_per_tenants.assert_called_once_with(
            net_context.context["users"])
        expected_networks = ["bar_tenant-net",
                             "foo_tenant-net"] * nets_per_tenant
        actual_networks = []
        for tenant_id, tenant_ctx in net_context.context["tenants"].items():
            actual_networks.extend(tenant_ctx["networks"])
        self.assertSequenceEqual(sorted(expected_networks),
                                 sorted(actual_networks))

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap")
    def test_cleanup(self, mock_wrap, mock_clients):
        net_context = network_context.Network(self.get_context())
        net_context.cleanup()
        mock_wrap().delete_network.assert_has_calls(
            [mock.call({"id": "foo_net"}), mock.call({"id": "bar_net"})],
            any_order=True)
