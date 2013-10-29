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
from rally import test
from tests.benchmark.scenarios.nova import test_utils


class NovaServersTestCase(test.TestCase):

    def setUp(self):
        super(NovaServersTestCase, self).setUp()
        self.scenario = "rally.benchmark.scenarios.nova.servers.NovaServers"
        self.boot = "%s._boot_server" % self.scenario
        self.delete = "%s._delete_server" % self.scenario
        self.random_name = "%s._generate_random_name" % self.scenario
        self.reboot = "%s._reboot_server" % self.scenario
        self.start = "%s._start_server" % self.scenario
        self.stop = "%s._stop_server" % self.scenario
        self.stop_start = "%s._stop_and_start_server" % self.scenario

    def _verify_boot_server(self, assert_delete=False):
        fake_server = object()
        with mock.patch(self.boot) as mock_boot:
            with mock.patch(self.delete) as mock_delete:
                with mock.patch(self.random_name) as mock_random_name:
                    mock_boot.return_value = fake_server
                    mock_random_name.return_value = "random_name"
                    servers.NovaServers.boot_and_delete_server({}, "img", 0,
                                                               fakearg="f")

        mock_boot.assert_called_once_with("random_name", "img", 0, fakearg="f")
        if assert_delete:
            mock_delete.assert_called_once_with(fake_server)

    def test_boot_stop_start(self):
        actions = [{'stop_start': 5}]
        fake_server = object()
        with mock.patch(self.boot) as mock_boot:
            with mock.patch(self.start) as mock_start:
                with mock.patch(self.stop) as mock_stop:
                    with mock.patch(self.random_name) as mock_name:
                        mock_boot.return_value = fake_server
                        mock_name.return_value = 'random_name'
                        servers.NovaServers.boot_and_bounce_server(
                                                            {}, "img",
                                                            1, actions=actions)
        mock_boot.assert_called_once_with("random_name", "img", 1,
                                          actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server))
        self.assertEqual(5, mock_stop.call_count, "Stop not called 5 times")
        self.assertEqual(5, mock_start.call_count, "Start not called 5 times")
        mock_stop.assert_has_calls(server_calls)
        mock_start.assert_has_calls(server_calls)

    def _bind_server_actions(self, mock_reboot, mock_stop_start):
        bindings = servers.ACTION_BUILDER._bindings
        if mock_reboot:
            bindings['soft_reboot']['action'] = mock_reboot
            bindings['hard_reboot']['action'] = mock_reboot
        if mock_stop_start:
            bindings['stop_start']['action'] = mock_stop_start

    def _verify_reboot(self, soft=True):
        actions = [{'soft_reboot' if soft else 'hard_reboot': 5}]
        fake_server = object()
        with mock.patch(self.boot) as mock_boot:
            with mock.patch(self.reboot) as mock_reboot:
                with mock.patch(self.random_name) as mock_name:
                    self._bind_server_actions(mock_reboot, None)
                    mock_boot.return_value = fake_server
                    mock_name.return_value = 'random_name'
                    servers.NovaServers.boot_and_bounce_server({},
                                                               "img",
                                                               1,
                                                               actions=actions)
        mock_boot.assert_called_once_with("random_name", "img", 1,
                                          actions=actions)
        server_calls = []
        for i in range(5):
            server_calls.append(mock.call(fake_server, soft=soft))
        self.assertEqual(5, mock_reboot.call_count,
                         "Reboot not called 5 times")
        mock_reboot.assert_has_calls(server_calls)

    def test_multiple_bounce_actions(self):
        actions = [{'hard_reboot': 5}, {'stop_start': 8}]
        fake_server = object()
        with mock.patch(self.boot) as mock_boot:
            with mock.patch(self.reboot) as mock_reboot:
                with mock.patch(self.random_name) as mock_name:
                    with mock.patch(self.stop_start) as mock_stop_start:
                        self._bind_server_actions(mock_reboot, mock_stop_start)
                        mock_boot.return_value = fake_server
                        mock_name.return_value = 'random_name'
                        servers.NovaServers.boot_and_bounce_server(
                                                            {}, "img", 1,
                                                            actions=actions)
        mock_boot.assert_called_once_with("random_name", "img",
                                          1, actions=actions)
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

    def test_validate_actions(self):
        actions = [{"hardd_reboot": 6}]
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          {}, 1, 1, actions=actions)
        actions = [{"hard_reboot": "no"}]
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          {}, 1, 1, actions=actions)
        actions = {"hard_reboot": 6}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          {}, 1, 1, actions=actions)
        actions = {"hard_reboot": -1}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          {}, 1, 1, actions=actions)
        actions = {"hard_reboot": 0}
        self.assertRaises(rally_exceptions.InvalidConfigException,
                          servers.NovaServers.boot_and_bounce_server,
                          {}, 1, 1, actions=actions)

    def test_boot_soft_reboot(self):
        self._verify_reboot(soft=True)

    def test_boot_hard_reboot(self):
        self._verify_reboot(soft=False)

    def test_boot_and_delete_server(self):
        self._verify_boot_server(assert_delete=True)

    def test_boot_server(self):
        self._verify_boot_server()

    def test_snapshot_server(self):

        fake_server = object()
        fake_image = test_utils.FakeImageManager().create()
        fake_image.id = "image_id"

        scenario = "rally.benchmark.scenarios.nova.servers.NovaServers"
        boot = "%s._boot_server" % scenario
        create_image = "%s._create_image" % scenario
        delete_server = "%s._delete_server" % scenario
        delete_image = "%s._delete_image" % scenario
        random_name = "%s._generate_random_name" % scenario
        with mock.patch(boot) as mock_boot:
            with mock.patch(create_image) as mock_create_image:
                with mock.patch(delete_server) as mock_delete_server:
                    with mock.patch(delete_image) as mock_delete_image:
                        with mock.patch(random_name) as mock_random_name:
                            mock_random_name.return_value = "random_name"
                            mock_boot.return_value = fake_server
                            mock_create_image.return_value = fake_image
                            servers.NovaServers.snapshot_server({}, "i", 0,
                                                                fakearg=2)

        mock_boot.assert_has_calls([
            mock.call("random_name", "i", 0, fakearg=2),
            mock.call("random_name", "image_id", 0, fakearg=2)])
        mock_create_image.assert_called_once_with(fake_server)
        mock_delete_server.assert_has_calls([
            mock.call(fake_server),
            mock.call(fake_server)])
        mock_delete_image.assert_called_once_with(fake_image)
