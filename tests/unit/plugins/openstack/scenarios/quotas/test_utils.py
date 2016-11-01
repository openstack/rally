# Copyright 2014: Kylin Cloud
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

from rally.plugins.openstack.scenarios.quotas import utils
from tests.unit import test


class QuotasScenarioTestCase(test.ScenarioTestCase):

    def test__update_quotas(self):
        tenant_id = "fake_tenant"
        quotas = {
            "metadata_items": 10,
            "key_pairs": 10,
            "injected_file_content_bytes": 1024,
            "injected_file_path_bytes": 1024,
            "ram": 5120,
            "instances": 10,
            "injected_files": 10,
            "cores": 10,
        }
        self.admin_clients("nova").quotas.update.return_value = quotas
        scenario = utils.QuotasScenario(self.context)
        scenario._generate_quota_values = mock.MagicMock(return_value=quotas)

        result = scenario._update_quotas("nova", tenant_id)

        self.assertEqual(quotas, result)
        self.admin_clients("nova").quotas.update.assert_called_once_with(
            tenant_id, **quotas)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "quotas.update_quotas")

    def test__update_quotas_fn(self):
        tenant_id = "fake_tenant"
        quotas = {
            "metadata_items": 10,
            "key_pairs": 10,
            "injected_file_content_bytes": 1024,
            "injected_file_path_bytes": 1024,
            "ram": 5120,
            "instances": 10,
            "injected_files": 10,
            "cores": 10,
        }
        self.admin_clients("nova").quotas.update.return_value = quotas
        scenario = utils.QuotasScenario(self.context)
        scenario._generate_quota_values = mock.MagicMock(return_value=quotas)

        mock_quota = mock.Mock(return_value=quotas)

        result = scenario._update_quotas("nova", tenant_id,
                                         quota_update_fn=mock_quota)

        self.assertEqual(quotas, result)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "quotas.update_quotas")

    def test__generate_quota_values_nova(self):
        max_quota = 1024
        scenario = utils.QuotasScenario(self.context)
        quotas = scenario._generate_quota_values(max_quota, "nova")
        for k, v in quotas.items():
            self.assertGreaterEqual(v, -1)
            self.assertLessEqual(v, max_quota)

    def test__generate_quota_values_cinder(self):
        max_quota = 1024
        scenario = utils.QuotasScenario(self.context)
        quotas = scenario._generate_quota_values(max_quota, "cinder")
        for k, v in quotas.items():
            self.assertGreaterEqual(v, -1)
            self.assertLessEqual(v, max_quota)

    def test__generate_quota_values_neutron(self):
        max_quota = 1024
        scenario = utils.QuotasScenario(self.context)
        quotas = scenario._generate_quota_values(max_quota, "neutron")
        for v in quotas.values():
            for v1 in v.values():
                for v2 in v1.values():
                    self.assertGreaterEqual(v2, -1)
                    self.assertLessEqual(v2, max_quota)

    def test__delete_quotas(self):
        tenant_id = "fake_tenant"
        scenario = utils.QuotasScenario(self.context)
        scenario._delete_quotas("nova", tenant_id)

        self.admin_clients("nova").quotas.delete.assert_called_once_with(
            tenant_id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "quotas.delete_quotas")

    def test__get_quotas(self):
        tenant_id = "fake_tenant"
        scenario = utils.QuotasScenario(self.context)
        scenario._get_quotas("nova", tenant_id)

        self.admin_clients("nova").quotas.get.assert_called_once_with(
            tenant_id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "quotas.get_quotas")
