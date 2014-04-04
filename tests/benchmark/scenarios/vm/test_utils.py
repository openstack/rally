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

import mock

from rally.benchmark.scenarios.vm import utils
from tests import fakes
from tests import test


VMTASKS_UTILS = "rally.benchmark.scenarios.vm.utils"


class VMScenarioTestCase(test.TestCase):

    @mock.patch('__builtin__.open')
    def test_run_action(self, mock_open):
        mock_ssh = mock.MagicMock()
        mock_file_handle = mock.MagicMock()
        mock_open.return_value = mock_file_handle
        vm_scenario = utils.VMScenario()
        vm_scenario.run_action(mock_ssh, 'interpreter', 'script')
        mock_ssh.execute.assert_called_once_with('interpreter',
                                                 stdin=mock_file_handle)

    def test_wait_for_network(self):
        ssh = mock.MagicMock()
        vm_scenario = utils.VMScenario()
        vm_scenario.wait_for_network(ssh)
        ssh.wait.assert_called_once_with()

    @mock.patch(VMTASKS_UTILS + ".VMScenario.run_action")
    @mock.patch("rally.sshutils.SSH")
    def test_run_command(self, mock_ssh_class,
                         mock_run_action):
        mock_ssh_instance = mock.MagicMock()
        mock_ssh_class.return_value = mock_ssh_instance
        fake_server = fakes.FakeServer()
        fake_server.addresses = dict(
            private=[dict(
                version=4,
                addr="1.2.3.4"
            )]
        )
        vm_scenario = utils.VMScenario()
        vm_scenario._context = {"user": {"keypair": {"private": "ssh"}}}
        vm_scenario.run_command(fake_server, "username", "private", 22, 4,
                                "int", "script")

        mock_ssh_class.assert_called_once_with("username", "1.2.3.4",
                                               port=22, pkey="ssh")
        mock_ssh_instance.wait.assert_called_once_with()
        mock_run_action.assert_called_once_with(mock_ssh_instance,
                                                "int", "script")
