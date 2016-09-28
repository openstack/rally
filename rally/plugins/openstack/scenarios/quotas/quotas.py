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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.quotas import utils
from rally.task import validation

"""Scenarios for quotas."""


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["nova.quotas"]},
                    name="Quotas.nova_update")
class NovaUpdate(utils.QuotasScenario):

    def run(self, max_quota=1024):
        """Update quotas for Nova.

        :param max_quota: Max value to be updated for quota.
        """

        self._update_quotas("nova", self.context["tenant"]["id"],
                            max_quota)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["nova.quotas"]},
                    name="Quotas.nova_update_and_delete")
class NovaUpdateAndDelete(utils.QuotasScenario):

    def run(self, max_quota=1024):
        """Update and delete quotas for Nova.

        :param max_quota: Max value to be updated for quota.
        """

        self._update_quotas("nova", self.context["tenant"]["id"],
                            max_quota)
        self._delete_quotas("nova", self.context["tenant"]["id"])


@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["cinder.quotas"]},
                    name="Quotas.cinder_update")
class CinderUpdate(utils.QuotasScenario):

    def run(self, max_quota=1024):
        """Update quotas for Cinder.

        :param max_quota: Max value to be updated for quota.
        """

        self._update_quotas("cinder", self.context["tenant"]["id"],
                            max_quota)


@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["cinder.quotas"]},
                    name="Quotas.cinder_update_and_delete")
class CinderUpdateAndDelete(utils.QuotasScenario):

    def run(self, max_quota=1024):
        """Update and Delete quotas for Cinder.

        :param max_quota: Max value to be updated for quota.
        """

        self._update_quotas("cinder", self.context["tenant"]["id"],
                            max_quota)
        self._delete_quotas("cinder", self.context["tenant"]["id"])


@validation.required_services(consts.Service.NEUTRON)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["neutron.quota"]},
                    name="Quotas.neutron_update")
class NeutronUpdate(utils.QuotasScenario):

    def run(self, max_quota=1024):
        """Update quotas for neutron.

        :param max_quota: Max value to be updated for quota.
        """

        quota_update_fn = self.admin_clients("neutron").update_quota
        self._update_quotas("neutron", self.context["tenant"]["id"],
                            max_quota, quota_update_fn)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["nova.quotas"]},
                    name="Quotas.nova_get")
class NovaGet(utils.QuotasScenario):

    def run(self):
        """Get quotas for nova."""

        self._get_quotas("nova", self.context["tenant"]["id"])
