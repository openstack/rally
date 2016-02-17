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

from rally.plugins.openstack.context.neutron import lbaas as lbaas_context
from tests.unit import test

NET = "rally.plugins.openstack.wrappers.network."


class LbaasTestCase(test.TestCase):
    def get_context(self, **kwargs):
        foo_tenant = {"networks": [{"id": "foo_net",
                                    "tenant_id": "foo_tenant",
                                    "subnets": ["foo_subnet"]}]}
        bar_tenant = {"networks": [{"id": "bar_net",
                                    "tenant_id": "bar_tenant",
                                    "subnets": ["bar_subnet"]}]}
        return {"task": {"uuid": "foo_task"},
                "admin": {"credential": "foo_admin"},
                "users": [{"id": "foo_user", "tenant_id": "foo_tenant"},
                          {"id": "bar_user", "tenant_id": "bar_tenant"}],
                "config": {"lbaas": kwargs},
                "tenants": {"foo_tenant": foo_tenant,
                            "bar_tenant": bar_tenant}}

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap", return_value="foo_service")
    def test__init__default(self, mock_wrap, mock_clients):
        context = lbaas_context.Lbaas(self.get_context())
        self.assertEqual(
            context.config["pool"]["lb_method"],
            lbaas_context.Lbaas.DEFAULT_CONFIG["pool"]["lb_method"])
        self.assertEqual(
            context.config["pool"]["protocol"],
            lbaas_context.Lbaas.DEFAULT_CONFIG["pool"]["protocol"])
        self.assertEqual(
            context.config["lbaas_version"],
            lbaas_context.Lbaas.DEFAULT_CONFIG["lbaas_version"])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap", return_value="foo_service")
    def test__init__explicit(self, mock_wrap, mock_clients):
        context = lbaas_context.Lbaas(
            self.get_context(pool={"lb_method": "LEAST_CONNECTIONS"}))
        self.assertEqual(context.config["pool"]["lb_method"],
                         "LEAST_CONNECTIONS")

    @mock.patch(NET + "wrap")
    @mock.patch("rally.plugins.openstack.context.neutron.lbaas.utils")
    @mock.patch("rally.osclients.Clients")
    def test_setup_with_lbaas(self, mock_clients, mock_utils, mock_wrap):
        mock_utils.iterate_per_tenants.return_value = [
            ("foo_user", "foo_tenant"),
            ("bar_user", "bar_tenant")]
        foo_net = {"id": "foo_net",
                   "tenant_id": "foo_tenant",
                   "subnets": ["foo_subnet"],
                   "lb_pools": [{"pool": {"id": "foo_pool",
                                          "tenant_id": "foo_tenant"}}]}
        bar_net = {"id": "bar_net",
                   "tenant_id": "bar_tenant",
                   "subnets": ["bar_subnet"],
                   "lb_pools": [{"pool": {"id": "bar_pool",
                                          "tenant_id": "bar_tenant"}}]}
        expected_net = [bar_net, foo_net]
        mock_create = mock.Mock(
            side_effect=lambda t, s,
            **kw: {"pool": {"id": str(t.split("_")[0]) + "_pool",
                            "tenant_id": t}})
        actual_net = []
        mock_wrap.return_value = mock.Mock(create_v1_pool=mock_create)
        net_wrapper = mock_wrap(mock_clients.return_value)
        net_wrapper.supports_extension.return_value = (True, None)
        fake_args = {"lbaas_version": 1}
        lb_context = lbaas_context.Lbaas(self.get_context(**fake_args))
        lb_context.setup()
        mock_utils.iterate_per_tenants.assert_called_once_with(
            lb_context.context["users"])
        net_wrapper.supports_extension.assert_called_once_with("lbaas")
        for tenant_id, tenant_ctx in (
                sorted(lb_context.context["tenants"].items())):
            for network in tenant_ctx["networks"]:
                actual_net.append(network)
        self.assertEqual(expected_net, actual_net)

    @mock.patch(NET + "wrap")
    @mock.patch("rally.plugins.openstack.context.neutron.lbaas.utils")
    @mock.patch("rally.osclients.Clients")
    def test_setup_with_no_lbaas(self, mock_clients, mock_utils, mock_wrap):
        mock_utils.iterate_per_tenants.return_value = [
            ("bar_user", "bar_tenant")]
        mock_create = mock.Mock(side_effect=lambda t, **kw: t + "-net")
        mock_wrap.return_value = mock.Mock(create_v1_pool=mock_create)
        fake_args = {"lbaas_version": 1}
        lb_context = lbaas_context.Lbaas(self.get_context(**fake_args))
        net_wrapper = mock_wrap(mock_clients.return_value)
        net_wrapper.supports_extension.return_value = (False, None)
        lb_context.setup()
        mock_utils.iterate_per_tenants.assert_not_called()
        net_wrapper.supports_extension.assert_called_once_with("lbaas")
        assert not net_wrapper.create_v1_pool.called

    @mock.patch(NET + "wrap")
    @mock.patch("rally.plugins.openstack.context.neutron.lbaas.utils")
    @mock.patch("rally.osclients.Clients")
    def test_setup_with_lbaas_version_not_one(self, mock_clients,
                                              mock_utils, mock_wrap):
        mock_utils.iterate_per_tenants.return_value = [
            ("bar_user", "bar_tenant")]
        mock_create = mock.Mock(side_effect=lambda t, **kw: t + "-net")
        mock_wrap.return_value = mock.Mock(create_v1_pool=mock_create)
        fake_args = {"lbaas_version": 2}
        lb_context = lbaas_context.Lbaas(self.get_context(**fake_args))
        net_wrapper = mock_wrap(mock_clients.return_value)
        net_wrapper.supports_extension.return_value = (True, None)
        self.assertRaises(NotImplementedError, lb_context.setup)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap")
    def test_cleanup(self, mock_wrap, mock_clients):
        net_wrapper = mock_wrap(mock_clients.return_value)
        lb_context = lbaas_context.Lbaas(self.get_context())
        expected_pools = []
        for tenant_id, tenant_ctx in lb_context.context["tenants"].items():
            resultant_pool = {"pool": {
                "id": str(tenant_id.split("_")[0]) + "_pool"}}
            expected_pools.append(resultant_pool)
            for network in (
                    lb_context.context["tenants"][tenant_id]["networks"]):
                network.setdefault("lb_pools", []).append(resultant_pool)
        lb_context.cleanup()
        net_wrapper.delete_v1_pool.assert_has_calls(
            [mock.call(pool["pool"]["id"]) for pool in expected_pools])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(NET + "wrap")
    def test_cleanup_lbaas_version_not_one(self, mock_wrap, mock_clients):
        fakeargs = {"lbaas_version": 2}
        net_wrapper = mock_wrap(mock_clients.return_value)
        lb_context = lbaas_context.Lbaas(self.get_context(**fakeargs))
        for tenant_id, tenant_ctx in lb_context.context["tenants"].items():
            resultant_pool = {"pool": {
                "id": str(tenant_id.split("_")[0]) + "_pool"}}
            for network in (
                    lb_context.context["tenants"][tenant_id]["networks"]):
                network.setdefault("lb_pools", []).append(resultant_pool)
        lb_context.cleanup()
        assert not net_wrapper.delete_v1_pool.called
