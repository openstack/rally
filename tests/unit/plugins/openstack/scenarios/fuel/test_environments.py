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

from rally.plugins.openstack.scenarios.fuel import environments
from tests.unit import test


class FuelEnvironmentsTestCase(test.ScenarioTestCase):

    def test_create_and_list_environments(self):
        scenario = environments.CreateAndListEnvironments(self.context)

        scenario._create_environment = mock.Mock()
        scenario._list_environments = mock.Mock()

        scenario.run(
            release_id=2, network_provider="test_neutron",
            deployment_mode="test_mode", net_segment_type="test_type")
        scenario._create_environment.assert_called_once_with(
            release_id=2, network_provider="test_neutron",
            deployment_mode="test_mode", net_segment_type="test_type")
        scenario._list_environments.assert_called_once_with()

    def test_create_and_delete_environments(self):
        scenario = environments.CreateAndDeleteEnvironment(self.context)

        scenario._create_environment = mock.Mock(return_value=42)
        scenario._delete_environment = mock.Mock()

        scenario.run(
            release_id=2, network_provider="test_neutron",
            deployment_mode="test_mode", net_segment_type="test_type")

        scenario._create_environment.assert_called_once_with(
            release_id=2, network_provider="test_neutron",
            deployment_mode="test_mode", net_segment_type="test_type")
        scenario._delete_environment.assert_called_once_with(42, 5)
