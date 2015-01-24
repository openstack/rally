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

from rally.benchmark.context import keypair
from rally.benchmark.scenarios.vm import vmtasks
from rally import exceptions
from tests.unit import test


VM = "rally.benchmark.scenarios.vm."


class VMTasksTestCase(test.TestCase):

    def setUp(self):
        super(VMTasksTestCase, self).setUp()
        self.scenario = vmtasks.VMTasks()
        self.clients = mock.Mock()
        self.server = mock.Mock(networks={"foo_net": "foo_net_data"},
                                addresses={"foo_net": [{"addr": "foo_addr"}]},
                                tenant_id="foo_tenant")
        self.scenario._generate_random_name = mock.Mock(
            return_value="foo_name")
        self.scenario._create_volume = mock.Mock(
            return_value=mock.Mock(id="foo_volume"))
        self.scenario._boot_server = mock.MagicMock(return_value=self.server)
        self.scenario._associate_floating_ip = mock.MagicMock()
        self.scenario._delete_server = mock.MagicMock()
        self.scenario.run_command = mock.MagicMock(
            return_value=(0, '\"foo_out\"', "foo_err"))

    @mock.patch(VM + "vmtasks.network_wrapper")
    def test_boot_runcommand_delete_missed_networks(self, mock_wrap):
        net_wrap = mock.Mock()
        mock_wrap.wrap.return_value = net_wrap
        self.server.networks = {}
        self.assertRaises(RuntimeError,
                          self.scenario.boot_runcommand_delete,
                          "foo_image", "foo_flavor", "foo_script",
                          "foo_interpreter", "foo_username")

    @mock.patch(VM + "vmtasks.network_wrapper")
    def test_boot_runcommand_delete_script_fails(self, mock_wrap):
        self.scenario.run_command = mock.MagicMock(
            return_value=(1, '\"foo_out\"', "foo_err"))
        self.assertRaises(exceptions.ScriptError,
                          self.scenario.boot_runcommand_delete,
                          "foo_image", "foo_flavor", "foo_script",
                          "foo_interpreter", "foo_username")

    @mock.patch(VM + "vmtasks.network_wrapper")
    def test_boot_runcommand_delete_with_nic(self, mock_wrap):
        net_wrap = mock.Mock()
        mock_wrap.wrap.return_value = net_wrap
        net_wrap.create_floating_ip.return_value = {"id": "foo_id",
                                                    "ip": "foo_fip"}
        result = self.scenario.boot_runcommand_delete(
            "foo_image", "foo_flavor", "foo_script", "foo_shell", "foo_user",
            password="foo_password",
            volume_args={"size": 10}, nics=[{"net-id": "foo_network"}])

        self.assertEqual(result, {"errors": "foo_err", "data": "foo_out"})
        self.scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            block_device_mapping={"vdrally": "foo_volume:::1"},
            nics=[{"net-id": "foo_network"}], auto_assign_nic=True,
            key_name=keypair.Keypair.KEYPAIR_NAME)

        self.scenario._associate_floating_ip.assert_called_once_with(
            self.server, "foo_fip", fixed_address="foo_addr")
        self.scenario.run_command.assert_called_once_with(
            "foo_fip", 22, "foo_user", "foo_password",
            "foo_shell", "foo_script")
        self.scenario._delete_server.assert_called_once_with(self.server,
                                                             force=False)
        net_wrap.create_floating_ip.assert_called_once_with(
            tenant_id="foo_tenant", fixed_ip="foo_addr",
            int_network="foo_net", ext_network=None)

    @mock.patch(VM + "vmtasks.network_wrapper")
    def test_boot_runcommand_delete_auto_assign_nic(self, mock_wrap):
        net_wrap = mock.Mock()
        mock_wrap.wrap.return_value = net_wrap
        net_wrap.create_floating_ip.return_value = {"id": "foo_id",
                                                    "ip": "foo_fip"}
        self.scenario.boot_runcommand_delete(
            "foo_image", "foo_flavor", "foo_script", "foo_shell", "foo_user")

        self.scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor", auto_assign_nic=True,
            key_name=keypair.Keypair.KEYPAIR_NAME)
        self.scenario._associate_floating_ip.assert_called_once_with(
            self.server, "foo_fip", fixed_address="foo_addr")

    @mock.patch(VM + "vmtasks.network_wrapper")
    def test_boot_runcommand_delete_with_floating_network(self, mock_wrap):
        net_wrap = mock.Mock()
        mock_wrap.wrap.return_value = net_wrap
        net_wrap.create_floating_ip.return_value = {"id": "foo_id",
                                                    "ip": "foo_fip"}
        self.scenario.boot_runcommand_delete(
            "foo_image", "foo_flavor", "foo_script", "foo_shell", "foo_user",
            floating_network="bar_network")

        self.scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor", auto_assign_nic=True,
            key_name=keypair.Keypair.KEYPAIR_NAME)

        net_wrap.create_floating_ip.assert_called_once_with(
            tenant_id="foo_tenant", fixed_ip="foo_addr",
            int_network="foo_net", ext_network="bar_network")
