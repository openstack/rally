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

from rally.benchmark.scenarios.quotas import quotas
from tests import test


class QuotasTestCase(test.TestCase):

    def test_nova_update(self):
        scenario = quotas.Quotas(context={"user": {"tenant_id": "fake"}})
        scenario._update_quotas = mock.MagicMock()
        scenario.nova_update(max_quota=1024)
        scenario._update_quotas.assert_called_once_with('nova', 'fake', 1024)

    def test_nova_update_and_delete(self):
        scenario = quotas.Quotas(context={"user": {"tenant_id": "fake"}})
        scenario._update_quotas = mock.MagicMock()
        scenario._delete_quotas = mock.MagicMock()
        scenario.nova_update_and_delete(max_quota=1024)
        scenario._update_quotas.assert_called_once_with('nova', 'fake', 1024)
        scenario._delete_quotas.assert_called_once_with('nova', 'fake')

    def test_cinder_update(self):
        scenario = quotas.Quotas(context={"user": {"tenant_id": "fake"}})
        scenario._update_quotas = mock.MagicMock()
        scenario.cinder_update(max_quota=1024)
        scenario._update_quotas.assert_called_once_with('cinder', 'fake', 1024)
