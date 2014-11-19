# Copyright 2013: Rackspace UK
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

from rally.benchmark.scenarios.vm import vmtasks
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


class VMTasksTestCase(test.TestCase):

    @mock.patch("json.loads")
    def test_boot_runcommand_delete(self, mock_json_loads):
        # Setup mocks
        scenario = vmtasks.VMTasks()
        fake_server = fakes.FakeServer()
        fake_server.addresses = dict(
            private=[dict(
                version=4,
                addr="1.2.3.4"
            )]
        )

        scenario._boot_server = mock.MagicMock(return_value=fake_server)

        fake_volume = fakes.FakeVolumeManager().create()
        fake_volume.id = "volume_id"
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)

        scenario._generate_random_name = mock.MagicMock(return_value="name")

        fake_floating_ip = fakes.FakeFloatingIP()
        fake_floating_ip.ip = "4.3.2.1"
        scenario._create_floating_ip = mock.MagicMock(
            return_value=fake_floating_ip)
        scenario._associate_floating_ip = mock.MagicMock()
        scenario._release_server_floating_ip = mock.MagicMock()

        fake_floating_ip_pool = fakes.FakeFloatingIPPool()
        fake_floating_ip_pool.name = "public"
        scenario._list_floating_ip_pools = mock.MagicMock(
            return_value=[fake_floating_ip_pool])

        scenario.run_command = mock.MagicMock()
        scenario.run_command.return_value = (0, 'stdout', 'stderr')
        scenario._delete_server = mock.MagicMock()

        # Run scenario
        scenario.boot_runcommand_delete(
            "image_id", "flavour_id", "script_path", "interpreter",
            fixed_network='private', floating_network='public',
            volume_args={'size': 10}, username="username", ip_version=4,
            port=22, use_floatingip=True, force_delete=False, fakearg="f")

        # Assertions
        scenario._boot_server.assert_called_once_with(
            'name', 'image_id', "flavour_id", key_name="rally_ssh_key",
            fakearg="f", block_device_mapping={'vda': 'volume_id:::1'})

        scenario._create_volume.assert_called_once_with(10, imageRef=None)
        scenario._create_floating_ip.assert_called_once_with(
            fake_floating_ip_pool.name)
        scenario._associate_floating_ip.assert_called_once_with(
            fake_server, fake_floating_ip)
        scenario.run_command.assert_called_once_with(
            fake_floating_ip.ip, 22, 'username',
            "interpreter", "script_path")

        mock_json_loads.assert_called_once_with('stdout')

        scenario._release_server_floating_ip.assert_called_once_with(
            fake_server, fake_floating_ip)
        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    @mock.patch("json.loads")
    def test_boot_runcommand_delete_fails(self, mock_json_loads):
        # Setup mocks
        scenario = vmtasks.VMTasks()
        fake_server = fakes.FakeServer()
        fake_server.addresses = dict(
            private=[dict(
                version=4,
                addr="1.2.3.4"
            )]
        )

        scenario._boot_server = mock.MagicMock(return_value=fake_server)

        scenario._generate_random_name = mock.MagicMock(return_value="name")

        fake_floating_ip = fakes.FakeFloatingIP()
        fake_floating_ip.ip = "4.3.2.1"
        scenario._create_floating_ip = mock.MagicMock(
            return_value=fake_floating_ip)
        scenario._associate_floating_ip = mock.MagicMock()
        scenario._release_server_floating_ip = mock.MagicMock()

        fake_floating_ip_pool = fakes.FakeFloatingIPPool()
        fake_floating_ip_pool.name = "public"
        scenario._list_floating_ip_pools = mock.MagicMock(
            return_value=[fake_floating_ip_pool])

        scenario.run_command = mock.MagicMock()
        scenario.run_command.return_value = (1, 'stdout', 'stderr')
        scenario._delete_server = mock.MagicMock()

        # Run scenario
        self.assertRaises(exceptions.ScriptError,
                          scenario.boot_runcommand_delete,
                          "image_id", "flavour_id", "script_path",
                          "interpreter", fixed_network='private',
                          floating_network='public', username="username",
                          ip_version=4, port=22, use_floatingip=True,
                          force_delete=False, fakearg="f")

        # Assertions
        scenario._boot_server.assert_called_once_with(
            'name', 'image_id', "flavour_id", key_name="rally_ssh_key",
            fakearg="f")

        scenario._create_floating_ip.assert_called_once_with(
            fake_floating_ip_pool.name)
        scenario._associate_floating_ip.assert_called_once_with(
            fake_server, fake_floating_ip)
        scenario.run_command.assert_called_once_with(
            fake_floating_ip.ip, 22, 'username',
            "interpreter", "script_path")

    @mock.patch("json.loads")
    def test_boot_runcommand_delete_valueerror_fails(self, mock_json_loads):
        # Setup mocks
        scenario = vmtasks.VMTasks()
        fake_server = fakes.FakeServer()
        fake_server.addresses = dict(
            private=[dict(
                version=4,
                addr="1.2.3.4"
            )]
        )

        mock_json_loads.side_effect = ValueError
        scenario._boot_server = mock.MagicMock(return_value=fake_server)

        scenario._generate_random_name = mock.MagicMock(return_value="name")

        fake_floating_ip = fakes.FakeFloatingIP()
        fake_floating_ip.ip = "4.3.2.1"
        scenario._create_floating_ip = mock.MagicMock(
            return_value=fake_floating_ip)
        scenario._associate_floating_ip = mock.MagicMock()
        scenario._release_server_floating_ip = mock.MagicMock()

        fake_floating_ip_pool = fakes.FakeFloatingIPPool()
        fake_floating_ip_pool.name = "public"
        scenario._list_floating_ip_pools = mock.MagicMock(
            return_value=[fake_floating_ip_pool])

        scenario.run_command = mock.MagicMock()
        scenario.run_command.return_value = (0, 'stdout', 'stderr')
        scenario._delete_server = mock.MagicMock()

        # Run scenario
        self.assertRaises(exceptions.ScriptError,
                          scenario.boot_runcommand_delete,
                          "image_id", "flavour_id", "script_path",
                          "interpreter", fixed_network='private',
                          floating_network='public', username="username",
                          ip_version=4, port=22, use_floatingip=True,
                          force_delete=False, fakearg="f")

        # Assertions
        scenario._boot_server.assert_called_once_with(
            'name', 'image_id', "flavour_id", key_name="rally_ssh_key",
            fakearg="f")

        scenario._create_floating_ip.assert_called_once_with(
            fake_floating_ip_pool.name)
        scenario._associate_floating_ip.assert_called_once_with(
            fake_server, fake_floating_ip)
        scenario.run_command.assert_called_once_with(
            fake_floating_ip.ip, 22, 'username',
            "interpreter", "script_path")

    @mock.patch("json.loads")
    def test_boot_runcommand_delete_no_floating_ip(self, mock_json_loads):
        # Setup mocks
        scenario = vmtasks.VMTasks()
        fake_server = fakes.FakeServer()
        fake_server.addresses = dict(
            private=[dict(
                version=4,
                addr="1.2.3.4"
            )]
        )

        scenario._boot_server = mock.MagicMock(return_value=fake_server)

        scenario._generate_random_name = mock.MagicMock(return_value="name")

        scenario.run_command = mock.MagicMock()
        scenario.run_command.return_value = (0, 'stdout', 'stderr')
        scenario._delete_server = mock.MagicMock()

        # Run scenario
        scenario.boot_runcommand_delete(
            "image_id", "flavour_id", "script_path", "interpreter",
            fixed_network='private', floating_network='public',
            username="username", ip_version=4,
            port=22, use_floatingip=False, force_delete=False, fakearg="f")

        # Assertions
        scenario._boot_server.assert_called_once_with(
            'name', 'image_id', "flavour_id", key_name="rally_ssh_key",
            fakearg="f")

        scenario.run_command.assert_called_once_with(
            fake_server.addresses['private'][0]['addr'], 22, 'username',
            "interpreter", "script_path")

        mock_json_loads.assert_called_once_with('stdout')

        scenario._delete_server.assert_called_once_with(fake_server,
                                                        force=False)

    def test__release_server_floating_ip(self):
        scenario = vmtasks.VMTasks()
        fake_server = fakes.FakeServer()
        fake_floating_ip = fakes.FakeFloatingIP()

        scenario._dissociate_floating_ip = mock.MagicMock()
        scenario._delete_floating_ip = mock.MagicMock()
        scenario.check_ip_address = mock.MagicMock(
            return_value=mock.MagicMock(return_value=True))

        scenario._release_server_floating_ip(fake_server, fake_floating_ip)

        scenario._dissociate_floating_ip.assert_called_once_with(
            fake_server, fake_floating_ip)
        scenario._delete_floating_ip.assert_called_once_with(fake_floating_ip)
