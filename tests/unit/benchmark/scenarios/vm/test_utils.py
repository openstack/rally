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
from oslotest import mockpatch
import six

from rally.benchmark.scenarios.vm import utils
from rally import exceptions
from tests.unit import test


VMTASKS_UTILS = "rally.benchmark.scenarios.vm.utils"


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

    @mock.patch(VMTASKS_UTILS + ".VMScenario._ping_ip_address",
                return_value=True)
    def test__wait_for_ping(self, mock__ping):
        vm_scenario = utils.VMScenario()
        vm_scenario._wait_for_ping("1.2.3.4")
        self.wait_for.mock.assert_called_once_with("1.2.3.4",
                                                   is_ready=mock__ping,
                                                   timeout=120)

    @mock.patch(VMTASKS_UTILS + ".VMScenario._run_command_over_ssh")
    @mock.patch("rally.common.sshutils.SSH")
    def test__run_command(self, mock_ssh_class, mock_run_command_over_ssh):
        mock_ssh_instance = mock.MagicMock()
        mock_ssh_class.return_value = mock_ssh_instance

        vm_scenario = utils.VMScenario()
        vm_scenario.context = {"user": {"keypair": {"private": "ssh"}}}
        vm_scenario._run_command("1.2.3.4", 22, "username",
                                 "password", "int", "script")

        mock_ssh_class.assert_called_once_with("username", "1.2.3.4", port=22,
                                               pkey="ssh",
                                               password="password")
        mock_ssh_instance.wait.assert_called_once_with()
        mock_run_command_over_ssh.assert_called_once_with(
            mock_ssh_instance, "int", "script")

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_linux(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "linux2"

        vm_scenario = utils.VMScenario()
        host_ip = "1.2.3.4"
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping", "-c1", "-w1", host_ip],
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
        host_ip = "1ce:c01d:bee2:15:a5:900d:a5:11fe"
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping6", "-c1", "-w1", host_ip],
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
        host_ip = "1.2.3.4"
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping", "-c1", host_ip],
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
        host_ip = "1ce:c01d:bee2:15:a5:900d:a5:11fe"
        self.assertTrue(vm_scenario._ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping6", "-c1", host_ip],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    def get_scenario(self):

        server = mock.Mock(
            networks={"foo_net": "foo_data"},
            addresses={"foo_net": [{"addr": "foo_addr"}]},
            tenant_id="foo_tenant"
        )
        scenario = utils.VMScenario(context={})

        scenario._netwrap = mock.Mock()
        scenario._boot_server = mock.Mock(return_value=server)
        scenario._delete_server = mock.Mock()
        scenario._associate_floating_ip = mock.Mock()
        scenario._wait_for_ping = mock.Mock()

        return scenario, server

    @mock.patch(VMTASKS_UTILS + ".network_wrapper")
    def test__get_netwrap(self, mock_wrap):
        scenario = utils.VMScenario(context={})
        scenario.clients = "clients"
        mock_wrap.wrap.return_value = "wrap"

        ret = scenario._get_netwrap()

        self.assertEqual("wrap", ret)

        mock_wrap.wrap.assert_called_once_with("clients")

    def test__boot_server_with_fip_missed_networks(self):
        scenario, server = self.get_scenario()

        server.networks = {}

        self.assertRaises(RuntimeError,
                          scenario._boot_server_with_fip,
                          "foo_image", "foo_flavor",
                          foo_arg="foo_value")

        scenario._boot_server.assert_called_once_with(
              "foo_image", "foo_flavor",
              foo_arg="foo_value", auto_assign_nic=True)

    def test__boot_server_with_fip(self):
        scenario, server = self.get_scenario()

        scenario._attach_floating_ip = mock.Mock(
            return_value={"id": "foo_id", "ip": "foo_ip"})

        scenario._boot_server_with_fip(
            "foo_image", "foo_flavor",
            wait_for_ping=True, foo_arg="foo_value",
            floating_network="floating_network")

        scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            foo_arg="foo_value", auto_assign_nic=True)

        scenario._attach_floating_ip.assert_called_once_with(
            server, "floating_network")

        scenario._wait_for_ping.assert_called_once_with(
            "foo_ip")

    def test__attach_floating_ip(self):
        scenario, server = self.get_scenario()

        scenario._netwrap.create_floating_ip.return_value = {
            "id": "foo_id", "ip": "foo_ip"}

        scenario._attach_floating_ip(
            server, floating_network="bar_network")

        scenario._netwrap.create_floating_ip.assert_called_once_with(
            ext_network="bar_network", int_network="foo_net",
            tenant_id="foo_tenant", fixed_ip="foo_addr")

        scenario._associate_floating_ip.assert_called_once_with(
            server, "foo_ip", fixed_address="foo_addr")

    def test__delete_floating_ip(self):
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
        scenario._netwrap.delete_floating_ip.assert_called_once_with(
            "foo_id", wait=True)

    def test__delete_server_with_fip(self):
        scenario, server = self.get_scenario()
        scenario._delete_floating_ip = mock.Mock()

        scenario._delete_server_with_fip(
            server, "foo_fip", force_delete=True)

        scenario._delete_floating_ip.assert_called_once_with(
            server, "foo_fip")

        scenario._delete_server.assert_called_once_with(
            server, force=True)
