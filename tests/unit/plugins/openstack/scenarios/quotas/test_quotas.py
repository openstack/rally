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

from rally.plugins.openstack.scenarios.quotas import quotas
from tests.unit import test


class QuotasTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(QuotasTestCase, self).setUp()
        self.context.update({
            "user": {
                "tenant_id": "fake",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake"}
        })

    def test_nova_update(self):
        scenario = quotas.NovaUpdate(self.context)
        scenario._update_quotas = mock.MagicMock()
        scenario.run(max_quota=1024)
        scenario._update_quotas.assert_called_once_with("nova", "fake", 1024)

    def test_nova_update_and_delete(self):
        scenario = quotas.NovaUpdateAndDelete(self.context)
        scenario._update_quotas = mock.MagicMock()
        scenario._delete_quotas = mock.MagicMock()
        scenario.run(max_quota=1024)
        scenario._update_quotas.assert_called_once_with("nova", "fake", 1024)
        scenario._delete_quotas.assert_called_once_with("nova", "fake")

    def test_cinder_update(self):
        scenario = quotas.CinderUpdate(self.context)
        scenario._update_quotas = mock.MagicMock()
        scenario.run(max_quota=1024)
        scenario._update_quotas.assert_called_once_with("cinder", "fake", 1024)

    def test_cinder_update_and_delete(self):
        scenario = quotas.CinderUpdateAndDelete(self.context)
        scenario._update_quotas = mock.MagicMock()
        scenario._delete_quotas = mock.MagicMock()
        scenario.run(max_quota=1024)
        scenario._update_quotas.assert_called_once_with("cinder", "fake", 1024)
        scenario._delete_quotas.assert_called_once_with("cinder", "fake")

    def test_neutron_update(self):
        scenario = quotas.NeutronUpdate(self.context)
        scenario._update_quotas = mock.MagicMock()
        mock_quota_update_fn = self.admin_clients("neutron").update_quota
        scenario.run(max_quota=1024)
        scenario._update_quotas.assert_called_once_with("neutron", "fake",
                                                        1024,
                                                        mock_quota_update_fn)
