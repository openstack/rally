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

import functools
import sys

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import utils
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class ResourceCleaner(base.Context):
    """Context class for resource cleanup (both admin and non-admin)."""

    __ctx_name__ = "cleanup"
    __ctx_order__ = 200
    __ctx_hidden__ = True

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": rutils.JSON_SCHEMA,
        "items": {
            "type": "string",
            "enum": ["nova", "glance", "cinder",
                     "quotas", "neutron", "ceilometer"]
        },
        "uniqueItems": True
    }

    def __init__(self, context):
        super(ResourceCleaner, self).__init__(context)
        self.admin = []
        self.users = []

    @rutils.log_task_wrapper(LOG.info, _("Cleanup users resources."))
    def _cleanup_users_resources(self):
        for user in self.users:
            clients = osclients.Clients(user)
            admin_clients = functools.partial(osclients.Clients, self.admin)
            tenant_id = clients.keystone().tenant_id
            cleanup_methods = {
                "nova": (utils.delete_nova_resources, clients.nova),
                "glance": (utils.delete_glance_resources, clients.glance,
                           tenant_id),
                "cinder": (utils.delete_cinder_resources, clients.cinder),
                "quotas": (utils.delete_quotas, admin_clients,
                           tenant_id),
                "neutron": (utils.delete_neutron_resources, clients.neutron,
                            tenant_id),
                "ceilometer": (utils.delete_ceilometer_resources,
                               clients.ceilometer, tenant_id)
            }

            for service_name in self.config:
                try:
                    service = cleanup_methods[service_name]
                    method = service[0]
                    client = service[1]()
                    args = service[2:]
                    method(client, *args)
                except Exception as e:
                    LOG.debug("Not all resources were cleaned.",
                              exc_info=sys.exc_info())
                    LOG.warning(_('Unable to fully cleanup the cloud: %s') %
                                (e.message))

    @rutils.log_task_wrapper(LOG.info, _("Cleanup admin resources."))
    def _cleanup_admin_resources(self):
        try:
            admin = osclients.Clients(self.admin)
            utils.delete_keystone_resources(admin.keystone())
        except Exception as e:
            LOG.debug("Not all resources were cleaned.",
                      exc_info=sys.exc_info())
            LOG.warning(_('Unable to fully cleanup keystone service: %s') %
                        (e.message))

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `cleanup`"))
    def setup(self):
        if "admin" in self.context and self.context["admin"]:
            self.admin = self.context["admin"]["endpoint"]
        if "users" in self.context and self.context["users"]:
            self.users = [u["endpoint"] for u in self.context["users"]]

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `cleanup`"))
    def cleanup(self):
        if self.users and self.config:
            self._cleanup_users_resources()
        if self.admin:
            self._cleanup_admin_resources()
