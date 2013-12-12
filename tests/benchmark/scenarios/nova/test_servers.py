# Copyright 2013: Mirantis Inc.
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

from rally.benchmark.scenarios.nova import servers
from rally.benchmark import utils as butils
from rally import exceptions as rally_exceptions
from rally import test
from tests.benchmark.scenarios.nova import test_utils


NOVA_SERVERS = "rally.benchmark.scenarios.nova.servers.NovaServers"


class NovaServersTestCase(test.TestCase):

    @mock.patch(NOVA_SERVERS + ".sleep_between")
    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._delete_server")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    def _verify_boot_and_delete_server(self, mock_boot, mock_delete,
                                       mock_random_name, mock_sleep):
        fake_server = object()
        mock_boot.return_value = fake_server
        mock_random_name.return_value = "random_name"
        servers.NovaServers.boot_and_delete_server("img", 0, 10, 20,
                                                   fakearg="f")

        mock_boot.assert_called_once_with("random_name", "img", 0, fakearg="f")
        mock_sleep.assert_called_once_with(10, 20)
        mock_delete.assert_called_once_with(fake_server)

    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.scenarios.nova.servers.random.choice")
    def _verify_boot_server(self, mock_choice, mock_osclients, mock_boot,
                            mock_random_name, nic=None, assert_nic=False):
        assert_nic = nic or assert_nic
        kwargs = {'fakearg': 'f'}
        expected_kwargs = {'fakearg': 'f'}

        fc = test_utils.FakeClients()
        mock_osclients.Clients.return_value = fc
        nova = test_utils.FakeNovaClient()
        fc.get_nova_client = lambda: nova

        temp_keys = ["username", "password", "tenant_name", "uri"]
        users_endpoints = [dict(zip(temp_keys, temp_keys))]
        servers.NovaServers._clients = butils._create_openstack_clients(
                                                users_endpoints, temp_keys)[0]

        mock_boot.return_value = object()
        mock_random_name.return_value = "random_name"
        if nic:
            kwargs['nics'] = nic
        if assert_nic:
            nova.networks.create('net-1')
            network = nova.networks.create('net-2')
            mock_choice.return_value = network
            expected_kwargs['nics'] = nic or [{'net-id': 'net-2'}]
        servers.NovaServers.boot_server("img", 0, **kwargs)

        mock_boot.assert_called_once_with("random_name", "img", 0,
                                          **expected_kwargs)

    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._delete_server")
    @mock.patch(NOVA_SERVERS + "._rescue_server")
    @mock.patch(NOVA_SERVERS + "._unrescue_server")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    def test_boot_rescue_unrescue(self, mock_boot, mock_unrescue,
                                  mock_rescue, mock_delete, mock_name):
        actions = [{'rescue_unrescue': 5}]
        fake_server = object()
        mock_boot.return_value = fake_server
        mock_name.return_value = 'random_name'
        servers.NovaServers.boot_and_bounce_server("img", 1,
                                                   actions=actions)
        mock_boot.assert_called_once_with("random_name", "img", 1,
                                          actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(5, mock_rescue.call_count,
                         "Rescue not called 5 times")
        self.assertEqual(5, mock_unrescue.call_count,
                         "Unrescue not called 5 times")
        mock_rescue.assert_has_calls(server_calls)
        mock_unrescue.assert_has_calls(server_calls)
        mock_delete.assert_called_once_with(fake_server)

    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._delete_server")
    @mock.patch(NOVA_SERVERS + "._stop_server")
    @mock.patch(NOVA_SERVERS + "._start_server")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    def test_boot_stop_start(self, mock_boot, mock_start, mock_stop,
                             mock_delete, mock_name):
        actions = [{'stop_start': 5}]
        fake_server = object()
        mock_boot.return_value = fake_server
        mock_name.return_value = 'random_name'
        servers.NovaServers.boot_and_bounce_server("img", 1,
                                                   actions=actions)
        mock_boot.assert_called_once_with("random_name", "img", 1,
                                          actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(5, mock_stop.call_count, "Stop not called 5 times")
        self.assertEqual(5, mock_start.call_count, "Start not called 5 times")
        mock_stop.assert_has_calls(server_calls)
        mock_start.assert_has_calls(server_calls)
        mock_delete.assert_called_once_with(fake_server)

    def _bind_server_actions(self, mock_reboot, mock_stop_start):
        bindings = servers.ACTION_BUILDER._bindings
        if mock_reboot:
            bindings['soft_reboot']['action'] = mock_reboot
            bindings['hard_reboot']['action'] = mock_reboot
        if mock_stop_start:
            bindings['stop_start']['action'] = mock_stop_start

    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._delete_server")
    @mock.patch(NOVA_SERVERS + "._reboot_server")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    def _verify_reboot(self, mock_boot, mock_reboot, mock_delete, mock_name,
                       soft=True):
        actions = [{'soft_reboot' if soft else 'hard_reboot': 5}]
        fake_server = object()
        self._bind_server_actions(mock_reboot, None)
        mock_boot.return_value = fake_server
        mock_name.return_value = 'random_name'
        servers.NovaServers.boot_and_bounce_server("img", 1,
                                                   actions=actions)
        mock_boot.assert_called_once_with("random_name", "img", 1,
                                          actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server, soft=soft))
        self.assertEqual(5, mock_reboot.call_count,
                         "Reboot not called 5 times")
        mock_reboot.assert_has_calls(server_calls)
        mock_delete.assert_called_once_with(fake_server)

    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._delete_server")
    @mock.patch(NOVA_SERVERS + "._stop_and_start_server")
    @mock.patch(NOVA_SERVERS + "._reboot_server")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    def test_multiple_bounce_actions(self, mock_boot, mock_reboot,
                                     mock_stop_start, mock_delete, mock_name):
        actions = [{'hard_reboot': 5}, {'stop_start': 8}]
        fake_server = object()
        self._bind_server_actions(mock_reboot, mock_stop_start)
        mock_boot.return_value = fake_server
        mock_name.return_value = 'random_name'
        servers.NovaServers.boot_and_bounce_server("img", 1,
                                                   actions=actions)
        mock_boot.assert_called_once_with("random_name", "img", 1,
                                          actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server, soft=False))
        self.assertEqual(5, mock_reboot.call_count,
                         "Reboot not called 5 times")
        mock_reboot.assert_has_calls(server_calls)
        server_calls = []
        for i in range(8):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(8, mock_stop_start.call_count,
                         "Stop/Start not called 8 times")
        mock_stop_start.assert_has_calls(server_calls)
        mock_delete.assert_called_once_with(fake_server)

    def test_validate_actions(self):
        actions = [{"hardd_reboot": 6}]
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = [{"hard_reboot": "no"}]
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = {"hard_reboot": 6}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = {"hard_reboot": -1}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = {"hard_reboot": 0}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          1, 1, actions=actions)

    def test_boot_soft_reboot(self):
        self._verify_reboot(soft=True)

    def test_boot_hard_reboot(self):
        self._verify_reboot(soft=False)

    def test_boot_and_delete_server(self):
        self._verify_boot_and_delete_server()

    def test_boot_server_no_nics(self):
        self._verify_boot_server(nic=None, assert_nic=False)

    def test_boot_server_with_nic(self):
        self._verify_boot_server(nic=[{'net-id': 'net-1'}],
                                 assert_nic=True)

    def test_boot_server_random_nic(self):
        self._verify_boot_server(nic=None, assert_nic=True)

    @mock.patch(NOVA_SERVERS + "._generate_random_name")
    @mock.patch(NOVA_SERVERS + "._delete_image")
    @mock.patch(NOVA_SERVERS + "._delete_server")
    @mock.patch(NOVA_SERVERS + "._create_image")
    @mock.patch(NOVA_SERVERS + "._boot_server")
    def test_snapshot_server(self, mock_boot, mock_create_image,
                             mock_delete_server, mock_delete_image,
                             mock_random_name):

        fake_server = object()
        fake_image = test_utils.FakeImageManager().create()
        fake_image.id = "image_id"

        mock_random_name.return_value = "random_name"
        mock_boot.return_value = fake_server
        mock_create_image.return_value = fake_image
        servers.NovaServers.snapshot_server("i", 0, fakearg=2)

        mock_boot.assert_has_calls([
            mock.call("random_name", "i", 0, fakearg=2),
            mock.call("random_name", "image_id", 0, fakearg=2)])
        mock_create_image.assert_called_once_with(fake_server)
        mock_delete_server.assert_has_calls([
            mock.call(fake_server),
            mock.call(fake_server)])
        mock_delete_image.assert_called_once_with(fake_image)
