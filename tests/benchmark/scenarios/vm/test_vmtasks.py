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
from tests import test


class VMTasksTestCase(test.TestCase):

    @mock.patch("json.loads")
    def test_boot_runcommand_delete(self, mock_json_loads):
        # Setup mocks
        scenario = vmtasks.VMTasks()
        scenario._boot_server = mock.MagicMock(return_value="fake_server")
        scenario._generate_random_name = mock.MagicMock(return_value="name")
        scenario.run_command = mock.MagicMock()
        scenario.run_command.return_value = ('code', 'stdout', 'stderr')
        scenario._delete_server = mock.MagicMock()

        # Run scenario
        scenario.boot_runcommand_delete(
            "image_id", "flavour_id", "script_path", "interpreter",
            network="network", username="username", ip_version="ip_version",
            port="port", fakearg="f")

        # Assertions
        scenario._boot_server.assert_called_once_with(
                'name', 'image_id', "flavour_id", key_name="rally_ssh_key",
                fakearg="f")

        scenario.run_command.assert_called_once_with(
            "fake_server", 'username', "network", "port", "ip_version",
            "interpreter", "script_path")

        mock_json_loads.assert_called_once_with('stdout')

        scenario._delete_server.assert_called_once_with("fake_server")
