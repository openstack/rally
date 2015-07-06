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
from oslotest import mockpatch

from rally.plugins.openstack.scenarios.ec2 import utils
from tests.unit import test

EC2_UTILS = "rally.plugins.openstack.scenarios.ec2.utils"
CONF = cfg.CONF


class EC2UtilsTestCase(test.TestCase):

    def test_ec2_resource_is(self):
        resource = mock.MagicMock(state="RUNNING")
        resource_is = utils.ec2_resource_is("RUNNING")
        self.assertTrue(resource_is(resource))
        resource.state = "PENDING"
        self.assertFalse(resource_is(resource))

    def test__update_resource(self):
        resource = mock.MagicMock()
        utils.EC2Scenario()._update_resource(resource)
        resource.update.assert_called_once_with()


class EC2ScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(EC2ScenarioTestCase, self).setUp()
        self.server = mock.MagicMock()
        self.reservation = mock.MagicMock(instances=[self.server])
        self.mock_resource_is = mockpatch.Patch(EC2_UTILS + ".ec2_resource_is")
        self.mock_update_resource = mockpatch.Patch(
            EC2_UTILS + ".EC2Scenario._update_resource")
        self.useFixture(self.mock_resource_is)
        self.useFixture(self.mock_update_resource)

    def test__boot_server(self):
        self.clients("ec2").run_instances.return_value = self.reservation
        ec2_scenario = utils.EC2Scenario(context={})
        return_server = ec2_scenario._boot_server("image", "flavor")
        self.mock_wait_for.mock.assert_called_once_with(
            self.server,
            is_ready=self.mock_resource_is.mock.return_value,
            update_resource=self.mock_update_resource.mock,
            check_interval=CONF.benchmark.ec2_server_boot_poll_interval,
            timeout=CONF.benchmark.ec2_server_boot_timeout)
        self.mock_resource_is.mock.assert_called_once_with("RUNNING")
        self.assertEqual(self.mock_wait_for.mock.return_value, return_server)
        self._test_atomic_action_timer(ec2_scenario.atomic_actions(),
                                       "ec2.boot_server")
