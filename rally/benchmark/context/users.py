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

from rally.benchmark.context import base
from rally import consts
from rally.objects import endpoint
from rally.openstack.common import log as logging
from rally import osclients


LOG = logging.getLogger(__name__)


class UserGenerator(base.Context):
    """Context class for generating temporary users/tenants for benchmarks."""

    __ctx_name__ = "users"

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": "http://json-schema.org/draft-03/schema",
        "properties": {
            "tenants": {
                "type": "integer",
                "minimum": 1
            },
            "users_per_tenant": {
                "type": "integer",
                "minimum": 1
            }
        },
        "additionalProperties": False
    }

    def __init__(self, context):
        super(UserGenerator, self).__init__(context)
        self.config.setdefault("tenants", 1)
        self.config.setdefault("users_per_tenant", 1)

        self.context["users"] = []
        self.context["tenants"] = []
        # NOTE(boris-42): I think this is the best place for adding logic when
        #                 we are using pre created users or temporary. So we
        #                 should rename this class s/UserGenerator/UserContext/
        #                 and change a bit logic of populating lists of users
        #                 and tenants
        self.clients = osclients.Clients(context["admin"]["endpoint"])

    def _create_user(self, user_id, tenant_id):
        pattern = "%(tenant_id)s_user_%(uid)d"
        name = pattern % {"tenant_id": tenant_id, "uid": user_id}
        email = "%s@email.me" % name
        return self.clients.keystone().users.create(name, "password",
                                                    email, tenant_id)

    def _create_tenant(self, run_id, i):
        pattern = "temp_%(run_id)s_tenant_%(iter)i"
        return self.clients.keystone().tenants.create(pattern %
                                                      {"run_id": run_id,
                                                       "iter": i})

    def create_users_and_tenants(self):
        run_id = str(uuid.uuid4())
        auth_url = self.clients.keystone().auth_url

        self.context["tenants"] = []
        for i in range(self.config["tenants"]):
            tenant = self._create_tenant(run_id, i)
            self.context["tenants"].append({"id": tenant.id,
                                            "name": tenant.name})

        for tenant in self.context["tenants"]:
            for user_id in range(self.config["users_per_tenant"]):
                user = self._create_user(user_id, tenant["id"])
                epoint = endpoint.Endpoint(auth_url, user.name, "password",
                                           tenant["name"],
                                           consts.EndpointPermission.USER)
                self.context["users"].append({"id": user.id,
                                              "endpoint": epoint})

    def _delete_users_and_tenants(self):
        for user in self.context["users"]:
            try:
                self.clients.keystone().users.delete(user["id"])
            except Exception as ex:
                LOG.warning("Failed to delete user: %(user_id)s. "
                            "Exception: %(ex)s" %
                            {"user_id": user["id"], "ex": ex})

        for tenant in self.context["tenants"]:
            try:
                self.clients.keystone().tenants.delete(tenant["id"])
            except Exception as ex:
                LOG.warning("Failed to delete tenant: %(tenant_id)s. "
                            "Exception: %(ex)s" %
                            {"tenant_id": tenant["id"], "ex": ex})

    def setup(self):
        self.create_users_and_tenants()

    def cleanup(self):
        self._delete_users_and_tenants()
