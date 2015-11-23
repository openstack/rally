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

import os

import jsonschema
import mock
import netaddr
from oslotest import mockpatch

from rally.deployment.serverprovider.providers import virsh
from tests.unit import test


class VirshProviderTestCase(test.TestCase):
    def setUp(self):
        super(VirshProviderTestCase, self).setUp()
        self.deployment = mock.Mock()
        self.config = {
            "type": "VirshProvider",
            "connection": "user@host",
            "template_name": "prefix",
            "template_user": "user",
            "template_password": "password",
        }
        self.provider = virsh.VirshProvider(self.deployment, self.config)
        self.useFixture(mockpatch.PatchObject(self.provider, "resources"))

    @mock.patch(
        "rally.deployment.serverprovider.providers.virsh.netaddr.IPAddress")
    @mock.patch("rally.deployment.serverprovider.providers.virsh.subprocess")
    @mock.patch("time.sleep")
    def test_create_vm(self, mock_sleep, mock_subprocess, mock_ip_address):
        mock_subprocess.check_output.return_value = "10.0.0.1"
        mock_ip_address.return_value = "10.0.0.2"
        server = self.provider.create_vm("name")
        script_path = ("%s/virsh/get_domain_ip.sh" %
                       os.path.split(virsh.__file__)[0])
        mock_subprocess.assert_has_calls([
            mock.call.check_call(
                ["virt-clone", "--connect=qemu+ssh://user@host/system",
                 "-o", "prefix", "-n", "name", "--auto-clone"]),
            mock.call.check_call(
                ["virsh", "--connect=qemu+ssh://user@host/system",
                 "start", "name"]),
            mock.call.check_call(
                ["scp", "-o StrictHostKeyChecking=no", script_path,
                 "user@host:~/get_domain_ip.sh"]),
            mock.call.check_output(["ssh", "-o StrictHostKeyChecking=no",
                                    "user@host", "./get_domain_ip.sh",
                                    "name"]),
        ])
        mock_ip_address.assert_called_once_with("10.0.0.1")
        self.assertEqual(server.host, "10.0.0.2")
        self.assertEqual(server.user, "user")
        self.assertIsNone(server.key)
        self.assertEqual(server.password, "password")
        self.provider.resources.create.assert_called_once_with({
            "name": "name",
        })

    @mock.patch(
        "rally.deployment.serverprovider.providers.virsh.netaddr.IPAddress")
    @mock.patch("rally.deployment.serverprovider.providers.virsh.subprocess")
    @mock.patch("time.sleep")
    def test_create_vm_ip_failed(self, mock_sleep, mock_subprocess,
                                 mock_ip_address):
        mock_ip_address.side_effect = netaddr.core.AddrFormatError
        server = self.provider.create_vm("name")
        mock_subprocess.assert_has_calls(3 * [
            mock.call.check_output(["ssh", "-o StrictHostKeyChecking=no",
                                    "user@host", "./get_domain_ip.sh",
                                    "name"]),
        ])
        self.assertEqual(server.host, "None")

    @mock.patch("rally.deployment.serverprovider.providers.virsh.subprocess")
    def test_destroy_vm(self, mock_subprocess):
        self.provider.destroy_vm("uuid")
        mock_subprocess.assert_has_calls([
            mock.call.check_call(
                ["virsh", "--connect=qemu+ssh://user@host/system",
                 "destroy", "uuid"]),
            mock.call.check_call(
                ["virsh", "--connect=qemu+ssh://user@host/system",
                 "undefine", "uuid", "--remove-all-storage"]),
        ])

    @mock.patch("rally.deployment.serverprovider.providers.virsh.uuid")
    @mock.patch.object(virsh.VirshProvider, "create_vm")
    def test_create_servers(self, mock_create_vm, mock_uuid):
        mock_uuid.uuid4.side_effect = ["1", "2", "3"]
        mock_create_vm.side_effect = ["s1", "s2", "s3"]
        servers = self.provider.create_servers(amount=3)
        self.assertEqual(servers, ["s1", "s2", "s3"])
        mock_create_vm.assert_has_calls([
            mock.call("1"),
            mock.call("2"),
            mock.call("3"),
        ])

    @mock.patch.object(virsh.VirshProvider, "destroy_vm")
    def test_destroy_servers(self, mock_destroy_vm):
        self.provider.resources.get_all.return_value = [
            {"info": {"name": "1"}},
            {"info": {"name": "2"}},
            {"info": {"name": "3"}},
        ]
        self.provider.destroy_servers()
        mock_destroy_vm.assert_has_calls([
            mock.call("1"),
            mock.call("2"),
            mock.call("3"),
        ])
        self.provider.resources.get_all.assert_called_once_with()

    def test_invalid_config(self):
        self.config["type"] = 42
        self.assertRaises(jsonschema.ValidationError, virsh.VirshProvider,
                          self.deployment, self.config)

    def test_invalid_connection(self):
        self.config["connection"] = "user host"
        self.assertRaises(jsonschema.ValidationError, virsh.VirshProvider,
                          self.deployment, self.config)
