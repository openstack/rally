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

import os

import ddt
import mock

from rally.common import validation
from rally import exceptions
from rally.plugins.openstack.scenarios.vm import vmtasks
from tests.unit import test


BASE = "rally.plugins.openstack.scenarios.vm.vmtasks"


@ddt.ddt
class VMTasksTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(VMTasksTestCase, self).setUp()
        self.context.update({"user": {"keypair": {"name": "keypair_name"},
                                      "credential": mock.MagicMock()}})

        cinder_patcher = mock.patch(
            "rally.plugins.openstack.services.storage.block.BlockStorage")
        self.cinder = cinder_patcher.start().return_value
        self.cinder.create_volume.return_value = mock.Mock(id="foo_volume")
        self.addCleanup(cinder_patcher.stop)

    def create_env(self, scenario):
        self.ip = {"id": "foo_id", "ip": "foo_ip", "is_floating": True}
        scenario._boot_server_with_fip = mock.Mock(
            return_value=("foo_server", self.ip))
        scenario._wait_for_ping = mock.Mock()
        scenario._delete_server_with_fip = mock.Mock()
        scenario._run_command = mock.MagicMock(
            return_value=(0, "{\"foo\": 42}", "foo_err"))
        scenario.add_output = mock.Mock()
        return scenario

    def test_boot_runcommand_delete(self):
        scenario = self.create_env(vmtasks.BootRuncommandDelete(self.context))
        scenario._run_command = mock.MagicMock(
            return_value=(0, "{\"foo\": 42}", "foo_err"))
        scenario.run("foo_flavor", image="foo_image",
                     command={"script_file": "foo_script",
                              "interpreter": "foo_interpreter"},
                     username="foo_username",
                     password="foo_password",
                     use_floating_ip="use_fip",
                     floating_network="ext_network",
                     force_delete="foo_force",
                     volume_args={"size": 16},
                     foo_arg="foo_value")

        self.cinder.create_volume.assert_called_once_with(16, imageRef=None)
        scenario._boot_server_with_fip.assert_called_once_with(
            "foo_image", "foo_flavor", key_name="keypair_name",
            use_floating_ip="use_fip", floating_network="ext_network",
            block_device_mapping={"vdrally": "foo_volume:::1"},
            foo_arg="foo_value")

        scenario._wait_for_ping.assert_called_once_with("foo_ip")
        scenario._run_command.assert_called_once_with(
            "foo_ip", 22, "foo_username", "foo_password",
            command={"script_file": "foo_script",
                     "interpreter": "foo_interpreter"})
        scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete="foo_force")
        scenario.add_output.assert_called_once_with(
            complete={"chart_plugin": "TextArea",
                      "data": [
                          "StdErr: foo_err",
                          "StdOut:",
                          "{\"foo\": 42}"],
                      "title": "Script Output"})

    @ddt.data(
        {"output": (0, "", ""),
         "expected": [{"complete": {"chart_plugin": "TextArea",
                                    "data": [
                                        "StdErr: (none)",
                                        "StdOut:",
                                        ""],
                                    "title": "Script Output"}}]},
        {"output": (1, "{\"foo\": 42}", ""), "raises": exceptions.ScriptError},
        {"output": ("", 1, ""), "raises": TypeError},
        {"output": (0, "{\"foo\": 42}", ""),
         "expected": [{"complete": {"chart_plugin": "TextArea",
                                    "data": [
                                        "StdErr: (none)",
                                        "StdOut:",
                                        "{\"foo\": 42}"],
                                    "title": "Script Output"}}]},
        {"output": (0, "{\"additive\": [1, 2]}", ""),
         "expected": [{"complete": {"chart_plugin": "TextArea",
                                    "data": [
                                        "StdErr: (none)",
                                        "StdOut:", "{\"additive\": [1, 2]}"],
                                    "title": "Script Output"}}]},
        {"output": (0, "{\"complete\": [3, 4]}", ""),
         "expected": [{"complete": {"chart_plugin": "TextArea",
                                    "data": [
                                        "StdErr: (none)",
                                        "StdOut:",
                                        "{\"complete\": [3, 4]}"],
                                    "title": "Script Output"}}]},
        {"output": (0, "{\"additive\": [1, 2], \"complete\": [3, 4]}", ""),
         "expected": [{"additive": 1}, {"additive": 2},
                      {"complete": 3}, {"complete": 4}]}
    )
    @ddt.unpack
    def test_boot_runcommand_delete_add_output(self, output,
                                               expected=None, raises=None):
        scenario = self.create_env(vmtasks.BootRuncommandDelete(self.context))

        scenario._run_command.return_value = output
        kwargs = {"flavor": "foo_flavor",
                  "image": "foo_image",
                  "command": {"remote_path": "foo"},
                  "username": "foo_username",
                  "password": "foo_password",
                  "use_floating_ip": "use_fip",
                  "floating_network": "ext_network",
                  "force_delete": "foo_force",
                  "volume_args": {"size": 16},
                  "foo_arg": "foo_value"}
        if raises:
            self.assertRaises(raises, scenario.run, **kwargs)
            self.assertFalse(scenario.add_output.called)
        else:
            scenario.run(**kwargs)
            calls = [mock.call(**kw) for kw in expected]
            scenario.add_output.assert_has_calls(calls, any_order=True)

            self.cinder.create_volume.assert_called_once_with(
                16, imageRef=None)
            scenario._boot_server_with_fip.assert_called_once_with(
                "foo_image", "foo_flavor", key_name="keypair_name",
                use_floating_ip="use_fip", floating_network="ext_network",
                block_device_mapping={"vdrally": "foo_volume:::1"},
                foo_arg="foo_value")

            scenario._run_command.assert_called_once_with(
                "foo_ip", 22, "foo_username", "foo_password",
                command={"remote_path": "foo"})
            scenario._delete_server_with_fip.assert_called_once_with(
                "foo_server", self.ip, force_delete="foo_force")

    def test_boot_runcommand_delete_command_timeouts(self):
        scenario = self.create_env(vmtasks.BootRuncommandDelete(self.context))

        scenario._run_command.side_effect = exceptions.SSHTimeout()
        self.assertRaises(exceptions.SSHTimeout,
                          scenario.run,
                          "foo_flavor", "foo_image", "foo_interpreter",
                          "foo_script", "foo_username")
        scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)
        self.assertFalse(scenario.add_output.called)

    def test_boot_runcommand_delete_ping_wait_timeouts(self):
        scenario = self.create_env(vmtasks.BootRuncommandDelete(self.context))

        scenario._wait_for_ping.side_effect = exceptions.TimeoutException(
            resource_type="foo_resource",
            resource_name="foo_name",
            resource_id="foo_id",
            desired_status="foo_desired_status",
            resource_status="foo_resource_status",
            timeout=2)
        exc = self.assertRaises(exceptions.TimeoutException,
                                scenario.run,
                                "foo_image", "foo_flavor", "foo_interpreter",
                                "foo_script", "foo_username",
                                wait_for_ping=True)
        self.assertEqual(exc.kwargs["resource_type"], "foo_resource")
        self.assertEqual(exc.kwargs["resource_name"], "foo_name")
        self.assertEqual(exc.kwargs["resource_id"], "foo_id")
        self.assertEqual(exc.kwargs["desired_status"], "foo_desired_status")
        self.assertEqual(exc.kwargs["resource_status"], "foo_resource_status")

        scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)
        self.assertFalse(scenario.add_output.called)

    @mock.patch("%s.json" % BASE)
    def test_boot_runcommand_delete_json_fails(self, mock_json):
        scenario = self.create_env(vmtasks.BootRuncommandDelete(self.context))

        mock_json.loads.side_effect = ValueError()
        scenario.run("foo_image", "foo_flavor", "foo_interpreter",
                     "foo_script", "foo_username")
        scenario.add_output.assert_called_once_with(complete={
            "chart_plugin": "TextArea", "data": ["StdErr: foo_err",
                                                 "StdOut:", "{\"foo\": 42}"],
            "title": "Script Output"})
        scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete=False)

    def test_boot_runcommand_delete_custom_image(self):
        context = {
            "user": {
                "tenant_id": "tenant_id",
                "keypair": {"name": "foo_keypair_name"},
                "credential": mock.Mock()
            },
            "tenant": {
                "custom_image": {"id": "image_id"}
            }
        }

        scenario = self.create_env(vmtasks.BootRuncommandDelete(context))
        scenario._run_command = mock.MagicMock(
            return_value=(0, "{\"foo\": 42}", "foo_err"))
        scenario.run("foo_flavor",
                     command={"script_file": "foo_script",
                              "interpreter": "foo_interpreter"},
                     username="foo_username",
                     password="foo_password",
                     use_floating_ip="use_fip",
                     floating_network="ext_network",
                     force_delete="foo_force",
                     volume_args={"size": 16},
                     foo_arg="foo_value")

        self.cinder.create_volume.assert_called_once_with(16, imageRef=None)
        scenario._boot_server_with_fip.assert_called_once_with(
            "image_id", "foo_flavor", key_name="foo_keypair_name",
            use_floating_ip="use_fip", floating_network="ext_network",
            block_device_mapping={"vdrally": "foo_volume:::1"},
            foo_arg="foo_value")

        scenario._wait_for_ping.assert_called_once_with("foo_ip")
        scenario._run_command.assert_called_once_with(
            "foo_ip", 22, "foo_username", "foo_password",
            command={"script_file": "foo_script",
                     "interpreter": "foo_interpreter"})
        scenario._delete_server_with_fip.assert_called_once_with(
            "foo_server", self.ip, force_delete="foo_force")
        scenario.add_output.assert_called_once_with(
            complete={"chart_plugin": "TextArea",
                      "data": [
                          "StdErr: foo_err",
                          "StdOut:", "{\"foo\": 42}"],
                      "title": "Script Output"})

    @mock.patch("%s.heat" % BASE)
    @mock.patch("%s.sshutils" % BASE)
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
                     "credential": mock.MagicMock()},
            "tenant": {"networks": [{"router_id": "1"}]}
        }
        scenario = vmtasks.RuncommandHeat(context)
        scenario.generate_random_name = mock.Mock(return_value="name")
        scenario.add_output = mock.Mock()
        workload = {"username": "admin",
                    "resource": ["foo", "bar"]}
        scenario.run(workload, "template",
                     {"file_key": "file_value"},
                     {"param_key": "param_value"})
        expected = {"chart_plugin": "Table",
                    "data": {"rows": [["key", "val"]],
                             "cols": ["key", "value"]},
                    "description": "Data generated by workload",
                    "title": "Workload summary"}
        scenario.add_output.assert_called_once_with(complete=expected)


