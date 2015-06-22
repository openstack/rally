# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.openstack.scenarios.ec2 import servers
from tests.unit import test


UTILS = "rally.plugins.openstack.scenarios.ec2.utils."


class EC2ServersTestCase(test.ClientsTestCase):

    @mock.patch("rally.benchmark.utils.wait_for",
                return_value="running_server")
    @mock.patch(UTILS + "ec2_resource_is", return_value="foo_state")
    @mock.patch(UTILS + "time")
    @mock.patch(UTILS + "CONF")
    def test_boot_server(self, mock_conf, mock_time, mock_ec2_resource_is,
                         mock_wait_for):
        mock_conf.benchmark.ec2_server_boot_prepoll_delay = "foo_delay"
        mock_conf.benchmark.ec2_server_boot_timeout = "foo_timeout"
        mock_conf.benchmark.ec2_server_boot_poll_interval = "foo_interval"

        scenario = servers.EC2Servers()
        scenario._update_resource = "foo_update"
        mock_instances = mock.Mock(instances=["foo_inst"])
        self.clients("ec2").run_instances.return_value = mock_instances
        server = scenario._boot_server("foo_image", "foo_flavor", foo="bar")

        mock_wait_for.assert_called_once_with("foo_inst", is_ready="foo_state",
                                              update_resource="foo_update",
                                              timeout="foo_timeout",
                                              check_interval="foo_interval")
        mock_time.sleep.assert_called_once_with("foo_delay")
        self.assertEqual(server, "running_server")
