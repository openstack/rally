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

import collections
import uuid

from oslo.config import cfg

from rally.benchmark.context import base
from rally.benchmark import utils
from rally.benchmark.wrappers import keystone
from rally import broker
from rally import consts
from rally import exceptions
from rally.i18n import _
from rally import log as logging
from rally.objects import endpoint
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)

context_opts = [
    cfg.IntOpt("resource_management_workers",
               default=30,
               help="How many concurrent threads use for serving users "
                    "context"),
    cfg.StrOpt("project_domain",
               default="default",
               help="ID of domain in which projects will be created."),
    cfg.StrOpt("user_domain",
               default="default",
               help="ID of domain in which users will be created."),
]

CONF = cfg.CONF
CONF.register_opts(context_opts,
                   group=cfg.OptGroup(name='users_context',
                                      title='benchmark context options'))


class UserGenerator(base.Context):
    """Context class for generating temporary users/tenants for benchmarks."""

    __ctx_name__ = "users"
    __ctx_order__ = 100
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
            "tenants": {
                "type": "integer",
                "minimum": 1
            },
            "users_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "resource_management_workers": {
                "type": "integer",
                "minimum": 1
            },
            "project_domain": {
                "type": "string",
            },
            "user_domain": {
                "type": "string",
            },
        },
        "additionalProperties": False
    }
    PATTERN_TENANT = "ctx_rally_%(task_id)s_tenant_%(iter)i"
    PATTERN_USER = "ctx_rally_%(tenant_id)s_user_%(uid)d"

    def __init__(self, context):
        super(UserGenerator, self).__init__(context)
        self.config.setdefault("tenants", 1)
        self.config.setdefault("users_per_tenant", 1)
        self.config.setdefault(
            "resource_management_workers",
            cfg.CONF.users_context.resource_management_workers)
        self.config.setdefault("project_domain",
                               cfg.CONF.users_context.project_domain)
        self.config.setdefault("user_domain",
                               cfg.CONF.users_context.user_domain)
        self.context["users"] = []
        self.context["tenants"] = []
        self.endpoint = self.context["admin"]["endpoint"]
        # NOTE(boris-42): I think this is the best place for adding logic when
        #                 we are using pre created users or temporary. So we
        #                 should rename this class s/UserGenerator/UserContext/
        #                 and change a bit logic of populating lists of users
        #                 and tenants

    def _remove_associated_networks(self):
        """Delete associated Nova networks from tenants."""
        # NOTE(rmk): Ugly hack to deal with the fact that Nova Network
        # networks can only be disassociated in an admin context. Discussed
        # with boris-42 before taking this approach [LP-Bug #1350517].
        clients = osclients.Clients(self.endpoint)
        if consts.Service.NOVA not in clients.services().values():
            return

        nova_admin = clients.nova()

        if not utils.check_service_status(nova_admin, 'nova-network'):
            return

        for network in nova_admin.networks.list():
            network_tenant_id = nova_admin.networks.get(network).project_id
            for tenant in self.context["tenants"]:
                if tenant["id"] == network_tenant_id:
                    try:
                        nova_admin.networks.disassociate(network)
                    except Exception as ex:
                        LOG.warning("Failed disassociate net: %(tenant_id)s. "
                                    "Exception: %(ex)s" %
                                    {"tenant_id": tenant["id"], "ex": ex})

    def _create_tenants(self):
        threads = self.config["resource_management_workers"]

        tenants = collections.deque()

        def publish(queue):
            for i in range(self.config["tenants"]):
                args = (self.config["project_domain"], self.task["uuid"], i)
                queue.append(args)

        def consume(cache, args):
            domain, task_id, i = args
            if "client" not in cache:
                clients = osclients.Clients(self.endpoint)
                cache["client"] = keystone.wrap(clients.keystone())
            tenant = cache["client"].create_project(
                self.PATTERN_TENANT % {"task_id": task_id, "iter": i}, domain)
            tenant_dict = {"id": tenant.id, "name": tenant.name}
            tenants.append(tenant_dict)

        # NOTE(msdubov): cosume() will fill the tenants list in the closure.
        broker.run(publish, consume, threads)
        return list(tenants)

    def _create_users(self):
        # NOTE(msdubov): This should be called after _create_tenants().
        threads = self.config["resource_management_workers"]
        users_per_tenant = self.config["users_per_tenant"]

        users = collections.deque()

        def publish(queue):
            for tenant in self.context["tenants"]:
                for user_id in range(users_per_tenant):
                    username = self.PATTERN_USER % {"tenant_id": tenant["id"],
                                                    "uid": user_id}
                    password = str(uuid.uuid4())
                    args = (username, password, self.config["project_domain"],
                            self.config["user_domain"], tenant)
                    queue.append(args)

        def consume(cache, args):
            username, password, project_dom, user_dom, tenant = args
            if "client" not in cache:
                clients = osclients.Clients(self.endpoint)
                cache["client"] = keystone.wrap(clients.keystone())
            client = cache["client"]
            user = client.create_user(username, password,
                                      "%s@email.me" % username,
                                      tenant["id"], user_dom)
            user_endpoint = endpoint.Endpoint(
                    client.auth_url, user.name, password, tenant["name"],
                    consts.EndpointPermission.USER, client.region_name,
                    project_domain_name=project_dom, user_domain_name=user_dom)
            users.append({"id": user.id,
                          "endpoint": user_endpoint,
                          "tenant_id": tenant["id"]})

        # NOTE(msdubov): cosume() will fill the users list in the closure.
        broker.run(publish, consume, threads)
        return list(users)

    def _delete_tenants(self):
        threads = self.config["resource_management_workers"]

        self._remove_associated_networks()

        def publish(queue):
            for tenant in self.context["tenants"]:
                queue.append(tenant["id"])

        def consume(cache, tenant_id):
            if "client" not in cache:
                clients = osclients.Clients(self.endpoint)
                cache["client"] = keystone.wrap(clients.keystone())
            cache["client"].delete_project(tenant_id)

        broker.run(publish, consume, threads)
        self.context["tenants"] = []

    def _delete_users(self):
        threads = self.config["resource_management_workers"]

        def publish(queue):
            for user in self.context["users"]:
                queue.append(user["id"])

        def consume(cache, user_id):
            if "client" not in cache:
                clients = osclients.Clients(self.endpoint)
                cache["client"] = keystone.wrap(clients.keystone())
            cache["client"].delete_user(user_id)

        broker.run(publish, consume, threads)
        self.context["users"] = []

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `users`"))
    def setup(self):
        """Create tenants and users, using the broker pattern."""
        threads = self.config["resource_management_workers"]

        LOG.debug("Creating %(tenants)d tenants using %(threads)s threads" %
                  {"tenants": self.config["tenants"], "threads": threads})
        self.context["tenants"] = self._create_tenants()

        if len(self.context["tenants"]) < self.config["tenants"]:
            raise exceptions.ContextSetupFailure(
                    ctx_name=self.__ctx_name__,
                    msg=_("Failed to create the requested number of tenants."))

        users_num = self.config["users_per_tenant"] * self.config["tenants"]
        LOG.debug("Creating %(users)d users using %(threads)s threads" %
                  {"users": users_num, "threads": threads})
        self.context["users"] = self._create_users()

        if len(self.context["users"]) < users_num:
            raise exceptions.ContextSetupFailure(
                    ctx_name=self.__ctx_name__,
                    msg=_("Failed to create the requested number of users."))

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `users`"))
    def cleanup(self):
        """Delete tenants and users, using the broker pattern."""
        self._delete_users()
        self._delete_tenants()
