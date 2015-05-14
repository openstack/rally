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
import six

from rally.benchmark.scenarios.quotas import utils
from tests.unit import fakes
from tests.unit import test


class QuotasScenarioTestCase(test.TestCase):

    def setUp(self):
        super(QuotasScenarioTestCase, self).setUp()

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
        fake_nova = fakes.FakeNovaClient()
        fake_nova.quotas.update = mock.MagicMock(return_value=quotas)
        fake_clients = fakes.FakeClients()
        fake_clients._nova = fake_nova
        scenario = utils.QuotasScenario(admin_clients=fake_clients)
        scenario._generate_quota_values = mock.MagicMock(return_value=quotas)

        result = scenario._update_quotas("nova", tenant_id)

        self.assertEqual(quotas, result)
        fake_nova.quotas.update.assert_called_once_with(tenant_id, **quotas)
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
        fake_nova = fakes.FakeNovaClient()
        fake_nova.quotas.update = mock.MagicMock(return_value=quotas)
        fake_clients = fakes.FakeClients()
        fake_clients._nova = fake_nova
        scenario = utils.QuotasScenario(admin_clients=fake_clients)
        scenario._generate_quota_values = mock.MagicMock(return_value=quotas)

        mock_quota = mock.Mock(return_value=quotas)

        result = scenario._update_quotas("nova", tenant_id,
                                         quota_update_fn=mock_quota)

        self.assertEqual(quotas, result)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "quotas.update_quotas")

    def test__generate_quota_values_nova(self):
        max_quota = 1024
        scenario = utils.QuotasScenario(admin_clients=fakes.FakeClients())
        quotas = scenario._generate_quota_values(max_quota, "nova")
        for k, v in six.iteritems(quotas):
            self.assertTrue(-1 <= v <= max_quota)

    def test__generate_quota_values_cinder(self):
        max_quota = 1024
        scenario = utils.QuotasScenario(admin_clients=fakes.FakeClients())
        quotas = scenario._generate_quota_values(max_quota, "cinder")
        for k, v in six.iteritems(quotas):
            self.assertTrue(-1 <= v <= max_quota)

    def test__generate_quota_values_neutron(self):
        max_quota = 1024
        scenario = utils.QuotasScenario(admin_clients=fakes.FakeClients())
        quotas = scenario._generate_quota_values(max_quota, "neutron")
        for v in six.itervalues(quotas):
            for v1 in six.itervalues(v):
                for v2 in six.itervalues(v1):
                    self.assertTrue(-1 <= v2 <= max_quota)

    def test__delete_quotas(self):
        tenant_id = "fake_tenant"
        fake_nova = fakes.FakeNovaClient()
        fake_nova.quotas.delete = mock.MagicMock()
        fake_clients = fakes.FakeClients()
        fake_clients._nova = fake_nova
        scenario = utils.QuotasScenario(admin_clients=fake_clients)

        scenario._delete_quotas("nova", tenant_id)

        fake_nova.quotas.delete.assert_called_once_with(tenant_id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "quotas.delete_quotas")
