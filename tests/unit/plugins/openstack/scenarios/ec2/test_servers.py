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


class EC2ServersTestCase(test.ScenarioTestCase):

    def test_list_servers(self):
        scenario = servers.EC2Servers()
        scenario._list_servers = mock.MagicMock()
        scenario.list_servers()
        scenario._list_servers.assert_called_once_with()

    def test_boot_server(self):
        scenario = servers.EC2Servers(self.context)
        scenario._boot_servers = mock.Mock()
        scenario.boot_server("foo_image", "foo_flavor", foo="bar")
        scenario._boot_servers.assert_called_once_with(
            "foo_image", "foo_flavor", foo="bar")
