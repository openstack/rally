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

import sys

import six

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import utils
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class UserCleanup(base.Context):
    """Context class for user resource cleanup."""

    __ctx_name__ = "cleanup"
    __ctx_order__ = 201
    __ctx_hidden__ = True

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": rutils.JSON_SCHEMA,
        "items": {
            "type": "string",
            "enum": ["nova", "glance", "cinder",
                     "neutron", "ceilometer", "heat", "sahara"]
        },
        "uniqueItems": True
    }

    def __init__(self, context):
        super(UserCleanup, self).__init__(context)
        self.users_endpoints = []

    def _cleanup_resources(self):
        for user in self.users_endpoints:
            clients = osclients.Clients(user)
            tenant_id = clients.keystone().tenant_id
            cleanup_methods = {
                "nova": (utils.delete_nova_resources, clients.nova),
                "glance": (utils.delete_glance_resources, clients.glance,
                           tenant_id),
                "cinder": (utils.delete_cinder_resources, clients.cinder),
                "neutron": (utils.delete_neutron_resources, clients.neutron,
                            tenant_id),
                "ceilometer": (utils.delete_ceilometer_resources,
                               clients.ceilometer, tenant_id),
                "heat": (utils.delete_heat_resources, clients.heat),
                "sahara": (utils.delete_sahara_resources, clients.sahara)
            }

            for service_name in self.config:
                cleanup_method = cleanup_methods[service_name]
                method = cleanup_method[0]
                client = cleanup_method[1]()
                try:
                    method(client, *cleanup_method[2:])
                except Exception as e:
                    LOG.debug("Not all user resources were cleaned.",
                              exc_info=sys.exc_info())
                    LOG.warning(_('Unable to fully cleanup the cloud: %s') %
                                (six.text_type(e)))

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `cleanup`"))
    def setup(self):
        self.users_endpoints = [u["endpoint"]
                                for u in self.context.get("users", [])]

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `cleanup`"))
    def cleanup(self):
        if self.users_endpoints and self.config:
            self._cleanup_resources()
