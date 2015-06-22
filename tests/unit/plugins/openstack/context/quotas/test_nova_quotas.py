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

from rally.plugins.openstack.context.quotas import nova_quotas as quotas
from tests.unit import test


class NovaQuotasTestCase(test.TestCase):

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    def test_update(self, mock_clients):
        nova_quotas = quotas.NovaQuotas(mock_clients)
        tenant_id = mock.MagicMock()
        quotas_values = {
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
            "security_group_rules": 50
        }
        nova_quotas.update(tenant_id, **quotas_values)
        mock_clients.nova().quotas.update.assert_called_once_with(
            tenant_id, **quotas_values)

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    def test_delete(self, mock_clients):
        nova_quotas = quotas.NovaQuotas(mock_clients)
        tenant_id = mock.MagicMock()
        nova_quotas.delete(tenant_id)
        mock_clients.nova().quotas.delete.assert_called_once_with(tenant_id)
