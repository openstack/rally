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

from rally.common.i18n import _
from rally.common import logging
from rally.plugins.openstack.cleanup import manager
from rally.plugins.openstack.context.cleanup import base
from rally.task import context


LOG = logging.getLogger(__name__)


# NOTE(amaretskiy): Set order to run this just before UserCleanup
@context.configure(name="admin_cleanup", order=(sys.maxsize - 1), hidden=True)
class AdminCleanup(base.CleanupMixin, context.Context):
    """Context class for admin resources cleanup."""

    @classmethod
    def validate(cls, config, non_hidden=False):
        super(AdminCleanup, cls).validate(config, non_hidden)

        missing = set(config)
        missing -= manager.list_resource_names(admin_required=True)
        missing = ", ".join(missing)
        if missing:
            LOG.info(_("Couldn't find cleanup resource managers: %s")
                     % missing)
            raise base.NoSuchCleanupResources(missing)

    @logging.log_task_wrapper(LOG.info, _("admin resources cleanup"))
    def cleanup(self):
        manager.cleanup(
            names=self.config,
            admin_required=True,
            admin=self.context["admin"],
            users=self.context.get("users", []),
            api_versions=self.context["config"].get("api_versions"))
