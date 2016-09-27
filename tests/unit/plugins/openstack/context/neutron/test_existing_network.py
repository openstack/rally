# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.openstack.context.network import existing_network
from tests.unit import test

CTX = "rally.plugins.openstack.context.network"


class ExistingNetworkTestCase(test.TestCase):

    def setUp(self):
        super(ExistingNetworkTestCase, self).setUp()

        self.config = {"foo": "bar"}
        self.context = test.get_test_context()
        self.context.update({
            "users": [
                {"id": 1,
                 "tenant_id": "tenant1",
                 "credential": mock.Mock()},
                {"id": 2,
                 "tenant_id": "tenant2",
                 "credential": mock.Mock()},
            ],
            "tenants": {
                "tenant1": {},
                "tenant2": {},
            },
            "config": {
                "existing_network": self.config
            },
        })

    @mock.patch("rally.osclients.Clients")
    @mock.patch("rally.plugins.openstack.wrappers.network.wrap")
    def test_setup(self, mock_network_wrap, mock_clients):
        networks = [mock.Mock(), mock.Mock(), mock.Mock()]
        net_wrappers = {
            "tenant1": mock.Mock(
                **{"list_networks.return_value": networks[0:2]}),
            "tenant2": mock.Mock(
                **{"list_networks.return_value": networks[2:]})
        }
        mock_network_wrap.side_effect = [net_wrappers["tenant1"],
                                         net_wrappers["tenant2"]]

        context = existing_network.ExistingNetwork(self.context)
        context.setup()

        mock_clients.assert_has_calls([
            mock.call(u["credential"]) for u in self.context["users"]])
        mock_network_wrap.assert_has_calls([
            mock.call(mock_clients.return_value, context, config=self.config),
            mock.call(mock_clients.return_value, context, config=self.config)])
        for net_wrapper in net_wrappers.values():
            net_wrapper.list_networks.assert_called_once_with()

        self.assertEqual(
            self.context["tenants"],
            {
                "tenant1": {"networks": networks[0:2]},
                "tenant2": {"networks": networks[2:]},
            }
        )

    def test_cleanup(self):
        # NOTE(stpierre): Test that cleanup is not abstract
        existing_network.ExistingNetwork({"task": mock.MagicMock()}).cleanup()
