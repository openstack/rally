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
import six

from rally import osclients
from rally.plugins.openstack.scenarios.fuel import utils
from tests.unit import test


UTILS = "rally.plugins.openstack.scenarios.fuel.utils."


class ModuleTestCase(test.TestCase):

    @mock.patch(UTILS + "six")
    @mock.patch(UTILS + "FuelClient", return_value="fuel_client")
    def test_fuel(self, mock_fuel_client, mock_six):
        mock_six.moves.urllib.parse.urlparse().hostname = "foo_host"
        clients_ins = mock.Mock(endpoint=mock.Mock(username="foo_user",
                                                   password="foo_pass"))

        client = utils.fuel(clients_ins)
        mock_fuel_client.assert_called_once_with(
            version="v1", server_address="foo_host", server_port=8000,
            username="foo_user", password="foo_pass")
        self.assertEqual("fuel_client", client)

    def test_fuel_is_registered(self):
        six.moves.reload_module(osclients)
        self.assertFalse(hasattr(osclients.Clients, "fuel"))
        six.moves.reload_module(utils)
        self.assertTrue(hasattr(osclients.Clients, "fuel"))
        # NOTE(amaretskiy): Now we can finally mock utils.FuelClient,
        # since `reload_module' above destroys mocks
        with mock.patch(UTILS + "FuelClient",
                        mock.Mock(return_value="fuel_client")):
            with mock.patch(UTILS + "six"):
                clients = osclients.Clients(mock.Mock())
                self.assertEqual("fuel_client", clients.fuel())


class FuelClientTestCase(test.TestCase):

    @mock.patch(UTILS + "os")
    def test___init__(self, mock_os):
        mock_os.environ = {}
        mock_fuelclient = mock.Mock(get_client=lambda *args, **kw: [args, kw])
        with mock.patch.dict("sys.modules", {"fuelclient": mock_fuelclient}):
            client = utils.FuelClient(version="foo_version",
                                      server_address="foo_address",
                                      server_port=1234,
                                      username="foo_user",
                                      password="foo_pass")
            expected_environ = {"KEYSTONE_PASS": "foo_pass",
                                "KEYSTONE_USER": "foo_user",
                                "LISTEN_PORT": "1234",
                                "SERVER_ADDRESS": "foo_address"}
            self.assertEqual(expected_environ, mock_os.environ)
            self.assertEqual([("environment",), {"version": "foo_version"}],
                             client.environment)
            self.assertEqual([("node",), {"version": "foo_version"}],
                             client.node)
            self.assertEqual([("task",), {"version": "foo_version"}],
                             client.task)


class FuelScenarioTestCase(test.ClientsTestCase):

    def test__list_environments(self):
        scenario = utils.FuelScenario()
        self.assertEqual(
            self.admin_clients("fuel").environment.get_all.return_value,
            scenario._list_environments())
        self.admin_clients(
            "fuel").environment.get_all.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "fuel.list_environments")
