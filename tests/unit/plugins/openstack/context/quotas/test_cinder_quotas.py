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

from rally.plugins.openstack.context.quotas import cinder_quotas
from tests.unit import test


class CinderQuotasTestCase(test.TestCase):

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    def test_update(self, client_mock):
        cinder_quo = cinder_quotas.CinderQuotas(client_mock)
        tenant_id = mock.MagicMock()
        quotas_values = {
            "volumes": 10,
            "snapshots": 50,
            "gigabytes": 1000
        }
        cinder_quo.update(tenant_id, **quotas_values)
        client_mock.cinder().quotas.update.assert_called_once_with(
            tenant_id, **quotas_values)

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    def test_delete(self, client_mock):
        cinder_quo = cinder_quotas.CinderQuotas(client_mock)
        tenant_id = mock.MagicMock()
        cinder_quo.delete(tenant_id)
        client_mock.cinder().quotas.delete.assert_called_once_with(tenant_id)
