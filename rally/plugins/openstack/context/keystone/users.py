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
import random
import uuid

from oslo_config import cfg
import six

from rally.common import broker
from rally.common.i18n import _
from rally.common import logging
from rally.common import objects
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.wrappers import keystone
from rally.plugins.openstack.wrappers import network
from rally.task import context
from rally.task import utils

LOG = logging.getLogger(__name__)

USER_CONTEXT_OPTS = [
    cfg.IntOpt("resource_management_workers",
               default=20,
               help="How many concurrent threads use for serving users "
                    "context"),
    cfg.StrOpt("project_domain",
               default="default",
               help="ID of domain in which projects will be created."),
    cfg.StrOpt("user_domain",
               default="default",
               help="ID of domain in which users will be created."),
    cfg.StrOpt("keystone_default_role",
               default="member",
               help="The default role name of the keystone."),
]

CONF = cfg.CONF
CONF.register_opts(USER_CONTEXT_OPTS,
                   group=cfg.OptGroup(name="users_context",
                                      title="benchmark context options"))


class UserContextMixin(object):

    @property
    def user_choice_method(self):
        if not hasattr(self, "_user_choice_method"):
            self._user_choice_method = self.context["config"].get(
                "users", {}).get("user_choice_method")
            if self._user_choice_method is None:
                # NOTE(vponomaryov): consider 'existing_users' context
                # picking up value for 'user_choice_method'
                # when it is supported there.
                # Until it happens we use old "random" approach for
                # 'existing_users' context.
                self._user_choice_method = "random"
        return self._user_choice_method

    def map_for_scenario(self, context_obj):
        """Pass only context of one user and related to it tenant to scenario.

        We are choosing on each iteration one user

        """
        scenario_ctx = {}
        for key, value in six.iteritems(context_obj):
            if key not in ["users", "tenants"]:
                scenario_ctx[key] = value

        if self.user_choice_method == "random":
            user = random.choice(context_obj["users"])
            tenant = context_obj["tenants"][user["tenant_id"]]
        else:
            # Second and last case - 'round_robin'.
            tenants_amount = len(context_obj["tenants"])
            # NOTE(amaretskiy): iteration is subtracted by `1' because it
            #                   starts from `1' but we count from `0'
            tenant_index = int((context_obj["iteration"] - 1) % tenants_amount)
            tenant_id = sorted(context_obj["tenants"].keys())[tenant_index]
            tenant = context_obj["tenants"][tenant_id]
            users = context_obj["tenants"][tenant_id]["users"]
            user_index = int(((context_obj["iteration"] - 1) / tenants_amount)
                             % len(users))
            user = users[user_index]

        scenario_ctx["user"], scenario_ctx["tenant"] = user, tenant

        return scenario_ctx