@ddt.ddt
class ValidCommandValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ValidCommandValidatorTestCase, self).setUp()
        self.context = {"admin": {"credential": mock.MagicMock()},
                        "users": [{"credential": mock.MagicMock()}]}

    @ddt.data({"command": {"script_inline": "foobar",
                           "interpreter": ["ENV=bar", "/bin/foo"],
                           "local_path": "bar",
                           "remote_path": "/bin/foo"}},
              {"command": {"script_inline": "foobar", "interpreter": "foo"}})
    @ddt.unpack
    def test_check_command_dict(self, command=None):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)
        self.assertIsNone(validator.check_command_dict(command))

    @ddt.data({"raises_message": "Command must be a dictionary"},
              {"command": "foo",
               "raises_message": "Command must be a dictionary"},
              {"command": {"interpreter": "foobar", "script_file": "foo",
                           "script_inline": "bar"},
               "raises_message": "Exactly one of "},
              {"command": {"script_file": "foobar"},
               "raises_message": "Supplied dict specifies no"},
              {"command": {"script_inline": "foobar",
                           "interpreter": "foo",
                           "local_path": "bar"},
               "raises_message": "When uploading an interpreter its path"},
              {"command": {"interpreter": "/bin/bash",
                           "script_path": "foo"},
               "raises_message": ("Unexpected command parameters: "
                                  "script_path")})
    @ddt.unpack
    def test_check_command_dict_failed(
            self, command=None, raises_message=None):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)
        e = self.assertRaises(
            validation.ValidationError,
            validator.check_command_dict, command)
        self.assertIn(raises_message, e.message)

    @mock.patch("rally.plugins.common.validators.FileExistsValidator"
                "._file_access_ok")
    def test_validate(self, mock__file_access_ok):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)
        mock__file_access_ok.return_value = None
        command = {"script_file": "foobar", "interpreter": "foo"}
        result = validator.validate(self.context, {"args": {"p": command}},
                                    None, None)
        self.assertIsNone(result)
        mock__file_access_ok.assert_called_once_with(
            filename="foobar", mode=os.R_OK, param_name="p",
            required=True)

    def test_valid_command_not_required(self):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=False)
        result = validator.validate(self.context, {"args": {"p": None}},
                                    None, None)
        self.assertIsNone(result)

    def test_valid_command_required(self):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)

        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, {"args": {"p": None}},
            self.context, None, None)
        self.assertEqual("Command must be a dictionary", e.message)

    @mock.patch("rally.plugins.common.validators.FileExistsValidator"
                "._file_access_ok")
    def test_valid_command_unreadable_script_file(self, mock__file_access_ok):
        mock__file_access_ok.side_effect = validation.ValidationError("O_o")

        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)

        command = {"script_file": "foobar", "interpreter": "foo"}
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, self.context, {"args": {"p": command}},
            None, None)
        self.assertEqual("O_o", e.message)

    @mock.patch("%s.ValidCommandValidator.check_command_dict" % BASE)
    def test_valid_command_fail_check_command_dict(self,
                                                   mock_check_command_dict):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)

        mock_check_command_dict.side_effect = validation.ValidationError(
            "foobar")
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, {"args": {"p": {"foo": "bar"}}},
            self.context, None, None)
        self.assertEqual("foobar", e.message)

    def test_valid_command_script_inline(self):
        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)

        command = {"script_inline": "bar", "interpreter": "/bin/sh"}
        result = validator.validate(self.context, {"args": {"p": command}},
                                    None, None)
        self.assertIsNone(result)

    @mock.patch("rally.plugins.common.validators.FileExistsValidator"
                "._file_access_ok")
    def test_valid_command_local_path(self, mock__file_access_ok):
        mock__file_access_ok.side_effect = validation.ValidationError("")

        validator = vmtasks.ValidCommandValidator(param_name="p",
                                                  required=True)

        command = {"remote_path": "bar", "local_path": "foobar"}
        self.assertRaises(
            validation.ValidationError,
            validator.validate, self.context, {"args": {"p": command}},
            None, None)
        mock__file_access_ok.assert_called_once_with(
            filename="foobar", mode=os.R_OK, param_name="p",
            required=True)
