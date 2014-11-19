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
from rally import exceptions as rally_exceptions
from rally.objects import endpoint
from rally import osclients
from tests.unit import fakes
from tests.unit import test


NOVA_SERVERS_MODULE = "rally.benchmark.scenarios.nova.servers"
NOVA_SERVERS = NOVA_SERVERS_MODULE + ".NovaServers"


class NovaServersTestCase(test.TestCase):

    def test_boot_rescue_unrescue(self):
        actions = [{'rescue_unrescue': 5}]
        fake_server = mock.MagicMock()
        scenario = servers.NovaServers()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario._rescue_server = mock.MagicMock()
        scenario._unrescue_server = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()

        scenario.boot_and_bounce_server("img", 1, actions=actions)
        scenario._boot_server.assert_called_once_with("name", "img", 1,
                                                      actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(5, scenario._rescue_server.call_count,
                         "Rescue not called 5 times")
        self.assertEqual(5, scenario._unrescue_server.call_count,
                         "Unrescue not called 5 times")
        scenario._rescue_server.assert_has_calls(server_calls)
        scenario._unrescue_server.assert_has_calls(server_calls)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def test_boot_stop_start(self):
        actions = [{'stop_start': 5}]
        fake_server = mock.MagicMock()
        scenario = servers.NovaServers()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario._start_server = mock.MagicMock()
        scenario._stop_server = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()

        scenario.boot_and_bounce_server("img", 1, actions=actions)

        scenario._boot_server.assert_called_once_with("name", "img", 1,
                                                      actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(5, scenario._stop_server.call_count,
                         "Stop not called 5 times")
        self.assertEqual(5, scenario._start_server.call_count,
                         "Start not called 5 times")
        scenario._stop_server.assert_has_calls(server_calls)
        scenario._start_server.assert_has_calls(server_calls)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def test_multiple_bounce_actions(self):
        actions = [{'hard_reboot': 5}, {'stop_start': 8}]
        fake_server = mock.MagicMock()
        scenario = servers.NovaServers()

        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario._reboot_server = mock.MagicMock()
        scenario._stop_and_start_server = mock.MagicMock()
        scenario._generate_random_name = mock.MagicMock(return_value='name')

        scenario.boot_and_bounce_server("img", 1, actions=actions)
        scenario._boot_server.assert_called_once_with("name", "img", 1,
                                                      actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(5, scenario._reboot_server.call_count,
                         "Reboot not called 5 times")
        scenario._reboot_server.assert_has_calls(server_calls)
        server_calls = []
        for i in range(8):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(8, scenario._stop_and_start_server.call_count,
                         "Stop/Start not called 8 times")
        scenario._stop_and_start_server.assert_has_calls(server_calls)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def test_validate_actions(self):
        actions = [{"hardd_reboot": 6}]
        scenario = servers.NovaServers()

        self.assertRaises(rally_exceptions.InvalidConfigException,
                          scenario.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = [{"hard_reboot": "no"}]
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          scenario.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = {"hard_reboot": 6}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          scenario.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = {"hard_reboot": -1}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          scenario.boot_and_bounce_server,
                          1, 1, actions=actions)
        actions = {"hard_reboot": 0}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          scenario.boot_and_bounce_server,
                          1, 1, actions=actions)

    def _verify_reboot(self, soft=True):
        actions = [{'soft_reboot' if soft else 'hard_reboot': 5}]
        fake_server = mock.MagicMock()
        scenario = servers.NovaServers()

        scenario._reboot_server = mock.MagicMock()
        scenario._soft_reboot_server = mock.MagicMock()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario._generate_random_name = mock.MagicMock(return_value='name')

        scenario.boot_and_bounce_server("img", 1, actions=actions)

        scenario._boot_server.assert_called_once_with("name", "img", 1,
                                                      actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        if soft:
            self.assertEqual(5, scenario._soft_reboot_server.call_count,
                             "Reboot not called 5 times")
            scenario._soft_reboot_server.assert_has_calls(server_calls)
        else:
            self.assertEqual(5, scenario._reboot_server.call_count,
                             "Reboot not called 5 times")
            scenario._reboot_server.assert_has_calls(server_calls)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def test_boot_soft_reboot(self):
        self._verify_reboot(soft=True)

    def test_boot_hard_reboot(self):
        self._verify_reboot(soft=False)

    def test_boot_and_delete_server(self):
        fake_server = object()

        scenario = servers.NovaServers()
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario.sleep_between = mock.MagicMock()

        scenario.boot_and_delete_server("img", 0, 10, 20, fakearg="fakearg")

        scenario._boot_server.assert_called_once_with("name", "img", 0,
                                                      fakearg="fakearg")
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def test_boot_and_list_server(self):
        scenario = servers.NovaServers()
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario._boot_server = mock.MagicMock()
        scenario._list_servers = mock.MagicMock()

        scenario.boot_and_list_server("img", 0, fakearg="fakearg")

        scenario._boot_server.assert_called_once_with("name", "img", 0,
                                                      fakearg="fakearg")
        scenario._list_servers.assert_called_once_with(True)

    def test_boot_server_from_volume_and_delete(self):
        fake_server = object()
        scenario = servers.NovaServers()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()

        fake_volume = fakes.FakeVolumeManager().create()
        fake_volume.id = "volume_id"
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)

        scenario.boot_server_from_volume_and_delete("img", 0, 5, 10, 20,
                                                    fakearg="f")

        scenario._create_volume.assert_called_once_with(5, imageRef="img")
        scenario._boot_server.assert_called_once_with(
            "name", "img", 0,
            block_device_mapping={'vda': 'volume_id:::1'},
            fakearg="f")
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def _prepare_boot(self, mock_osclients, nic=None, assert_nic=False):
        fake_server = mock.MagicMock()

        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc
        nova = fakes.FakeNovaClient()
        fc.nova = lambda: nova

        user_endpoint = endpoint.Endpoint("url", "user", "password", "tenant")
        clients = osclients.Clients(user_endpoint)
        scenario = servers.NovaServers(clients=clients)

        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._generate_random_name = mock.MagicMock(return_value="name")

        kwargs = {'fakearg': 'f'}
        expected_kwargs = {'fakearg': 'f'}

        assert_nic = nic or assert_nic
        if nic:
            kwargs['nics'] = nic
        if assert_nic:
            nova.networks.create('net-1')
            expected_kwargs['nics'] = nic or [{'net-id': 'net-2'}]

        print(kwargs)
        print(expected_kwargs)

        return scenario, kwargs, expected_kwargs

    def _verify_boot_server(self, mock_osclients, nic=None, assert_nic=False):
        scenario, kwargs, expected_kwargs = self._prepare_boot(
            mock_osclients=mock_osclients,
            nic=nic, assert_nic=assert_nic)

        scenario.boot_server("img", 0, **kwargs)
        scenario._boot_server.assert_called_once_with("name", "img", 0, False,
                                                      **expected_kwargs)

    @mock.patch("rally.benchmark.scenarios.nova.servers.NovaServers.clients")
    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_boot_server_no_nics(self, mock_osclients, mock_nova_clients):
        mock_nova_clients.return_value = fakes.FakeNovaClient()
        self._verify_boot_server(mock_osclients=mock_osclients,
                                 nic=None, assert_nic=False)

    @mock.patch("rally.benchmark.runners.base.osclients")
    def test_boot_server_with_nic(self, mock_osclients):
        self._verify_boot_server(mock_osclients=mock_osclients,
                                 nic=[{'net-id': 'net-1'}], assert_nic=True)

    def test_snapshot_server(self):
        fake_server = object()
        fake_image = fakes.FakeImageManager()._create()
        fake_image.id = "image_id"

        scenario = servers.NovaServers()
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._create_image = mock.MagicMock(return_value=fake_image)
        scenario._delete_server = mock.MagicMock()
        scenario._delete_image = mock.MagicMock()

        scenario.snapshot_server("i", 0, fakearg=2)

        scenario._boot_server.assert_has_calls([
            mock.call("name", "i", 0, fakearg=2),
            mock.call("name", "image_id", 0, fakearg=2)])
        scenario._create_image.assert_called_once_with(fake_server)
        scenario._delete_server.assert_has_calls([
            mock.call(fake_server, force=False),
            mock.call(fake_server, force=False)])
        scenario._delete_image.assert_called_once_with(fake_image)

    def _test_resize(self, confirm=False):
        fake_server = object()
        fake_image = fakes.FakeImageManager()._create()
        fake_image.id = "image_id"
        flavor = mock.MagicMock()
        to_flavor = mock.MagicMock()

        scenario = servers.NovaServers()
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._resize_confirm = mock.MagicMock()
        scenario._resize_revert = mock.MagicMock()
        scenario._resize = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()

        kwargs = {'confirm': confirm}
        scenario.resize_server(fake_image, flavor, to_flavor, **kwargs)

        scenario._resize.assert_called_once_with(fake_server, to_flavor)

        if confirm:
            scenario._resize_confirm.assert_called_once_with(fake_server)
        else:
            scenario._resize_revert.assert_called_once_with(fake_server)

    def test_resize_with_confirm(self):
        self._test_resize(confirm=True)

    def test_resize_with_revert(self):
        self._test_resize(confirm=False)
