# Copyright 2014: Mirantis Inc.
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

import uuid

from rally.benchmark import utils
from rally import consts
from rally.objects import endpoint
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class UserGenerator(object):
    """Context class for generating temporary users/tenants for benchmarks."""

    def __init__(self, admin_endpoints):
        self.users = []
        self.tenants = []
        self.keystone_client = \
            utils.create_openstack_clients(admin_endpoints)["keystone"]

    def _create_user(self, user_id, tenant_id):
        pattern = "%(tenant_id)s_user_%(uid)d"
        name = pattern % {"tenant_id": tenant_id, "uid": user_id}
        email = "%s@email.me" % name
        return self.keystone_client.users.create(name, "password",
                                                 email, tenant_id)

    def _create_tenant(self, run_id, i):
        pattern = "temp_%(run_id)s_tenant_%(iter)i"
        return self.keystone_client.tenants.create(pattern % {"run_id": run_id,
                                                              "iter": i})

    def create_users_and_tenants(self, tenants, users_per_tenant):
        run_id = str(uuid.uuid4())
        auth_url = self.keystone_client.auth_url
        self.tenants = [self._create_tenant(run_id, i)
                        for i in range(tenants)]
        self.users = []
        endpoints = []
        for tenant in self.tenants:
            for user_id in range(users_per_tenant):
                user = self._create_user(user_id, tenant.id)
                self.users.append(user)
                endpoints.append(endpoint.Endpoint(
                    auth_url, user.name, "password", tenant.name,
                    consts.EndpointPermission.USER))
        return endpoints

    def _delete_users_and_tenants(self):
        for user in self.users:
            try:
                user.delete()
            except Exception:
                LOG.info("Failed to delete user: %s" % user.name)

        for tenant in self.tenants:
            try:
                tenant.delete()
            except Exception:
                LOG.info("Failed to delete tenant: %s" % tenant.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._delete_users_and_tenants()

        if exc_type:
            LOG.debug(_("Failed to generate temporary users."),
                      exc_info=(exc_type, exc_value, exc_traceback))
        else:
            LOG.debug(_("Completed deleting temporary users and tenants."))
