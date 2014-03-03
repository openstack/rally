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
import itertools
import sys

from rally.benchmark.context import base
from rally.benchmark import utils
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class ResourceCleaner(base.Context):
    """Context class for resource cleanup (both admin and non-admin)."""

    __name__ = "cleaner"

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": "http://json-schema.org/draft-03/schema",
        "properties": {},
        "additionalProperties": False
    }

    def __init__(self, context):
        super(ResourceCleaner, self).__init__(context)
        self.admin = None
        self.users = None
        if "admin" in context and context["admin"]:
            self.admin = context["admin"]["endpoint"]
        if "users" in context and context["users"]:
            self.users = [u["endpoint"] for u in context["users"]]

    @rutils.log_task_wrapper(LOG.info, _("Cleanup users resources."))
    def _cleanup_users_resources(self):
        if not self.users:
            return

        for user in itertools.imap(utils.create_openstack_clients, self.users):
            methods = [
                functools.partial(utils.delete_nova_resources, user["nova"]),
                functools.partial(utils.delete_glance_resources,
                                  user["glance"], user["keystone"]),
                functools.partial(utils.delete_cinder_resources,
                                  user["cinder"])
            ]

            for method in methods:
                try:
                    method()
                except Exception as e:
                    LOG.debug(_("Not all resources were cleaned."),
                              exc_info=sys.exc_info())
                    LOG.warning(_('Unable to fully cleanup the cloud: \n%s') %
                                (e.message))

    @rutils.log_task_wrapper(LOG.info, _("Cleanup admin resources."))
    def _cleanup_admin_resources(self):
        if not self.admin:
            return

        try:
            admin = utils.create_openstack_clients(self.admin)
            utils.delete_keystone_resources(admin["keystone"])
        except Exception as e:
            LOG.debug(_("Not all resources were cleaned."),
                      exc_info=sys.exc_info())
            LOG.warning(_('Unable to fully cleanup keystone service: %s') %
                        (e.message))

    def setup(self):
        pass

    def cleanup(self):
        if self.users:
            self._cleanup_users_resources()
        if self.admin:
            self._cleanup_admin_resources()
