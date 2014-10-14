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

from rally.benchmark.context import base
from rally import exceptions
from rally.i18n import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class RoleGenerator(base.Context):
    """Context class for adding temporary roles for benchmarks."""

    __ctx_name__ = "roles"
    __ctx_order__ = 101
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": rutils.JSON_SCHEMA,
        "items": {
            "type": "string",
        },
        "additionalProperties": False
    }

    def __init__(self, context):
        super(RoleGenerator, self).__init__(context)
        self.context["roles"] = []
        self.endpoint = self.context["admin"]["endpoint"]

    def _add_role(self, admin_endpoint, context_role):
        """Add role to users.

        :param admin_endpoint: The base url.
        :param context_role: name of existing role.
        """
        client = osclients.Clients(admin_endpoint).keystone()
        default_roles = client.roles.list()
        for def_role in default_roles:
            if str(def_role.name) == context_role:
                role = def_role
                break
        else:
            raise exceptions.NoSuchRole(role=context_role)

        LOG.debug("Adding role %s to all users" % (role.id))
        for user in self.context["users"]:
            client.roles.add_user_role(user["id"], role.id,
                                       tenant=user["tenant_id"])

        return {"id": str(role.id), "name": str(role.name)}

    def _remove_role(self, admin_endpoint, role):
        """Remove given role from users.

        :param admin_endpoint: The base url.
        :param role: dictionary with role parameters (id, name).
        """
        client = osclients.Clients(admin_endpoint).keystone()

        for user in self.context["users"]:
            try:
                client.roles.remove_user_role(
                    user["id"], role["id"], tenant=user["tenant_id"])
            except Exception as ex:
                LOG.warning("Failed to remove role: %(role_id)s. "
                            "Exception: %(ex)s" %
                            {"role_id": role["id"], "ex": ex})

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `roles`"))
    def setup(self):
        """Add roles to all users."""
        for name in self.config:
            role = self._add_role(self.endpoint, name)
            self.context["roles"].append(role)

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `roles`"))
    def cleanup(self):
        """Remove roles from users."""
        for role in self.context["roles"]:
            self._remove_role(self.endpoint, role)
