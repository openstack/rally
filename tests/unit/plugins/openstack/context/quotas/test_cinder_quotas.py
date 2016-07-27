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

    def test_update(self):
        mock_clients = mock.MagicMock()
        cinder_quo = cinder_quotas.CinderQuotas(mock_clients)
        tenant_id = mock.MagicMock()
        quotas_values = {
            "volumes": 10,
            "snapshots": 50,
            "gigabytes": 1000
        }
        cinder_quo.update(tenant_id, **quotas_values)
        mock_clients.cinder().quotas.update.assert_called_once_with(
            tenant_id, **quotas_values)

    def test_delete(self):
        mock_clients = mock.MagicMock()
        cinder_quo = cinder_quotas.CinderQuotas(mock_clients)
        tenant_id = mock.MagicMock()
        cinder_quo.delete(tenant_id)
        mock_clients.cinder().quotas.delete.assert_called_once_with(tenant_id)

    def test_get(self):
        tenant_id = "tenant_id"
        quotas = {"gigabytes": "gb", "snapshots": "ss", "volumes": "v"}
        quota_set = mock.MagicMock(**quotas)
        clients = mock.MagicMock()
        clients.cinder.return_value.quotas.get.return_value = quota_set
        cinder_quo = cinder_quotas.CinderQuotas(clients)

        self.assertEqual(quotas, cinder_quo.get(tenant_id))
        clients.cinder().quotas.get.assert_called_once_with(tenant_id)
