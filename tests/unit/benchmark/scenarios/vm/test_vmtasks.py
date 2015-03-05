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
from tests.unit import test


class VMTasksTestCase(test.TestCase):

    def setUp(self):
        super(VMTasksTestCase, self).setUp()
        self.scenario = vmtasks.VMTasks(
            context={"user": {"keypair": {"name": "keypair_name"}}})
        self.ip = {"id": "foo_id", "ip": "foo_ip", "is_floating": True}
        self.scenario._boot_server_with_fip = mock.Mock(
            return_value=("foo_server", self.ip))
        self.scenario._delete_server_with_fip = mock.Mock()
        self.scenario._create_volume = mock.Mock(
            return_value=mock.Mock(id="foo_volume"))
        self.scenario._run_command = mock.MagicMock(
            return_value=(0, "\"foo_out\"", "foo_err"))

    def test_boot_runcommand_delete(self):
        self.scenario.boot_runcommand_delete(
                "foo_image", "foo_flavor", "foo_script",
                "foo_interpreter", "foo_username",
                password="foo_password",
                use_floating_ip="use_fip",
                floating_network="ext_network",
                force_delete="foo_force",
                volume_args={"size": 16},
                foo_arg="foo_value")

        self.scenario._create_volume.assert_called_once_with(
            16, imageRef=None)
        self.scenario._boot_server_with_fip.assert_called_once_with(
            "foo_image", "foo_flavor", use_floating_ip="use_fip",
            floating_network="ext_network", key_name="keypair_name",
            block_device_mapping={"vdrally": "foo_volume:::1"},
            foo_arg="foo_value")

        self.scenario._run_command.assert_called_once_with(
            "foo_ip", 22, "foo_username", "foo_password",
            "foo_interpreter", "foo_script")
        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete="foo_force")

    def test_boot_runcommand_delete_script_fails(self):
        self.scenario._run_command = mock.MagicMock(
            return_value=(1, "\"foo_out\"", "foo_err"))
        self.assertRaises(exceptions.ScriptError,
                          self.scenario.boot_runcommand_delete,
                          "foo_image", "foo_flavor", "foo_interpreter",
                          "foo_script", "foo_username")
        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)

    @mock.patch("rally.benchmark.scenarios.vm.vmtasks.json")
    def test_boot_runcommand_delete_json_fails(self, mock_json):
        mock_json.loads.side_effect = ValueError()
        self.assertRaises(exceptions.ScriptError,
                          self.scenario.boot_runcommand_delete,
                          "foo_image", "foo_flavor", "foo_interpreter",
                          "foo_script", "foo_username")
        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)
