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

import ddt
import mock

from rally.plugins.openstack.scenarios.neutron import loadbalancer_v1
from tests.unit import test


@ddt.ddt
class NeutronLoadbalancerv1TestCase(test.TestCase):

    def _get_context(self):
        context = test.get_test_context()
        context.update({
            "user": {
                "id": "fake_user",
                "tenant_id": "fake_tenant",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake_tenant",
                       "networks": [{"id": "fake_net",
                                     "subnets": ["fake_subnet"]}]}})
        return context

    @ddt.data(
        {},
        {"pool_create_args": None},
        {"pool_create_args": {}},
        {"pool_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_list_pools(self, pool_create_args=None):
        scenario = loadbalancer_v1.CreateAndListPools(self._get_context())
        pool_data = pool_create_args or {}
        networks = self._get_context()["tenant"]["networks"]
        scenario._create_v1_pools = mock.Mock()
        scenario._list_v1_pools = mock.Mock()
        scenario.run(pool_create_args=pool_create_args)
        scenario._create_v1_pools.assert_called_once_with(networks,
                                                          **pool_data)
        scenario._list_v1_pools.assert_called_once_with()

    @ddt.data(
        {},
        {"pool_create_args": None},
        {"pool_create_args": {}},
        {"pool_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_delete_pools(self, pool_create_args=None):
        scenario = loadbalancer_v1.CreateAndDeletePools(self._get_context())
        pools = [{
            "pool": {
                "id": "pool-id"
            }
        }]
        pool_data = pool_create_args or {}
        networks = self._get_context()["tenant"]["networks"]
        scenario._create_v1_pools = mock.Mock(return_value=pools)
        scenario._delete_v1_pool = mock.Mock()
        scenario.run(pool_create_args=pool_create_args)
        self.assertEqual([mock.call(networks, **pool_data)],
                         scenario._create_v1_pools.mock_calls)
        for _ in pools:
            self.assertEqual(1, scenario._delete_v1_pool.call_count)

    @ddt.data(
        {},
        {"pool_create_args": None},
        {"pool_create_args": {}},
        {"pool_create_args": {"name": "given-name"}},
        {"pool_update_args": None},
        {"pool_update_args": {}},
        {"pool_update_args": {"name": "updated-name"}},
        {"pool_create_args": None, "pool_update_args": None},
        {"pool_create_args": {"name": "given-name"},
         "pool_update_args": {"name": "updated-name"}},
        {"pool_create_args": None,
         "pool_update_args": {"name": "updated-name"}},
        {"pool_create_args": None, "pool_update_args": {}},
        {"pool_create_args": {}, "pool_update_args": None},
    )
    @ddt.unpack
    def test_create_and_update_pools(self, pool_create_args=None,
                                     pool_update_args=None):
        scenario = loadbalancer_v1.CreateAndUpdatePools(self._get_context())
        pools = [{
            "pool": {
                "id": "pool-id"
            }
        }]
        updated_pool = {
            "pool": {
                "id": "pool-id",
                "name": "updated-pool",
                "admin_state_up": True
            }
        }
        pool_data = pool_create_args or {}
        pool_update_args = pool_update_args or {}
        pool_update_args.update({"name": "_updated", "admin_state_up": True})
        scenario._create_v1_pools = mock.Mock(return_value=pools)
        scenario._update_v1_pool = mock.Mock(return_value=updated_pool)
        networks = self._get_context()["tenant"]["networks"]
        scenario.run(pool_create_args=pool_data,
                     pool_update_args=pool_update_args)
        self.assertEqual([mock.call(networks, **pool_data)],
                         scenario._create_v1_pools.mock_calls)
        for pool in pools:
            scenario._update_v1_pool.assert_called_once_with(
                pool, **pool_update_args)

    @ddt.data(
        {},
        {"vip_create_args": None},
        {"vip_create_args": {}},
        {"vip_create_args": {"name": "given-vip-name"}},
        {"pool_create_args": None},
        {"pool_create_args": {}},
        {"pool_create_args": {"name": "given-pool-name"}},
    )
    @ddt.unpack
    def test_create_and_list_vips(self, pool_create_args=None,
                                  vip_create_args=None):
        scenario = loadbalancer_v1.CreateAndListVips(self._get_context())
        pools = [{
            "pool": {
                "id": "pool-id"
            }
        }]
        vip_data = vip_create_args or {}
        pool_data = pool_create_args or {}
        networks = self._get_context()["tenant"]["networks"]
        scenario._create_v1_pools = mock.Mock(return_value=pools)
        scenario._create_v1_vip = mock.Mock()
        scenario._list_v1_vips = mock.Mock()
        scenario.run(pool_create_args=pool_create_args,
                     vip_create_args=vip_create_args)
        scenario._create_v1_pools.assert_called_once_with(networks,
                                                          **pool_data)
        scenario._create_v1_vip.assert_has_calls(
            [mock.call(pool, **vip_data) for pool in pools])
        scenario._list_v1_vips.assert_called_once_with()

    @ddt.data(
        {},
        {"vip_create_args": None},
        {"vip_create_args": {}},
        {"vip_create_args": {"name": "given-name"}},
        {"pool_create_args": None},
        {"pool_create_args": {}},
        {"pool_create_args": {"name": "given-pool-name"}},
    )
    @ddt.unpack
    def test_create_and_delete_vips(self, pool_create_args=None,
                                    vip_create_args=None):
        scenario = loadbalancer_v1.CreateAndDeleteVips(self._get_context())
        pools = [{
            "pool": {
                "id": "pool-id"
            }
        }]
        vip = {
            "vip": {
                "id": "vip-id"
            }
        }
        vip_data = vip_create_args or {}
        pool_data = pool_create_args or {}
        networks = self._get_context()["tenant"]["networks"]
        scenario._create_v1_pools = mock.Mock(return_value=pools)
        scenario._create_v1_vip = mock.Mock(return_value=vip)
        scenario._delete_v1_vip = mock.Mock()
        scenario.run(pool_create_args=pool_create_args,
                     vip_create_args=vip_create_args)
        scenario._create_v1_pools.assert_called_once_with(networks,
                                                          **pool_data)
        scenario._create_v1_vip.assert_has_calls(
            [mock.call(pool, **vip_data) for pool in pools])
        scenario._delete_v1_vip.assert_has_calls([mock.call(vip["vip"])])

    @ddt.data(
        {},
        {"vip_create_args": None},
        {"vip_create_args": {}},
        {"vip_create_args": {"name": "given-vip-name"}},
        {"pool_create_args": None},
        {"pool_create_args": {}},
        {"pool_create_args": {"name": "given-pool-name"}},
    )
    @ddt.unpack
    def test_create_and_update_vips(self, pool_create_args=None,
                                    vip_create_args=None,
                                    vip_update_args=None):
        scenario = loadbalancer_v1.CreateAndUpdateVips(self._get_context())
        pools = [{
            "pool": {
                "id": "pool-id",
            }
        }]
        expected_vip = {
            "vip": {
                "id": "vip-id",
                "name": "vip-name"
            }
        }
        updated_vip = {
            "vip": {
                "id": "vip-id",
                "name": "updated-vip-name"
            }
        }
        vips = [expected_vip]
        vip_data = vip_create_args or {}
        vip_update_data = vip_update_args or {}
        pool_data = pool_create_args or {}
        networks = self._get_context()["tenant"]["networks"]
        scenario._create_v1_pools = mock.Mock(return_value=pools)
        scenario._create_v1_vip = mock.Mock(return_value=expected_vip)
        scenario._update_v1_vip = mock.Mock(return_value=updated_vip)
        scenario.run(pool_create_args=pool_create_args,
                     vip_create_args=vip_create_args,
                     vip_update_args=vip_update_args)
        scenario._create_v1_pools.assert_called_once_with(networks,
                                                          **pool_data)
        scenario._create_v1_vip.assert_has_calls(
            [mock.call(pool, **vip_data) for pool in pools])
        scenario._update_v1_vip.assert_has_calls(
            [mock.call(vip, **vip_update_data) for vip in vips])

    @ddt.data(
        {},
        {"healthmonitor_create_args": None},
        {"healthmonitor_create_args": {}},
        {"healthmonitor_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_list_healthmonitors(self,
                                            healthmonitor_create_args=None):
        scenario = loadbalancer_v1.CreateAndListHealthmonitors(
            self._get_context())
        hm_data = healthmonitor_create_args or {}
        scenario._create_v1_healthmonitor = mock.Mock()
        scenario._list_v1_healthmonitors = mock.Mock()
        scenario.run(healthmonitor_create_args=healthmonitor_create_args)
        scenario._create_v1_healthmonitor.assert_called_once_with(**hm_data)
        scenario._list_v1_healthmonitors.assert_called_once_with()

    @ddt.data(
        {},
        {"healthmonitor_create_args": None},
        {"healthmonitor_create_args": {}},
        {"healthmonitor_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_delete_healthmonitors(self,
                                              healthmonitor_create_args=None):
        scenario = loadbalancer_v1.CreateAndDeleteHealthmonitors(
            self._get_context())
        hm = {"health_monitor": {"id": "hm-id"}}
        hm_data = healthmonitor_create_args or {}
        scenario._create_v1_healthmonitor = mock.Mock(return_value=hm)
        scenario._delete_v1_healthmonitor = mock.Mock()
        scenario.run(healthmonitor_create_args=healthmonitor_create_args)
        scenario._create_v1_healthmonitor.assert_called_once_with(**hm_data)
        scenario._delete_v1_healthmonitor.assert_called_once_with(
            scenario._create_v1_healthmonitor.return_value["health_monitor"])

    @ddt.data(
        {},
        {"healthmonitor_create_args": None},
        {"healthmonitor_create_args": {}},
        {"healthmonitor_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_update_healthmonitors(self,
                                              healthmonitor_create_args=None,
                                              healthmonitor_update_args=None):
        scenario = loadbalancer_v1.CreateAndUpdateHealthmonitors(
            self._get_context())
        mock_random = loadbalancer_v1.random = mock.Mock()
        hm = {"healthmonitor": {"id": "hm-id"}}
        hm_data = healthmonitor_create_args or {}
        hm_update_data = healthmonitor_update_args or {
            "max_retries": mock_random.choice.return_value}
        scenario._create_v1_healthmonitor = mock.Mock(return_value=hm)
        scenario._update_v1_healthmonitor = mock.Mock()
        scenario.run(healthmonitor_create_args=healthmonitor_create_args,
                     healthmonitor_update_args=healthmonitor_update_args)
        scenario._create_v1_healthmonitor.assert_called_once_with(**hm_data)
        scenario._update_v1_healthmonitor.assert_called_once_with(
            scenario._create_v1_healthmonitor.return_value, **hm_update_data)