@context.configure(name="users", order=100)
class UserGenerator(UserContextMixin, context.Context):
    """Context class for generating temporary users/tenants for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
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
            "user_choice_method": {
                "enum": ["random", "round_robin"],
            },
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "tenants": 1,
        "users_per_tenant": 1,
        "resource_management_workers":
            cfg.CONF.users_context.resource_management_workers,
        "project_domain": cfg.CONF.users_context.project_domain,
        "user_domain": cfg.CONF.users_context.user_domain,
        "user_choice_method": "random",
    }

    def __init__(self, context):
        super(UserGenerator, self).__init__(context)
        self.credential = self.context["admin"]["credential"]

    def _remove_default_security_group(self):
        """Delete default security group for tenants."""
        clients = osclients.Clients(self.credential)

        if consts.Service.NEUTRON not in clients.services().values():
            return

        use_sg, msg = network.wrap(clients, self).supports_extension(
            "security-group")
        if not use_sg:
            LOG.debug("Security group context is disabled: %s" % msg)
            return

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            with logging.ExceptionLogger(
                    LOG, _("Unable to delete default security group")):
                uclients = osclients.Clients(user["credential"])
                sg = uclients.nova().security_groups.find(name="default")
                clients.neutron().delete_security_group(sg.id)

    def _remove_associated_networks(self):
        """Delete associated Nova networks from tenants."""
        # NOTE(rmk): Ugly hack to deal with the fact that Nova Network
        # networks can only be disassociated in an admin context. Discussed
        # with boris-42 before taking this approach [LP-Bug #1350517].
        clients = osclients.Clients(self.credential)
        if consts.Service.NOVA not in clients.services().values():
            return

        nova_admin = clients.nova()

        if not utils.check_service_status(nova_admin, "nova-network"):
            return

        for net in nova_admin.networks.list():
            network_tenant_id = nova_admin.networks.get(net).project_id
            if network_tenant_id in self.context["tenants"]:
                try:
                    nova_admin.networks.disassociate(net)
                except Exception as ex:
                    LOG.warning("Failed disassociate net: %(tenant_id)s. "
                                "Exception: %(ex)s" %
                                {"tenant_id": network_tenant_id, "ex": ex})

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
                clients = osclients.Clients(self.credential)
                cache["client"] = keystone.wrap(clients.keystone())
            tenant = cache["client"].create_project(
                self.generate_random_name(), domain)
            tenant_dict = {"id": tenant.id, "name": tenant.name, "users": []}
            tenants.append(tenant_dict)

        # NOTE(msdubov): consume() will fill the tenants list in the closure.
        broker.run(publish, consume, threads)
        tenants_dict = {}
        for t in tenants:
            tenants_dict[t["id"]] = t

        return tenants_dict

    def _create_users(self):
        # NOTE(msdubov): This should be called after _create_tenants().
        threads = self.config["resource_management_workers"]
        users_per_tenant = self.config["users_per_tenant"]
        default_role = cfg.CONF.users_context.keystone_default_role

        users = collections.deque()

        def publish(queue):
            for tenant_id in self.context["tenants"]:
                for user_id in range(users_per_tenant):
                    username = self.generate_random_name()
                    password = str(uuid.uuid4())
                    args = (username, password, self.config["project_domain"],
                            self.config["user_domain"], tenant_id)
                    queue.append(args)

        def consume(cache, args):
            username, password, project_dom, user_dom, tenant_id = args
            if "client" not in cache:
                clients = osclients.Clients(self.credential)
                cache["client"] = keystone.wrap(clients.keystone())
            client = cache["client"]
            user = client.create_user(
                username, password,
                "%s@email.me" % username,
                tenant_id, user_dom,
                default_role=default_role)
            user_credential = objects.Credential(
                client.auth_url, user.name, password,
                self.context["tenants"][tenant_id]["name"],
                consts.EndpointPermission.USER, client.region_name,
                project_domain_name=project_dom, user_domain_name=user_dom,
                endpoint_type=self.credential.endpoint_type,
                https_insecure=self.credential.insecure,
                https_cacert=self.credential.cacert)
            users.append({"id": user.id,
                          "credential": user_credential,
                          "tenant_id": tenant_id})

        # NOTE(msdubov): consume() will fill the users list in the closure.
        broker.run(publish, consume, threads)
        return list(users)

    def _get_consumer_for_deletion(self, func_name):
        def consume(cache, resource_id):
            if "client" not in cache:
                clients = osclients.Clients(self.credential)
                cache["client"] = keystone.wrap(clients.keystone())
            getattr(cache["client"], func_name)(resource_id)
        return consume

    def _delete_tenants(self):
        threads = self.config["resource_management_workers"]

        self._remove_associated_networks()

        def publish(queue):
            for tenant_id in self.context["tenants"]:
                queue.append(tenant_id)

        broker.run(publish, self._get_consumer_for_deletion("delete_project"),
                   threads)
        self.context["tenants"] = {}

    def _delete_users(self):
        threads = self.config["resource_management_workers"]

        def publish(queue):
            for user in self.context["users"]:
                queue.append(user["id"])

        broker.run(publish, self._get_consumer_for_deletion("delete_user"),
                   threads)
        self.context["users"] = []

    @logging.log_task_wrapper(LOG.info, _("Enter context: `users`"))
    def setup(self):
        """Create tenants and users, using the broker pattern."""
        self.context["users"] = []
        self.context["tenants"] = {}

        threads = self.config["resource_management_workers"]

        LOG.debug("Creating %(tenants)d tenants using %(threads)s threads" %
                  {"tenants": self.config["tenants"], "threads": threads})
        self.context["tenants"] = self._create_tenants()

        if len(self.context["tenants"]) < self.config["tenants"]:
            raise exceptions.ContextSetupFailure(
                ctx_name=self.get_name(),
                msg=_("Failed to create the requested number of tenants."))

        users_num = self.config["users_per_tenant"] * self.config["tenants"]
        LOG.debug("Creating %(users)d users using %(threads)s threads" %
                  {"users": users_num, "threads": threads})
        self.context["users"] = self._create_users()
        for user in self.context["users"]:
            self.context["tenants"][user["tenant_id"]]["users"].append(user)

        if len(self.context["users"]) < users_num:
            raise exceptions.ContextSetupFailure(
                ctx_name=self.get_name(),
                msg=_("Failed to create the requested number of users."))

    @logging.log_task_wrapper(LOG.info, _("Exit context: `users`"))
    def cleanup(self):
        """Delete tenants and users, using the broker pattern."""
        self._remove_default_security_group()
        self._delete_users()
        self._delete_tenants()
