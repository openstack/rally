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
from oslo_config import cfg

from rally.plugins.openstack.scenarios.vm import utils
from tests.unit import test

VMTASKS_UTILS = "rally.plugins.openstack.scenarios.vm.utils"
CONF = cfg.CONF


class VMScenarioTestCase(test.ScenarioTestCase):

    @mock.patch("%s.open" % VMTASKS_UTILS,
                side_effect=mock.mock_open(), create=True)
    def test__run_command_over_ssh_script_file(self, mock_open):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario._run_command_over_ssh(
            mock_ssh,
            {
                "script_file": "foobar",
                "interpreter": ["interpreter", "interpreter_arg"],
                "command_args": ["arg1", "arg2"]
            }
        )
        mock_ssh.execute.assert_called_once_with(
            ["interpreter", "interpreter_arg", "arg1", "arg2"],
            stdin=mock_open.side_effect())
        mock_open.assert_called_once_with("foobar", "rb")

    @mock.patch("%s.six.moves.StringIO" % VMTASKS_UTILS)
    def test__run_command_over_ssh_script_inline(self, mock_string_io):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario._run_command_over_ssh(
            mock_ssh,
            {
                "script_inline": "foobar",
                "interpreter": ["interpreter", "interpreter_arg"],
                "command_args": ["arg1", "arg2"]
            }
        )
        mock_ssh.execute.assert_called_once_with(
            ["interpreter", "interpreter_arg", "arg1", "arg2"],
            stdin=mock_string_io.return_value)
        mock_string_io.assert_called_once_with("foobar")

    def test__run_command_over_ssh_remote_path(self):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario._run_command_over_ssh(
            mock_ssh,
            {
                "remote_path": ["foo", "bar"],
                "command_args": ["arg1", "arg2"]
            }
        )
        mock_ssh.execute.assert_called_once_with(
            ["foo", "bar", "arg1", "arg2"],
            stdin=None)

    def test__run_command_over_ssh_remote_path_copy(self):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario._run_command_over_ssh(
            mock_ssh,
            {
                "remote_path": ["foo", "bar"],
                "local_path": "/bin/false",
                "command_args": ["arg1", "arg2"]
            }
        )
        mock_ssh.put_file.assert_called_once_with(
            "/bin/false", "bar", mode=0o755
        )
        mock_ssh.execute.assert_called_once_with(
            ["foo", "bar", "arg1", "arg2"],
            stdin=None)

    def test__wait_for_ssh(self):
        ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario._wait_for_ssh(ssh)
        ssh.wait.assert_called_once_with(120, 1)

    def test__wait_for_ping(self):
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario._ping_ip_address = mock.Mock(return_value=True)
        vm_scenario._wait_for_ping(netaddr.IPAddress("1.2.3.4"))
        self.mock_wait_for_status.mock.assert_called_once_with(
            utils.Host("1.2.3.4"),
            ready_statuses=[utils.Host.ICMP_UP_STATUS],
            update_resource=utils.Host.update_status,
            timeout=CONF.benchmark.vm_ping_timeout,
            check_interval=CONF.benchmark.vm_ping_poll_interval)

    @mock.patch(VMTASKS_UTILS + ".VMScenario._run_command_over_ssh")
    @mock.patch("rally.common.sshutils.SSH")
    def test__run_command(self, mock_sshutils_ssh,
                          mock_vm_scenario__run_command_over_ssh):
        vm_scenario = utils.VMScenario(self.context)
        vm_scenario.context = {"user": {"keypair": {"private": "ssh"}}}
        vm_scenario._run_command("1.2.3.4", 22, "username", "password",
                                 command={"script_file": "foo",
                                          "interpreter": "bar"})

        mock_sshutils_ssh.assert_called_once_with(
            "username", "1.2.3.4", port=22, pkey="ssh", password="password")
        mock_sshutils_ssh.return_value.wait.assert_called_once_with(120, 1)
        mock_vm_scenario__run_command_over_ssh.assert_called_once_with(
            mock_sshutils_ssh.return_value,
            {"script_file": "foo", "interpreter": "bar"})

    def get_scenario(self):
        server = mock.Mock(
            networks={"foo_net": "foo_data"},
            addresses={"foo_net": [{"addr": "foo_ip"}]},
            tenant_id="foo_tenant"
        )
        scenario = utils.VMScenario(self.context)

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
            use_floating_ip=False, foo_arg="foo_value")

        self.assertEqual(ip, {"ip": "foo_ip", "id": None,
                              "is_floating": False})
        scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            auto_assign_nic=True, foo_arg="foo_value")
        self.assertEqual(scenario._attach_floating_ip.mock_calls, [])

    def test__boot_server_with_fip(self):
        scenario, server = self.get_scenario()
        scenario._attach_floating_ip = mock.Mock(
            return_value={"id": "foo_id", "ip": "foo_ip"})
        server, ip = scenario._boot_server_with_fip(
            "foo_image", "foo_flavor", floating_network="ext_network",
            use_floating_ip=True, foo_arg="foo_value")
        self.assertEqual(ip, {"ip": "foo_ip", "id": "foo_id",
                              "is_floating": True})

        scenario._boot_server.assert_called_once_with(
            "foo_image", "foo_flavor",
            auto_assign_nic=True, foo_arg="foo_value")
        scenario._attach_floating_ip.assert_called_once_with(
            server, "ext_network")

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

        mock_wrap.assert_called_once_with(scenario.clients, scenario)
        netwrap.create_floating_ip.assert_called_once_with(
            ext_network="bar_network",
            tenant_id="foo_tenant", fixed_ip="foo_ip")

        scenario._associate_floating_ip.assert_called_once_with(
            server, "foo_ip", fixed_address="foo_ip", atomic_action=False)

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
            server, "foo_ip", atomic_action=False)
        mock_wrap.assert_called_once_with(scenario.clients, scenario)
        mock_wrap.return_value.delete_floating_ip.assert_called_once_with(
            "foo_id", wait=True)


