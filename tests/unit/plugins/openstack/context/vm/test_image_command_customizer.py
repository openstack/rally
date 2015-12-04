# Copyright 2015: Mirantis Inc.
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

"""Tests for the image customizer using a command execution."""

import mock

from rally import exceptions
from rally.plugins.openstack.context.vm import image_command_customizer
from tests.unit import test

BASE = "rally.plugins.openstack.context.vm.image_command_customizer"


class ImageCommandCustomizerContextVMTestCase(test.TestCase):

    def setUp(self):
        super(ImageCommandCustomizerContextVMTestCase, self).setUp()

        self.context = {
            "task": mock.MagicMock(),
            "config": {
                "image_command_customizer": {
                    "image": {"name": "image"},
                    "flavor": {"name": "flavor"},
                    "username": "fedora",
                    "password": "foo_password",
                    "floating_network": "floating",
                    "port": 1022,
                    "command": {
                        "interpreter": "foo_interpreter",
                        "script_file": "foo_script"
                    }
                }
            },
            "admin": {
                "credential": "credential",
            }
        }

        self.user = {"keypair": {"private": "foo_private"}}
        self.fip = {"ip": "foo_ip"}

    @mock.patch("%s.vm_utils.VMScenario" % BASE)
    def test_customize_image(self, mock_vm_scenario):
        mock_vm_scenario.return_value._run_command.return_value = (
            0, "foo_stdout", "foo_stderr")

        customizer = image_command_customizer.ImageCommandCustomizerContext(
            self.context)

        retval = customizer.customize_image(server=None, ip=self.fip,
                                            user=self.user)

        mock_vm_scenario.assert_called_once_with(customizer.context)
        mock_vm_scenario.return_value._run_command.assert_called_once_with(
            "foo_ip", 1022, "fedora", "foo_password", pkey="foo_private",
            command={"interpreter": "foo_interpreter",
                     "script_file": "foo_script"})

        self.assertEqual((0, "foo_stdout", "foo_stderr"), retval)

    @mock.patch("%s.vm_utils.VMScenario" % BASE)
    def test_customize_image_fail(self, mock_vm_scenario):
        mock_vm_scenario.return_value._run_command.return_value = (
            1, "foo_stdout", "foo_stderr")

        customizer = image_command_customizer.ImageCommandCustomizerContext(
            self.context)

        exc = self.assertRaises(
            exceptions.ScriptError, customizer.customize_image,
            server=None, ip=self.fip, user=self.user)

        str_exc = str(exc)
        self.assertIn("foo_stdout", str_exc)
        self.assertIn("foo_stderr", str_exc)

        mock_vm_scenario.return_value._run_command.assert_called_once_with(
            "foo_ip", 1022, "fedora", "foo_password", pkey="foo_private",
            command={"interpreter": "foo_interpreter",
                     "script_file": "foo_script"})
