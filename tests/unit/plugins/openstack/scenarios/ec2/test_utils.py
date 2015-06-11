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


class EC2ScenarioTestCase(test.ClientsTestCase):

    def setUp(self):
        super(EC2ScenarioTestCase, self).setUp()
        self.server = mock.MagicMock()
        self.reservation = mock.MagicMock(instances=[self.server])
        self.res_is = mockpatch.Patch(EC2_UTILS + ".ec2_resource_is")
        self.update_res = mockpatch.Patch(
            EC2_UTILS + ".EC2Scenario._update_resource")
        self.wait_for = mockpatch.Patch(EC2_UTILS + ".bench_utils.wait_for")
        self.useFixture(self.wait_for)
        self.useFixture(self.res_is)
        self.useFixture(self.update_res)
        self.useFixture(mockpatch.Patch("time.sleep"))

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = atomic_actions.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    def test__boot_server(self):
        self.clients("ec2").run_instances.return_value = self.reservation
        ec2_scenario = utils.EC2Scenario(context={})
        return_server = ec2_scenario._boot_server("image", "flavor")
        expected = mock.call(
            self.server, is_ready=self.res_is.mock(),
            update_resource=self.update_res.mock,
            check_interval=CONF.benchmark.ec2_server_boot_poll_interval,
            timeout=CONF.benchmark.ec2_server_boot_timeout)
        self.assertEqual([expected], self.wait_for.mock.mock_calls)
        self.res_is.mock.assert_has_calls([mock.call("RUNNING")])
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(ec2_scenario.atomic_actions(),
                                       "ec2.boot_server")
