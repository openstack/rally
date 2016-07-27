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

from rally.plugins.openstack.context.quotas import designate_quotas
from tests.unit import test


class DesignateQuotasTestCase(test.TestCase):

    def test_update(self):
        clients = mock.MagicMock()
        quotas = designate_quotas.DesignateQuotas(clients)
        tenant_id = mock.MagicMock()
        quotas_values = {
            "domains": 5,
            "domain_recordsets": 20,
            "domain_records": 20,
            "recordset_records": 20,
        }
        quotas.update(tenant_id, **quotas_values)
        clients.designate().quotas.update.assert_called_once_with(
            tenant_id, quotas_values)

    def test_delete(self):
        clients = mock.MagicMock()
        quotas = designate_quotas.DesignateQuotas(clients)
        tenant_id = mock.MagicMock()
        quotas.delete(tenant_id)
        clients.designate().quotas.reset.assert_called_once_with(tenant_id)

    def test_get(self):
        tenant_id = "tenant_id"
        quotas = {"domains": -1, "domain_recordsets": 2, "domain_records": 3,
                  "recordset_records": 3}
        clients = mock.MagicMock()
        clients.designate.return_value.quotas.get.return_value = quotas
        designate_quo = designate_quotas.DesignateQuotas(clients)

        self.assertEqual(quotas, designate_quo.get(tenant_id))
        clients.designate().quotas.get.assert_called_once_with(tenant_id)
