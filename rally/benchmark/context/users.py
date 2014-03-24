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

from oslo.config import cfg
from rally.benchmark.context import base
from rally.benchmark import utils
from rally import consts
from rally.objects import endpoint
from rally.openstack.common import log as logging
from rally import osclients


LOG = logging.getLogger(__name__)

context_opts = [
    cfg.IntOpt('concurrent',
               default=1,
               help='How many concurrent threads use for'
                    ' serving users context'),
]

CONF = cfg.CONF
CONF.register_opts(context_opts,
                   group=cfg.OptGroup(name='users_context',
                                      title='benchmark context options'))


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
            },
            "concurrent": {
                "type": "integer",
                "minimum": 1
            },
        },
        "additionalProperties": False
    }
    PATTERN_TENANT = "temp_%(run_id)s_tenant_%(iter)i"
    PATTERN_USER = "%(tenant_id)s_user_%(uid)d"

    def __init__(self, context):
        super(UserGenerator, self).__init__(context)
        self.config.setdefault("tenants", 1)
        self.config.setdefault("users_per_tenant", 1)
        self.config.setdefault("concurrent",
                               cfg.CONF.users_context.concurrent)
        self.context["users"] = []
        self.context["tenants"] = []
        self.endpoint = self.context["admin"]["endpoint"]
        # NOTE(boris-42): I think this is the best place for adding logic when
        #                 we are using pre created users or temporary. So we
        #                 should rename this class s/UserGenerator/UserContext/
        #                 and change a bit logic of populating lists of users
        #                 and tenants

    @classmethod
    def _create_tenant_users(cls, args):
        """Create tenant with users and their endpoints.

        This is suitable for using with pool of threads.
        :param args: tuple arguments, for Pool.imap()
        :returns: tuple (dict tenant, list users)
        """

        admin_endpoint, users_num, run_id, i = args
        users = []

        client = osclients.Clients(admin_endpoint).keystone()
        tenant = client.tenants.create(
            cls.PATTERN_TENANT % {"run_id": run_id, "iter": i})

        LOG.debug("Creating %d users for tenant %s" % (users_num, tenant.id))

        for user_id in range(users_num):
            username = cls.PATTERN_USER % {"tenant_id": tenant.id,
                                           "uid": user_id}
            user = client.users.create(username, "password",
                                       "%s@email.me" % username, tenant.id)
            user_endpoint = endpoint.Endpoint(client.auth_url, user.name,
                                              "password", tenant.name,
                                              consts.EndpointPermission.USER)
            users.append({"id": user.id, "endpoint": user_endpoint})

        return ({"id": tenant.id, "name": tenant.name}, users)

    def setup(self):
        """Create tenants and users, using pool of threads."""

        users_num = self.config["users_per_tenant"]
        run_id = str(uuid.uuid4())

        args = [(self.endpoint, users_num, run_id, i)
                for i in range(self.config["tenants"])]

        LOG.debug("Creating %d users using %s threads" % (
                users_num * self.config["tenants"], self.config["concurrent"]))

        for tenant, users in utils.run_concurrent(
                self.config["concurrent"],
                self._create_tenant_users,
                args):
            self.context["tenants"].append(tenant)
            self.context["users"] += users

    # TODO(amaretskiy): re-implement this method using pool of threads
    def cleanup(self):
        """Delete tenants and users."""

        self.clients = osclients.Clients(self.context["admin"]["endpoint"])

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

        # NOTE(amaretskiy): Consider that after cleanup() is complete, this has
        #                   actually deleted (all or some of) users and tenants
        #                   in openstack, but we *STILL HAVE*
        #                   self.context["users"] and self.context["tenants"].
        #                   Should we ignore that, or just reset these lists
        #                   after cleanup() is done, or actually synchronize
        #                   for all successfully deleted objects?
