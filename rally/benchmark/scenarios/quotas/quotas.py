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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.quotas import utils
from rally.benchmark import validation
from rally import consts


class Quotas(utils.QuotasScenario):
    """Benchmark scenarios for quotas."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True, users=True)
    @base.scenario(context={"admin_cleanup": ["nova.quotas"]})
    def nova_update(self, max_quota=1024):
        """Update quotas for Nova.

        :param max_quota: Max value to be updated for quota.
        """
        tenant_id = self.context["user"]["tenant_id"]
        self._update_quotas("nova", tenant_id, max_quota)

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True, users=True)
    @base.scenario(context={"admin_cleanup": ["nova.quotas"]})
    def nova_update_and_delete(self, max_quota=1024):
        """Update and delete quotas for Nova.

        :param max_quota: Max value to be updated for quota.
        """

        tenant_id = self.context["user"]["tenant_id"]
        self._update_quotas("nova", tenant_id, max_quota)
        self._delete_quotas("nova", tenant_id)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(admin=True, users=True)
    @base.scenario(context={"admin_cleanup": ["cinder.quotas"]})
    def cinder_update(self, max_quota=1024):
        """Update quotas for Cinder.

        :param max_quota: Max value to be updated for quota.
        """
        tenant_id = self.context["user"]["tenant_id"]
        self._update_quotas("cinder", tenant_id, max_quota)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(admin=True, users=True)
    @base.scenario(context={"admin_cleanup": ["cinder.quotas"]})
    def cinder_update_and_delete(self, max_quota=1024):
        """Update and Delete quotas for Cinder.

        :param max_quota: Max value to be updated for quota.
        """
        tenant_id = self.context["user"]["tenant_id"]
        self._update_quotas("cinder", tenant_id, max_quota)
        self._delete_quotas("cinder", tenant_id)
