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


class AdminCleanup(base.Context):
    """Context class for admin resource cleanup."""

    __ctx_name__ = "admin_cleanup"
    __ctx_order__ = 200
    __ctx_hidden__ = True

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": rutils.JSON_SCHEMA,
        "items": {
            "type": "string",
            "enum": ["keystone", "quotas"]
        },
        "uniqueItems": True
    }

    def __init__(self, context):
        super(AdminCleanup, self).__init__(context)
        self.endpoint = None

    def _cleanup_resources(self):
        client = osclients.Clients(self.endpoint)

        cleanup_methods = {
            "keystone": (utils.delete_keystone_resources, client.keystone()),
            "quotas": (utils.delete_admin_quotas, client,
                       self.context.get("tenants", [])),
        }

        for service_name in self.config:
            cleanup_method = cleanup_methods[service_name]
            method, client = cleanup_method[:2]
            try:
                method(client, *cleanup_method[2:])
            except Exception as e:
                LOG.debug("Not all admin resources were cleaned.",
                          exc_info=sys.exc_info())
                LOG.warning(_('Unable to fully cleanup the cloud: %s') %
                            (six.text_type(e)))

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `admin cleanup`"))
    def setup(self):
        self.endpoint = self.context["admin"]["endpoint"]

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `admin cleanup`"))
    def cleanup(self):
        self._cleanup_resources()
