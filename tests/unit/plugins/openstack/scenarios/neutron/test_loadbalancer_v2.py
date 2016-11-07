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

from rally.plugins.openstack.scenarios.neutron import loadbalancer_v2
from tests.unit import test


@ddt.ddt
class NeutronLoadbalancerv2TestCase(test.TestCase):

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
        {"lb_create_args": None},
        {"lb_create_args": {}},
        {"lb_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_list_load_balancers(self, lb_create_args=None):
        context = self._get_context()
        scenario = loadbalancer_v2.CreateAndListLoadbalancers(context)
        lb_create_args = lb_create_args or {}
        networks = context["tenant"]["networks"]
        scenario._create_lbaasv2_loadbalancer = mock.Mock()
        scenario._list_lbaasv2_loadbalancers = mock.Mock()
        scenario.run(lb_create_args=lb_create_args)

        subnets = []
        mock_has_calls = []
        for network in networks:
            subnets.extend(network.get("subnets", []))
        for subnet in subnets:
            mock_has_calls.append(mock.call(subnet, **lb_create_args))
        scenario._create_lbaasv2_loadbalancer.assert_has_calls(mock_has_calls)
        scenario._list_lbaasv2_loadbalancers.assert_called_once_with()
