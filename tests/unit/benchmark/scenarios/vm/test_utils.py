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

from rally.benchmark.scenarios.vm import utils
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
    def test_run_action(self, mock_open):
        mock_ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario()
        vm_scenario.run_action(mock_ssh, "interpreter", "script")
        mock_ssh.execute.assert_called_once_with("interpreter",
                                                 stdin=mock_open.side_effect())

    def test_wait_for_ssh(self):
        ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario()
        vm_scenario.wait_for_ssh(ssh)
        ssh.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".VMScenario.ping_ip_address",
                return_value=True)
    def test_wait_for_ping(self, mock_ping):
        vm_scenario = utils.VMScenario()
        vm_scenario.wait_for_ping("1.2.3.4")
        self.wait_for.mock.assert_called_once_with("1.2.3.4",
                                                   is_ready=mock_ping,
                                                   timeout=120)

    @mock.patch(VMTASKS_UTILS + ".VMScenario.run_action")
    @mock.patch(VMTASKS_UTILS + ".VMScenario.wait_for_ping")
    @mock.patch("rally.common.sshutils.SSH")
    def test_run_command(self, mock_ssh_class, mock_wait_ping,
                         mock_run_action):
        mock_ssh_instance = mock.MagicMock()
        mock_ssh_class.return_value = mock_ssh_instance

        vm_scenario = utils.VMScenario()
        vm_scenario.context = {"user": {"keypair": {"private": "ssh"}}}
        vm_scenario.run_command("1.2.3.4", 22, "username",
                                "password", "int", "script")

        mock_wait_ping.assert_called_once_with("1.2.3.4")
        mock_ssh_class.assert_called_once_with("username", "1.2.3.4", port=22,
                                               pkey="ssh",
                                               password="password")
        mock_ssh_instance.wait.assert_called_once_with()
        mock_run_action.assert_called_once_with(mock_ssh_instance,
                                                "int", "script")

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test_ping_ip_address_linux(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "linux2"

        vm_scenario = utils.VMScenario()
        host_ip = "1.2.3.4"
        self.assertTrue(vm_scenario.ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping", "-c1", "-w1", host_ip],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test_ping_ip_address_linux_ipv6(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "linux2"

        vm_scenario = utils.VMScenario()
        host_ip = "1ce:c01d:bee2:15:a5:900d:a5:11fe"
        self.assertTrue(vm_scenario.ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping6", "-c1", "-w1", host_ip],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test_ping_ip_address_other_os(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "freebsd10"

        vm_scenario = utils.VMScenario()
        host_ip = "1.2.3.4"
        self.assertTrue(vm_scenario.ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping", "-c1", host_ip],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".sys")
    @mock.patch("subprocess.Popen")
    def test_ping_ip_address_other_os_ipv6(self, mock_subprocess, mock_sys):
        ping_process = mock.MagicMock()
        ping_process.returncode = 0
        mock_subprocess.return_value = ping_process
        mock_sys.platform = "freebsd10"

        vm_scenario = utils.VMScenario()
        host_ip = "1ce:c01d:bee2:15:a5:900d:a5:11fe"
        self.assertTrue(vm_scenario.ping_ip_address(host_ip))

        mock_subprocess.assert_called_once_with(
                ["ping6", "-c1", host_ip],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        ping_process.wait.assert_called_once_with()
