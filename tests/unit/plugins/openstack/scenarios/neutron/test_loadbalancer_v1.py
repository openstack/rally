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

from rally.plugins.openstack.scenarios.neutron import loadbalancer_v1
from tests.unit import test


class NeutronLoadbalancerv1TestCase(test.TestCase):

    def _get_context(self):
        return {
            "user": {"id": "fake_user", "tenant_id": "fake_tenant"},
            "tenant": {"id": "fake_tenant",
                       "networks": [{"id": "fake_net",
                                     "subnets": ["fake_subnet"]}]}}

    def _validate_create_and_list_pools_scenario(self, pool_create_args=None):
        neutron_scenario = loadbalancer_v1.NeutronLoadbalancerV1(
            self._get_context())
        pool_data = pool_create_args or {}
        neutron_scenario._create_v1_pool = mock.Mock()
        neutron_scenario._list_v1_pools = mock.Mock()
        neutron_scenario.create_and_list_pools(
            pool_create_args=pool_create_args)
        for net in self._get_context()["tenant"]["networks"]:
            for subnet_id in net["subnets"]:
                neutron_scenario._create_v1_pool.assert_called_once_with(
                    subnet_id, **pool_data)
        neutron_scenario._list_v1_pools.assert_called_once_with()

    def _validate_create_and_delete_pools_scenario(self,
                                                   pool_create_args=None):
        neutron_scenario = loadbalancer_v1.NeutronLoadbalancerV1(
            self._get_context())
        pool = {
            "pool": {
                "id": "pool-id"
            }
        }
        pool_data = pool_create_args or {}
        neutron_scenario._create_v1_pool = mock.Mock(return_value=pool)
        neutron_scenario._delete_v1_pool = mock.Mock()
        neutron_scenario.create_and_delete_pools(
            pool_create_args=pool_create_args)
        pools = []
        for net in self._get_context()["tenant"]["networks"]:
            for subnet_id in net["subnets"]:
                self.assertEqual([mock.call(subnet_id=subnet_id,
                                  **pool_data)],
                                 neutron_scenario._create_v1_pool.mock_calls)
        for pool in pools:
            self.assertEqual(1, neutron_scenario._delete_v1_pool.call_count)

    def _validate_create_and_update_pools_scenario(self,
                                                   pool_create_args=None):
        neutron_scenario = loadbalancer_v1.NeutronLoadbalancerV1(
            self._get_context())
        pool = {
            "pool": {
                "id": "pool-id"
            }
        }
        updated_pool = {
            "pool": {
                "id": "pool-id",
                "name": "updated-pool",
                "admin_state_up": True
            }
        }
        pool_data = pool_create_args or {}
        pool_update_args = {"name": "_updated", "admin_state_up": True}
        neutron_scenario._create_v1_pool = mock.Mock(return_value=pool)
        neutron_scenario._update_v1_pool = mock.Mock(
            return_value=updated_pool)
        neutron_scenario.create_and_update_pools(
            pool_create_args=pool_data,
            pool_update_args=pool_update_args)
        pools = []
        for net in self._get_context()["tenant"]["networks"]:
            for subnet_id in net["subnets"]:
                pools.append(
                    neutron_scenario._create_v1_pool.assert_called_once_with(
                        subnet_id, **pool_data))
        for pool in pools:
            neutron_scenario._update_v1_pool.assert_called_once_with(
                neutron_scenario._create_v1_pool.return_value,
                **pool_update_args)

    def test_create_and_list_pools_default(self):
        self._validate_create_and_list_pools_scenario(pool_create_args={})

    def test_create_and_list_pools_None(self):
        self._validate_create_and_list_pools_scenario()

    def test_create_and_list_pools_explicit(self):
        self._validate_create_and_list_pools_scenario(
            pool_create_args={"name": "given-name"})

    def test_create_and_delete_pools_default(self):
        self._validate_create_and_delete_pools_scenario(pool_create_args={})

    def test_create_and_delete_pools_None(self):
        self._validate_create_and_delete_pools_scenario()

    def test_create_and_delete_pools_explicit(self):
        self._validate_create_and_delete_pools_scenario(
            pool_create_args={"name": "given-name"})

    def test_create_and_update_pools_default(self):
        self._validate_create_and_update_pools_scenario(pool_create_args={})

    def test_create_and_update_pools_None(self):
        self._validate_create_and_update_pools_scenario()

    def test_create_and_update_pools_explicit(self):
        self._validate_create_and_update_pools_scenario(
            pool_create_args={"name": "given-name"})
