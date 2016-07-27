# Copyright 2015 Mirantis Inc.
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

from rally.plugins.openstack.context.quotas import manila_quotas
from tests.unit import test


class ManilaQuotasTestCase(test.TestCase):

    def test_update(self):
        clients = mock.MagicMock()
        instance = manila_quotas.ManilaQuotas(clients)
        tenant_id = mock.MagicMock()
        quotas_values = {
            "shares": 10,
            "gigabytes": 13,
            "snapshots": 7,
            "snapshot_gigabytes": 51,
            "share_networks": 1014,
        }

        instance.update(tenant_id, **quotas_values)

        clients.manila.return_value.quotas.update.assert_called_once_with(
            tenant_id, **quotas_values)

    def test_delete(self):
        clients = mock.MagicMock()
        instance = manila_quotas.ManilaQuotas(clients)
        tenant_id = mock.MagicMock()

        instance.delete(tenant_id)

        clients.manila.return_value.quotas.delete.assert_called_once_with(
            tenant_id)

    def test_get(self):
        tenant_id = "tenant_id"
        quotas = {"gigabytes": "gb", "snapshots": "ss", "shares": "v",
                  "snapshot_gigabytes": "sg", "share_networks": "sn"}
        quota_set = mock.MagicMock(**quotas)
        clients = mock.MagicMock()
        clients.manila.return_value.quotas.get.return_value = quota_set
        manila_quo = manila_quotas.ManilaQuotas(clients)

        self.assertEqual(quotas, manila_quo.get(tenant_id))
        clients.manila().quotas.get.assert_called_once_with(tenant_id)
