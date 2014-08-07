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

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark.scenarios.quotas import utils


class Quotas(utils.QuotasScenario):

    @scenario_base.scenario(admin_only=True, context={"cleanup": ["quotas"]})
    def nova_update(self, max_quota=1024):
        """Tests updating quotas for nova.

        :param max_quota: Max value to be updated for quota.
        """
        tenant_id = self.context()["user"]["tenant_id"]
        self._update_quotas('nova', tenant_id, max_quota)

    @scenario_base.scenario(admin_only=True, context={"cleanup": ["quotas"]})
    def nova_update_and_delete(self, max_quota=1024):
        """Tests updating and deleting quotas for nova.

        :param max_quota: Max value to be updated for quota.
        """

        tenant_id = self.context()["user"]["tenant_id"]
        self._update_quotas('nova', tenant_id, max_quota)
        self._delete_quotas('nova', tenant_id)

    @scenario_base.scenario(admin_only=True, context={"cleanup": ["quotas"]})
    def cinder_update(self, max_quota=1024):
        """Tests updating quotas for cinder.

        :param max_quota: Max value to be updated for quota.
        """
        tenant_id = self.context()["user"]["tenant_id"]
        self._update_quotas('cinder', tenant_id, max_quota)
