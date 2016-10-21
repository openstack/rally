# Copyright 2016 IBM Corp.
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

from rally.plugins.openstack.scenarios.nova import hosts
from tests.unit import test


class NovaHostsTestCase(test.TestCase):

    def test_list_hosts(self):
        scenario = hosts.ListHosts()
        scenario._list_hosts = mock.Mock()
        scenario.run(zone=None)
        scenario._list_hosts.assert_called_once_with(None)

    def test_list_and_get_hosts(self):
        fake_hosts = [mock.Mock(host_name="fake_hostname")]
        scenario = hosts.ListAndGetHosts()
        scenario._list_hosts = mock.MagicMock(
            return_value=fake_hosts)
        scenario._get_host = mock.MagicMock()
        scenario.run(zone="nova")

        scenario._list_hosts.assert_called_once_with("nova")
        scenario._get_host.assert_called_once_with(
            "fake_hostname", atomic_action=False)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "nova.get_1_hosts")
