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

from rally.plugins.openstack.scenarios.neutron import bgpvpn
from tests.unit import test


@ddt.ddt
class NeutronBgpvpnTestCase(test.TestCase):

    def _get_context(self):
        context = test.get_test_context()
        return context

    @ddt.data(
        {},
        {"bgpvpn_create_args": None},
        {"bgpvpn_create_args": {}},
        {"bgpvpn_create_args": {"name": "given-name"}},
    )
    @ddt.unpack
    def test_create_and_delete_bgpvpns(self, bgpvpn_create_args=None):
        scenario = bgpvpn.CreateAndDeleteBgpvpns(self._get_context())
        bgpvpn_create_data = bgpvpn_create_args or {}
        scenario._create_bgpvpn = mock.Mock()
        scenario._delete_bgpvpn = mock.Mock()
        scenario.run(bgpvpn_create_args=bgpvpn_create_data)
        scenario._create_bgpvpn.assert_called_once_with(bgpvpn_create_data)
        scenario._delete_bgpvpn.assert_called_once_with(
            scenario._create_bgpvpn.return_value)
