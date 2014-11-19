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
from rally.benchmark.context.cleanup import manager
from rally import exceptions
from rally.i18n import _
from rally import log as logging
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class NoSuchCleanupResources(exceptions.RallyException):
    msg_fmt = _("Missing cleanup resource managers: %(message)s")


class CleanupMixin(object):

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": rutils.JSON_SCHEMA,
        "items": {
            "type": "string",
        },
        "additionalProperties": False
    }

    def setup(self):
        pass


class AdminCleanup(CleanupMixin, base.Context):
    """Context class for admin resources cleanup."""

    __ctx_hidden__ = True
    __ctx_name__ = "admin_cleanup"
    __ctx_order__ = 200

    @classmethod
    def validate(cls, config, non_hidden=False):
        super(AdminCleanup, cls).validate(config, non_hidden)

        missing = set(config)
        missing -= manager.list_resource_names(admin_required=True)
        missing = ", ".join(missing)
        if missing:
            LOG.info(_("Couldn't find cleanup resource managers: %s")
                     % missing)
            raise NoSuchCleanupResources(missing)

    @rutils.log_task_wrapper(LOG.info, _("admin resources cleanup"))
    def cleanup(self):
        manager.cleanup(names=self.config,
                        admin_required=True,
                        admin=self.context["admin"],
                        users=self.context.get("users", []))


class UserCleanup(CleanupMixin, base.Context):
    """Context class for user resources cleanup."""

    __ctx_hidden__ = True
    __ctx_name__ = "cleanup"
    __ctx_order__ = 201

    @classmethod
    def validate(cls, config, non_hidden=False):
        super(UserCleanup, cls).validate(config, non_hidden)

        missing = set(config)
        missing -= manager.list_resource_names(admin_required=False)
        missing = ", ".join(missing)
        if missing:
            LOG.info(_("Couldn't find cleanup resource managers: %s")
                     % missing)
            raise NoSuchCleanupResources(missing)

    @rutils.log_task_wrapper(LOG.info, _("user resources cleanup"))
    def cleanup(self):
        manager.cleanup(names=self.config,
                        admin_required=False,
                        users=self.context.get("users", []))
