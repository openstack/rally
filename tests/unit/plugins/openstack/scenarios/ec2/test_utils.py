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
from oslo_config import cfg

from rally.plugins.openstack.scenarios.ec2 import utils
from tests.unit import test

CONF = cfg.CONF


class EC2ScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(EC2ScenarioTestCase, self).setUp()
        self.server1 = mock.MagicMock()
        self.server2 = mock.MagicMock()
        self.reservations = mock.MagicMock(instances=[self.server1,
                                                      self.server2])

    def test__list_servers(self):
        servers_list = []
        self.clients("ec2").get_only_instances.return_value = servers_list
        ec2_scenario = utils.EC2Scenario()
        return_servers_list = ec2_scenario._list_servers()
        self.assertEqual(servers_list, return_servers_list)
        self._test_atomic_action_timer(ec2_scenario.atomic_actions(),
                                       "ec2.list_servers")

    def test__update_resource(self):
        resource = mock.MagicMock()
        scenario = utils.EC2Scenario(self.context)
        self.assertEqual(scenario._update_resource(resource), resource)
        resource.update.assert_called_once_with()

    def test__boot_servers(self):
        self.clients("ec2").run_instances.return_value = self.reservations
        ec2_scenario = utils.EC2Scenario(context={})
        ec2_scenario._update_resource = mock.Mock()
        ec2_scenario._boot_servers("image", "flavor", 2)
        expected = [
            mock.call(
                self.server1,
                ready_statuses=["RUNNING"],
                update_resource=ec2_scenario._update_resource,
                check_interval=CONF.benchmark.ec2_server_boot_poll_interval,
                timeout=CONF.benchmark.ec2_server_boot_timeout
            ),
            mock.call(
                self.server2,
                ready_statuses=["RUNNING"],
                update_resource=ec2_scenario._update_resource,
                check_interval=CONF.benchmark.ec2_server_boot_poll_interval,
                timeout=CONF.benchmark.ec2_server_boot_timeout
            )
        ]
        self.mock_wait_for.mock.assert_has_calls(expected)
        self._test_atomic_action_timer(ec2_scenario.atomic_actions(),
                                       "ec2.boot_servers")
