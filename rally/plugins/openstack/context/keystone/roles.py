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

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.wrappers import keystone
from rally.task import context

LOG = logging.getLogger(__name__)


@context.configure(name="roles", order=330)
class RoleGenerator(context.Context):
    """Context class for adding temporary roles for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "items": {
            "type": "string",
        },
        "additionalProperties": False
    }

    def __init__(self, ctx):
        super(RoleGenerator, self).__init__(ctx)
        self.endpoint = self.context["admin"]["endpoint"]

    def _add_role(self, admin_endpoint, context_role):
        """Add role to users.

        :param admin_endpoint: The base url.
        :param context_role: name of existing role.
        """
        client = keystone.wrap(osclients.Clients(admin_endpoint).keystone())
        default_roles = client.list_roles()
        for def_role in default_roles:
            if str(def_role.name) == context_role:
                role = def_role
                break
        else:
            raise exceptions.NoSuchRole(role=context_role)

        LOG.debug("Adding role %s to all users" % (role.id))
        for user in self.context["users"]:
            client.add_role(user_id=user["id"], role_id=role.id,
                            project_id=user["tenant_id"])

        return {"id": str(role.id), "name": str(role.name)}

    def _remove_role(self, admin_endpoint, role):
        """Remove given role from users.

        :param admin_endpoint: The base url.
        :param role: dictionary with role parameters (id, name).
        """
        client = keystone.wrap(osclients.Clients(admin_endpoint).keystone())

        for user in self.context["users"]:
            with logging.ExceptionLogger(
                    LOG, _("Failed to remove role: %s") % role["id"]):
                client.remove_role(
                    user_id=user["id"], role_id=role["id"],
                    project_id=user["tenant_id"])

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `roles`"))
    def setup(self):
        """Add roles to all users."""
        self.context["roles"] = [self._add_role(self.endpoint, name)
                                 for name in self.config]

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `roles`"))
    def cleanup(self):
        """Remove roles from users."""
        for role in self.context["roles"]:
            self._remove_role(self.endpoint, role)
