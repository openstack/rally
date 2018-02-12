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

from rally.common import broker
from rally.common import cfg
from rally.common import logging
from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.openstack import osclients
from rally.plugins.openstack.services.identity import identity
from rally.task import context


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="roles", platform="openstack", order=330)
class RoleGenerator(context.Context):
    """Context class for assigning roles for users."""

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "items": {
            "type": "string",
            "description": "The name of role to assign to user"
        }
    }

    def __init__(self, ctx):
        super(RoleGenerator, self).__init__(ctx)
        self.credential = self.context["admin"]["credential"]
        self.workers = (
            cfg.CONF.openstack.roles_context_resource_management_workers)

    def _get_role_object(self, context_role):
        """Check if role exists.

        :param context_role: name of existing role.
        """
        keystone = identity.Identity(osclients.Clients(self.credential))
        default_roles = keystone.list_roles()
        for def_role in default_roles:
            if str(def_role.name) == context_role:
                return def_role
        else:
            raise exceptions.NotFoundException(
                "There is no role with name `%s`" % context_role)

    def _get_user_role_ids(self, user_id, project_id):
        keystone = identity.Identity(osclients.Clients(self.credential))
        user_roles = keystone.list_roles(user_id=user_id,
                                         project_id=project_id)
        return [role.id for role in user_roles]

    def _get_consumer(self, func_name):
        def consume(cache, args):
            role_id, user_id, project_id = args
            if "client" not in cache:
                clients = osclients.Clients(self.credential)
                cache["client"] = identity.Identity(clients)
            getattr(cache["client"], func_name)(role_id=role_id,
                                                user_id=user_id,
                                                project_id=project_id)
        return consume

    def setup(self):
        """Add all roles to users."""
        threads = self.workers
        roles_dict = {}

        def publish(queue):
            for context_role in self.config:
                role = self._get_role_object(context_role)
                roles_dict[role.id] = role.name
                LOG.debug("Adding role %(role_name)s having ID %(role_id)s "
                          "to all users using %(threads)s threads"
                          % {"role_name": role.name,
                             "role_id": role.id,
                             "threads": threads})
                for user in self.context["users"]:
                    if "roles" not in user:
                        user["roles"] = self._get_user_role_ids(
                            user["id"],
                            user["tenant_id"])
                        user["assigned_roles"] = []
                    if role.id not in user["roles"]:
                        args = (role.id, user["id"], user["tenant_id"])
                        queue.append(args)
                        user["assigned_roles"].append(role.id)

        broker.run(publish, self._get_consumer("add_role"), threads)
        self.context["roles"] = roles_dict

    def cleanup(self):
        """Remove assigned roles from users."""
        threads = self.workers

        def publish(queue):
            for role_id in self.context["roles"]:
                LOG.debug("Removing assigned role %s from all users" % role_id)
                for user in self.context["users"]:
                    if role_id in user["assigned_roles"]:
                        args = (role_id, user["id"], user["tenant_id"])
                        queue.append(args)

        broker.run(publish, self._get_consumer("revoke_role"), threads)