class HostTestCase(test.TestCase):

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_linux(self, mock_popen, mock_sys):
        mock_popen.return_value.returncode = 0
        mock_sys.platform = "linux2"

        host = utils.Host("1.2.3.4")
        self.assertEqual(utils.Host.ICMP_UP_STATUS,
                         utils.Host.update_status(host).status)

        mock_popen.assert_called_once_with(
            ["ping", "-c1", "-w1", str(host.ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        mock_popen.return_value.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_linux_ipv6(self, mock_popen, mock_sys):
        mock_popen.return_value.returncode = 0
        mock_sys.platform = "linux2"

        host = utils.Host("1ce:c01d:bee2:15:a5:900d:a5:11fe")
        self.assertEqual(utils.Host.ICMP_UP_STATUS,
                         utils.Host.update_status(host).status)

        mock_popen.assert_called_once_with(
            ["ping6", "-c1", "-w1", str(host.ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        mock_popen.return_value.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_other_os(self, mock_popen, mock_sys):
        mock_popen.return_value.returncode = 0
        mock_sys.platform = "freebsd10"

        host = utils.Host("1.2.3.4")
        self.assertEqual(utils.Host.ICMP_UP_STATUS,
                         utils.Host.update_status(host).status)

        mock_popen.assert_called_once_with(
            ["ping", "-c1", str(host.ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        mock_popen.return_value.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test__ping_ip_address_other_os_ipv6(self, mock_popen, mock_sys):
        mock_popen.return_value.returncode = 0
        mock_sys.platform = "freebsd10"

        host = utils.Host("1ce:c01d:bee2:15:a5:900d:a5:11fe")
        self.assertEqual(utils.Host.ICMP_UP_STATUS,
                         utils.Host.update_status(host).status)

        mock_popen.assert_called_once_with(
            ["ping6", "-c1", str(host.ip)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        mock_popen.return_value.wait.assert_called_once_with()
