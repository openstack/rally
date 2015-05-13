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


import subprocess

import mock
import netaddr
from oslotest import mockpatch
import six

from rally import exceptions
from rally.plugins.openstack.scenarios.vm import utils
from tests.unit import test

VMTASKS_UTILS = "rally.plugins.openstack.scenarios.vm.utils"


class VMScenarioTestCase(test.TestCase):

    def setUp(self):
        super(VMScenarioTestCase, self).setUp()
        self.wait_for = mockpatch.Patch(VMTASKS_UTILS +
                                        ".bench_utils.wait_for")
        self.useFixture(self.wait_for)

    @mock.patch("%s.open" % VMTASKS_UTILS,
                side_effect=mock.mock_open(), create=True)
    def test__run_command_over_ssh(self, mock_open):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario()
        vm_scenario._run_command_over_ssh(mock_ssh, "interpreter", "script")
        mock_ssh.execute.assert_called_once_with("interpreter",
                                                 stdin=mock_open.side_effect())

    def test__run_command_over_ssh_stringio(self):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario()
        script = six.moves.StringIO("script")
        vm_scenario._run_command_over_ssh(mock_ssh, "interpreter", script)
        mock_ssh.execute.assert_called_once_with("interpreter",
                                                 stdin=script)

    def test__run_command_over_ssh_fails(self):
        vm_scenario = utils.VMScenario()
        self.assertRaises(exceptions.ScriptError,
                          vm_scenario._run_command_over_ssh,
                          None, "interpreter", 10)

    def test__wait_for_ssh(self):
        ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario()
        vm_scenario._wait_for_ssh(ssh)
        ssh.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".bench_utils.resource_is")
    @mock.patch(VMTASKS_UTILS + ".VMScenario._ping_ip_address",
                return_value=True)
    def test__wait_for_ping(self, mock__ping, mock_resource_is):
        vm_scenario = utils.VMScenario()
        vm_scenario._wait_for_ping(netaddr.IPAddress("1.2.3.4"))
        self.wait_for.mock.assert_called_once_with(
            netaddr.IPAddress("1.2.3.4"),
            is_ready=mock_resource_is.return_value,
            timeout=120)
        mock_resource_is.assert_called_once_with("ICMP UP", mock__ping)

    @mock.patch(VMTASKS_UTILS + ".VMScenario._run_command_over_ssh")
    @mock.patch("rally.common.sshutils.SSH")
    def test__run_command(self, mock_ssh_class, mock_run_command_over_ssh):
        mock_ssh_instance = mock.MagicMock()
        mock_ssh_class.return_value = mock_ssh_instance

        vm_scenario = utils.VMScenario()
        vm_scenario.context = {"user": {"keypair": {"private": "ssh"}}}
        vm_scenario._run_command("1.2.3.4", 22, "username",
                                 "password", "int", "/path/to/foo/script.sh",
                                 is_file=True)

        mock_ssh_class.assert_called_once_with("username", "1.2.3.4", port=22,
                                               pkey="ssh",
                                               password="password")
        mock_ssh_instance.wait.assert_called_once_with()
        mock_run_command_over_ssh.assert_called_once_with(
            mock_ssh_instance, "int", "/path/to/foo/script.sh", True)

    @mock.patch(VMTASKS_UTILS + ".sshutils.SSH")
    def test__run_command_inline_script(self, mock_ssh):
        mock_ssh_instance = mock.MagicMock()
        mock_ssh.return_value = mock_ssh_instance
        mock_ssh_instance.execute.return_value = "foobar"
        vm_scenario = utils.VMScenario()
        vm_scenario._wait_for_ssh = mock.Mock()
        vm_scenario.context = {"user": {"keypair": {"private": "foo_pkey"}}}
        result = vm_scenario._run_command("foo_ip", "foo_port", "foo_username",
                                          "foo_password", "foo_interpreter",
                                          "foo_script", is_file=False)
        mock_ssh.assert_called_once_with("foo_username", "foo_ip",
                                         port="foo_port", pkey="foo_pkey",
                                         password="foo_password")
        vm_scenario._wait_for_ssh.assert_called_once_with(mock_ssh_instance)
        mock_ssh_instance.execute.assert_called_once_with("foo_interpreter",
                                                          stdin="foo_script")
        self.assertEqual(result, "foobar")

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_linux(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "linux2"

        vm_scenario = utils.VMScenario()
        host_ip = netaddr.IPAddress("1.2.3.4")
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
            ["ping", "-c1", "-w1", str(host_ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_linux_ipv6(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "linux2"

        vm_scenario = utils.VMScenario()
        host_ip = netaddr.IPAddress("1ce:c01d:bee2:15:a5:900d:a5:11fe")
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
            ["ping6", "-c1", "-w1", str(host_ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_other_os(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "freebsd10"

        vm_scenario = utils.VMScenario()
        host_ip = netaddr.IPAddress("1.2.3.4")
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
            ["ping", "-c1", str(host_ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_other_os_ipv6(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "freebsd10"

        vm_scenario = utils.VMScenario()
        host_ip = netaddr.IPAddress("1ce:c01d:bee2:15:a5:900d:a5:11fe")
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
            ["ping6", "-c1", str(host_ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    def get_scenario(self):
        server = mock.Mock(
            networks={"foo_net": "foo_data"},
            addresses={"foo_net": [{"addr": "foo_ip"}]},
            tenant_id="foo_tenant"
        )
        scenario = utils.VMScenario(context={})

        scenario._boot_server = mock.Mock(return_value=server)
        scenario._delete_server = mock.Mock()
        scenario._associate_floating_ip = mock.Mock()
        scenario._wait_for_ping = mock.Mock()

        return scenario, server

    def test__boot_server_with_fip_without_networks(self):
        scenario, server = self.get_scenario()
        server.networks = {}
        self.assertRaises(RuntimeError,
                          scenario._boot_server_with_fip,
                          "foo_image", "foo_flavor", foo_arg="foo_value")
        scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            foo_arg="foo_value", auto_assign_nic=True)

    def test__boot_server_with_fixed_ip(self):
        scenario, server = self.get_scenario()
        scenario._attach_floating_ip = mock.Mock()
        server, ip = scenario._boot_server_with_fip(
            "foo_image", "foo_flavor", floating_network="ext_network",
            use_floating_ip=False, wait_for_ping=True, foo_arg="foo_value")

        self.assertEqual(ip, {"ip": "foo_ip", "id": None,
                              "is_floating": False})
        scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            auto_assign_nic=True, foo_arg="foo_value")
        self.assertEqual(scenario._attach_floating_ip.mock_calls, [])
        scenario._wait_for_ping.assert_called_once_with("foo_ip")

    def test__boot_server_with_fip(self):
        scenario, server = self.get_scenario()
        scenario._attach_floating_ip = mock.Mock(
            return_value={"id": "foo_id", "ip": "foo_ip"})
        server, ip = scenario._boot_server_with_fip(
            "foo_image", "foo_flavor", floating_network="ext_network",
            use_floating_ip=True, wait_for_ping=True, foo_arg="foo_value")
        self.assertEqual(ip, {"ip": "foo_ip", "id": "foo_id",
                              "is_floating": True})

        scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            auto_assign_nic=True, foo_arg="foo_value")
        scenario._attach_floating_ip.assert_called_once_with(
            server, "ext_network")
        scenario._wait_for_ping.assert_called_once_with("foo_ip")

    def test__delete_server_with_fixed_ip(self):
        ip = {"ip": "foo_ip", "id": None, "is_floating": False}
        scenario, server = self.get_scenario()
        scenario._delete_floating_ip = mock.Mock()
        scenario._delete_server_with_fip(server, ip, force_delete=True)

        self.assertEqual(scenario._delete_floating_ip.mock_calls, [])
        scenario._delete_server.assert_called_once_with(server, force=True)

    def test__delete_server_with_fip(self):
        fip = {"ip": "foo_ip", "id": "foo_id", "is_floating": True}
        scenario, server = self.get_scenario()
        scenario._delete_floating_ip = mock.Mock()
        scenario._delete_server_with_fip(server, fip, force_delete=True)

        scenario._delete_floating_ip.assert_called_once_with(server, fip)
        scenario._delete_server.assert_called_once_with(server, force=True)

    @mock.patch(VMTASKS_UTILS + ".network_wrapper.wrap")
    def test__attach_floating_ip(self, mock_wrap):
        scenario, server = self.get_scenario()

        netwrap = mock_wrap.return_value
        netwrap.create_floating_ip.return_value = {
            "id": "foo_id", "ip": "foo_ip"}

        scenario._attach_floating_ip(
            server, floating_network="bar_network")

        mock_wrap.assert_called_once_with(scenario.clients)
        netwrap.create_floating_ip.assert_called_once_with(
            ext_network="bar_network", int_network="foo_net",
            tenant_id="foo_tenant", fixed_ip="foo_ip")

        scenario._associate_floating_ip.assert_called_once_with(
            server, "foo_ip", fixed_address="foo_ip")

    @mock.patch(VMTASKS_UTILS + ".network_wrapper.wrap")
    def test__delete_floating_ip(self, mock_wrap):
        scenario, server = self.get_scenario()

        _check_addr = mock.Mock(return_value=True)
        scenario.check_ip_address = mock.Mock(return_value=_check_addr)
        scenario._dissociate_floating_ip = mock.Mock()

        scenario._delete_floating_ip(
            server, fip={"id": "foo_id", "ip": "foo_ip"})

        scenario.check_ip_address.assert_called_once_with(
            "foo_ip")
        _check_addr.assert_called_once_with(server)
        scenario._dissociate_floating_ip.assert_called_once_with(
            server, "foo_ip")
        mock_wrap.assert_called_once_with(scenario.clients)
        mock_wrap.return_value.delete_floating_ip.assert_called_once_with(
            "foo_id", wait=True)
