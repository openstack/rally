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

from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.fuel import utils
from rally.task import validation


"""Scenarios for Fuel environments."""


@validation.required_clients("fuel", admin=True)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["fuel"]},
                    name="FuelEnvironments.create_and_delete_environment")
class CreateAndDeleteEnvironment(utils.FuelScenario):

    def run(self, release_id=1, network_provider="neutron",
            deployment_mode="ha_compact", net_segment_type="vlan",
            delete_retries=5):
        """Create and delete Fuel environments.

        :param release_id: release id (default 1)
        :param network_provider: network provider (default 'neutron')
        :param deployment_mode: deployment mode (default 'ha_compact')
        :param net_segment_type: net segment type (default 'vlan')
        :param delete_retries: retries count on delete operations (default 5)
        """

        env_id = self._create_environment(release_id=release_id,
                                          network_provider=network_provider,
                                          deployment_mode=deployment_mode,
                                          net_segment_type=net_segment_type)
        self._delete_environment(env_id, delete_retries)


@validation.required_clients("fuel", admin=True)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["fuel"]},
                    name="FuelEnvironments.create_and_list_environments")
class CreateAndListEnvironments(utils.FuelScenario):

    def run(self, release_id=1, network_provider="neutron",
            deployment_mode="ha_compact", net_segment_type="vlan"):
        """Create and list Fuel environments.

        :param release_id: release id (default 1)
        :param network_provider: network provider (default 'neutron')
        :param deployment_mode: deployment mode (default 'ha_compact')
        :param net_segment_type: net segment type (default 'vlan')
        """

        self._create_environment(release_id=release_id,
                                 network_provider=network_provider,
                                 deployment_mode=deployment_mode,
                                 net_segment_type=net_segment_type)
        self._list_environments()