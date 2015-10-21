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

from rally.deployment.serverprovider.providers import cobbler
from tests.unit import test


class TestCobblerProvider(test.TestCase):
    def setUp(self):
        self.config = {"type": "CobblerProvider",
                       "host": "h1", "user": "u1", "password": "p1",
                       "system_password": "p2",
                       "selector": {"profile": "p1", "owners": "o1"}}
        self.rendered = {"ip_address_eth3": "",
                         "ip_address_eth1": "1.1.1.1",
                         "power_user": "fake_root",
                         "redhat_management_key": "fake_key",
                         "name": "fake_name"}
        self.system_names = ["s1", "s2"]
        self.token = "token"
        self.handle = "handle"
        super(TestCobblerProvider, self).setUp()

    def create_mocks(self, mock_server, is_no_ip, provider):
        mock_server.find_system = mock.Mock(return_value=self.system_names)
        mock_server.login = mock.Mock(return_value=self.token)
        mock_server.get_system_handle = mock.Mock(return_value=self.handle)
        mock_server.power_system = mock.Mock()
        if is_no_ip:
            self.rendered["ip_address_eth1"] = ""
        mock_server.get_system_as_rendered = mock.Mock(
            return_value=self.rendered)
        provider.cobbler = mock_server

    @mock.patch("six.moves.xmlrpc_client.Server")
    def test_create_servers(self, mock_server):
        provider = cobbler.CobblerProvider(config=self.config, deployment=None)
        mock_server.assert_called_once_with(uri="http://h1/cobbler_api")

        self.create_mocks(mock_server=mock_server, is_no_ip=False,
                          provider=provider)

        credentials = provider.create_servers()

        mock_server.find_system.assert_called_once_with(
            self.config["selector"])

        mock_server.login.assert_called_with(self.config["user"],
                                             self.config["password"])
        mock_server.login.call_count = len(self.system_names)

        mock_server.power_system.assert_called_with(self.handle, "reboot",
                                                    self.token)

        self.assertEqual(["1.1.1.1"] * 2, [s.host for s in credentials])
        self.assertEqual(["fake_root"] * 2, [s.user for s in credentials])
        self.assertEqual(["p2"] * 2, [s.password for s in credentials])
        self.assertEqual(["fake_key"] * 2, [s.key for s in credentials])
        self.assertEqual([22] * 2, [s.port for s in credentials])

    @mock.patch("six.moves.xmlrpc_client.Server")
    def test_create_servers_when_selects_nothing(self, mock_server):
        provider = cobbler.CobblerProvider(config=self.config, deployment=None)

        mock_server.find_system = mock.Mock(return_value=[])
        provider.cobbler = mock_server

        self.assertRaisesRegexp(RuntimeError,
                                "No associated systems selected by {.*}$",
                                provider.create_servers)

    @mock.patch("six.moves.xmlrpc_client.Server")
    def test_create_servers_when_no_ip_found(self, mock_server):
        provider = cobbler.CobblerProvider(config=self.config, deployment=None)

        self.create_mocks(mock_server=mock_server, is_no_ip=True,
                          provider=provider)

        self.assertRaisesRegexp(RuntimeError,
                                "No valid ip address found for system '.*'$",
                                provider.create_servers)
