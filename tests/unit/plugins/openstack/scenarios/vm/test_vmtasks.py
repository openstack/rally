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

import ddt
import mock

from rally import exceptions
from rally.plugins.openstack.scenarios.vm import vmtasks
from tests.unit import test


@ddt.ddt
class VMTasksTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(VMTasksTestCase, self).setUp()
        self.context.update({"user": {"keypair": {"name": "keypair_name"},
                                      "credential": mock.MagicMock()}})
        self.scenario = vmtasks.VMTasks(context=self.context)
        self.ip = {"id": "foo_id", "ip": "foo_ip", "is_floating": True}
        self.scenario._boot_server_with_fip = mock.Mock(
            return_value=("foo_server", self.ip))
        self.scenario._wait_for_ping = mock.Mock()
        self.scenario._delete_server_with_fip = mock.Mock()
        self.scenario._create_volume = mock.Mock(
            return_value=mock.Mock(id="foo_volume"))
        self.scenario._run_command = mock.MagicMock(
            return_value=(0, "{\"foo\": 42}", "foo_err"))
        self.scenario.add_output = mock.Mock()

    def test_boot_runcommand_delete(self):
        self.scenario._run_command = mock.MagicMock(
            return_value=(0, "{\"foo\": 42}", "foo_err"))
        self.scenario.boot_runcommand_delete(
            "foo_image", "foo_flavor",
            command={"script_file": "foo_script",
                     "interpreter": "foo_interpreter"},
            username="foo_username",
            password="foo_password",
            use_floating_ip="use_fip",
            floating_network="ext_network",
            force_delete="foo_force",
            volume_args={"size": 16},
            foo_arg="foo_value")

        self.scenario._create_volume.assert_called_once_with(
            16, imageRef=None)
        self.scenario._boot_server_with_fip.assert_called_once_with(
            "foo_image", "foo_flavor", key_name="keypair_name",
            use_floating_ip="use_fip", floating_network="ext_network",
            block_device_mapping={"vdrally": "foo_volume:::1"},
            foo_arg="foo_value")

        self.scenario._wait_for_ping.assert_called_once_with("foo_ip")
        self.scenario._run_command.assert_called_once_with(
            "foo_ip", 22, "foo_username", "foo_password",
            command={"script_file": "foo_script",
                     "interpreter": "foo_interpreter"})
        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete="foo_force")
        self.scenario.add_output.assert_called_once_with(
            additive={"title": "Command output", "chart_plugin": "Lines",
                      "data": [["foo", 42.0]]})

    @ddt.data(
        {"output": (0, "", ""), "raises": exceptions.ScriptError},
        {"output": (0, "{\"foo\": 42}", ""),
         "expected": [{"additive": {"chart_plugin": "Lines",
                                    "data": [["foo", 42.0]],
                                    "title": "Command output"}}]},
        {"output": (1, "{\"foo\": 42}", ""), "raises": exceptions.ScriptError},
        {"output": ("", 1, ""), "raises": TypeError},
        {"output": (0, "{\"additive\": [1, 2]}", ""),
         "expected": [{"additive": 1}, {"additive": 2}]},
        {"output": (0, "{\"complete\": [3, 4]}", ""),
         "expected": [{"complete": 3}, {"complete": 4}]},
        {"output": (0, "{\"additive\": [1, 2], \"complete\": [3, 4]}", ""),
         "expected": [{"additive": 1}, {"additive": 2},
                      {"complete": 3}, {"complete": 4}]}
    )
    @ddt.unpack
    def test_boot_runcommand_delete_add_output(self, output,
                                               expected=None, raises=None):
        self.scenario._run_command.return_value = output
        kwargs = {"command": {"remote_path": "foo"},
                  "username": "foo_username",
                  "password": "foo_password",
                  "use_floating_ip": "use_fip",
                  "floating_network": "ext_network",
                  "force_delete": "foo_force",
                  "volume_args": {"size": 16},
                  "foo_arg": "foo_value"}
        if raises:
            self.assertRaises(raises, self.scenario.boot_runcommand_delete,
                              "foo_image", "foo_flavor", **kwargs)
            self.assertFalse(self.scenario.add_output.called)
        else:
            self.scenario.boot_runcommand_delete("foo_image", "foo_flavor",
                                                 **kwargs)
            calls = [mock.call(**kw) for kw in expected]
            self.scenario.add_output.assert_has_calls(calls, any_order=True)

            self.scenario._create_volume.assert_called_once_with(
                16, imageRef=None)
            self.scenario._boot_server_with_fip.assert_called_once_with(
                "foo_image", "foo_flavor", key_name="keypair_name",
                use_floating_ip="use_fip", floating_network="ext_network",
                block_device_mapping={"vdrally": "foo_volume:::1"},
                foo_arg="foo_value")

            self.scenario._run_command.assert_called_once_with(
                "foo_ip", 22, "foo_username", "foo_password",
                command={"remote_path": "foo"})
            self.scenario._delete_server_with_fip.assert_called_once_with(
                "foo_server", self.ip, force_delete="foo_force")

    def test_boot_runcommand_delete_command_timeouts(self):
        self.scenario._run_command.side_effect = exceptions.SSHTimeout()
        self.assertRaises(exceptions.SSHTimeout,
                          self.scenario.boot_runcommand_delete,
                          "foo_image", "foo_flavor", "foo_interpreter",
                          "foo_script", "foo_username")
        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)
        self.assertFalse(self.scenario.add_output.called)

    def test_boot_runcommand_delete_ping_wait_timeouts(self):
        self.scenario._wait_for_ping.side_effect = exceptions.TimeoutException(
            resource_type="foo_resource",
            resource_name="foo_name",
            resource_id="foo_id",
            desired_status="foo_desired_status",
            resource_status="foo_resource_status")
        exc = self.assertRaises(exceptions.TimeoutException,
                                self.scenario.boot_runcommand_delete,
                                "foo_image", "foo_flavor", "foo_interpreter",
                                "foo_script", "foo_username",
                                wait_for_ping=True)
        self.assertEqual(exc.kwargs["resource_type"], "foo_resource")
        self.assertEqual(exc.kwargs["resource_name"], "foo_name")
        self.assertEqual(exc.kwargs["resource_id"], "foo_id")
        self.assertEqual(exc.kwargs["desired_status"], "foo_desired_status")
        self.assertEqual(exc.kwargs["resource_status"], "foo_resource_status")

        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)
        self.assertFalse(self.scenario.add_output.called)

    @mock.patch("rally.plugins.openstack.scenarios.vm.vmtasks.json")
    def test_boot_runcommand_delete_json_fails(self, mock_json):
        mock_json.loads.side_effect = ValueError()
        self.assertRaises(exceptions.ScriptError,
                          self.scenario.boot_runcommand_delete,
                          "foo_image", "foo_flavor", "foo_interpreter",
                          "foo_script", "foo_username")
        self.scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)
        self.assertFalse(self.scenario.add_output.called)

    def test_boot_runcommand_delete_custom_image(self):
        context = {
            "user": {
                "tenant_id": "tenant_id",
                "credential": mock.Mock()
            },
            "tenant": {
                "custom_image": {"id": "image_id"}
            }
        }
        scenario = vmtasks.VMTasks(context)

        scenario.boot_runcommand_delete = mock.Mock()

        scenario.boot_runcommand_delete_custom_image(
            flavor="flavor_id",
            command={
                "script_file": "foo_script",
                "interpreter": "bar_interpreter"},
            username="username")

        scenario.boot_runcommand_delete.assert_called_once_with(
            image="image_id", flavor="flavor_id", username="username",
            command={
                "script_file": "foo_script",
                "interpreter": "bar_interpreter"}
        )

    @mock.patch("rally.plugins.openstack.scenarios.vm.vmtasks.heat")
    @mock.patch("rally.plugins.openstack.scenarios.vm.vmtasks.sshutils")
    def test_runcommand_heat(self, mock_sshutils, mock_heat):
        fake_ssh = mock.Mock()
        fake_ssh.execute.return_value = [0, "key:val", ""]
        mock_sshutils.SSH.return_value = fake_ssh
        fake_stack = mock.Mock()
        fake_stack.stack.outputs = [{"output_key": "gate_node",
                                     "output_value": "ok"}]
        mock_heat.main.Stack.return_value = fake_stack
        context = {
            "user": {"keypair": {"name": "name", "private": "pk"},
                     "credential": "ok"},
            "tenant": {"networks": [{"router_id": "1"}]}
        }
        scenario = vmtasks.VMTasks(context)
        scenario.generate_random_name = mock.Mock(return_value="name")
        scenario.add_output = mock.Mock()
        workload = {"username": "admin",
                    "resource": ["foo", "bar"]}
        scenario.runcommand_heat(workload, "template",
                                 {"file_key": "file_value"},
                                 {"param_key": "param_value"})
        expected = {"chart_plugin": "Table",
                    "data": {"rows": [["key", "val"]],
                             "cols": ["key", "value"]},
                    "description": "Data generated by workload",
                    "title": "Workload summary"}
        scenario.add_output.assert_called_once_with(complete=expected)
