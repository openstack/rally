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
import netaddr

from rally.plugins.openstack.context import network as network_context
from tests.unit import test

NET = "rally.plugins.openstack.wrappers.network."


class NetworkTestCase(test.TestCase):
    def get_context(self, **kwargs):
        return {"task": {"uuid": "foo_task"},
                "admin": {"endpoint": "foo_admin"},
                "config": {"network": kwargs},
                "tenants": {"foo_tenant": {"networks": [{"id": "foo_net"}]},
                            "bar_tenant": {"networks": [{"id": "bar_net"}]}}}

    def test_START_CIDR_DFLT(self):
        netaddr.IPNetwork(network_context.Network.DEFAULT_CONFIG["start_cidr"])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap", return_value="foo_service")
    def test__init__(self, mock_wrap, mock_clients):
        context = network_context.Network(self.get_context())
        self.assertEqual(context.net_wrapper, "foo_service")
        self.assertEqual(context.config["networks_per_tenant"], 1)
        self.assertEqual(context.config["start_cidr"],
                         network_context.Network.DEFAULT_CONFIG["start_cidr"])

        context = network_context.Network(
            self.get_context(start_cidr="foo_cidr", networks_per_tenant=42))
        self.assertEqual(context.net_wrapper, "foo_service")
        self.assertEqual(context.config["networks_per_tenant"], 42)
        self.assertEqual(context.config["start_cidr"], "foo_cidr")

    @mock.patch(NET + "wrap")
    @mock.patch("rally.plugins.openstack.context.network.utils")
    @mock.patch("rally.osclients.Clients")
    def test_setup(self, mock_clients, mock_utils, mock_wrap):
        mock_utils.iterate_per_tenants.return_value = [
            ("foo_user", "foo_tenant"),
            ("bar_user", "bar_tenant")]
        mock_create = mock.Mock(side_effect=lambda t, **kw: t + "-net")
        mock_wrap.return_value = mock.Mock(create_network=mock_create)
        nets_per_tenant = 2
        net_context = network_context.Network(
            self.get_context(networks_per_tenant=nets_per_tenant))
        net_context.setup()
        expected_networks = [["bar_tenant-net"] * nets_per_tenant,
                             ["foo_tenant-net"] * nets_per_tenant]
        actual_networks = []
        for tenant_id, tenant_ctx in (
                sorted(net_context.context["tenants"].items())):
            actual_networks.append(tenant_ctx["networks"])
        self.assertEqual(expected_networks, actual_networks)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap")
    def test_cleanup(self, mock_wrap, mock_osclients):
        net_context = network_context.Network(self.get_context())
        net_context.cleanup()
        mock_wrap().delete_network.assert_has_calls(
            [mock.call({"id": "foo_net"}), mock.call({"id": "bar_net"})],
            any_order=True)
