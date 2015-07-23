# Copyright 2015: Mirantis Inc.
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

import zipfile

from rally.common.i18n import _
from rally.common.i18n import _LE
from rally.common import log as logging
from rally.common import utils
from rally import consts
from rally import osclients
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="murano_packages", order=401)
class PackageGenerator(context.Context):
    """Context class for uploading applications for murano."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "app_package": {
                "type": "string",
            }
        },
        "required": ["app_package"],
        "additionalProperties": False
    }

    @utils.log_task_wrapper(LOG.info, _("Enter context: `Murano packages`"))
    def setup(self):
        if not zipfile.is_zipfile(self.config["app_package"]):
            msg = (_LE("There is no zip archive by this path: %s")
                   % self.config["app_package"])
            raise OSError(msg)

        for user, tenant_id in utils.iterate_per_tenants(
                self.context["users"]):
            clients = osclients.Clients(user["endpoint"])
            self.context["tenants"][tenant_id]["packages"] = []
            package = clients.murano().packages.create(
                {"categories": ["Web"], "tags": ["tag"]},
                {"file": open(self.config["app_package"])})

            self.context["tenants"][tenant_id]["packages"].append(package)

    @utils.log_task_wrapper(LOG.info, _("Exit context: `Murano packages`"))
    def cleanup(self):
        resource_manager.cleanup(names=["murano.packages"],
                                 users=self.context.get("users", []))
