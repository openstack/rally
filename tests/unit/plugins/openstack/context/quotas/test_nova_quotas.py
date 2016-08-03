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

from rally.plugins.openstack.context.quotas import nova_quotas
from tests.unit import test


class NovaQuotasTestCase(test.TestCase):

    def setUp(self):
        super(NovaQuotasTestCase, self).setUp()
        self.quotas = {
            "instances": 10,
            "cores": 100,
            "ram": 100000,
            "floating_ips": 100,
            "fixed_ips": 10000,
            "metadata_items": 5,
            "injected_files": 5,
            "injected_file_content_bytes": 2048,
            "injected_file_path_bytes": 1024,
            "key_pairs": 50,
            "security_groups": 50,
            "security_group_rules": 50,
            "server_group_members": 777,
            "server_groups": 33
        }

    def test_update(self):
        clients = mock.MagicMock()
        nova_quo = nova_quotas.NovaQuotas(clients)
        tenant_id = mock.MagicMock()
        nova_quo.update(tenant_id, **self.quotas)
        clients.nova().quotas.update.assert_called_once_with(tenant_id,
                                                             **self.quotas)

    def test_delete(self):
        clients = mock.MagicMock()
        nova_quo = nova_quotas.NovaQuotas(clients)
        tenant_id = mock.MagicMock()
        nova_quo.delete(tenant_id)
        clients.nova().quotas.delete.assert_called_once_with(tenant_id)

    def test_get(self):
        tenant_id = "tenant_id"
        quota_set = mock.MagicMock(**self.quotas)
        clients = mock.MagicMock()
        clients.nova.return_value.quotas.get.return_value = quota_set
        nova_quo = nova_quotas.NovaQuotas(clients)

        self.assertEqual(self.quotas, nova_quo.get(tenant_id))
        clients.nova().quotas.get.assert_called_once_with(tenant_id)
