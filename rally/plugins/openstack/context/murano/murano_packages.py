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

import os
import zipfile

from rally.common import fileutils
from rally.common.i18n import _
from rally.common.i18n import _LE
from rally.common import logging
from rally.common import utils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.cleanup import manager as resource_manager
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

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Murano packages`"))
    def setup(self):
        is_config_app_dir = False
        pckg_path = os.path.expanduser(self.config["app_package"])
        if zipfile.is_zipfile(pckg_path):
            zip_name = pckg_path
        elif os.path.isdir(pckg_path):
            is_config_app_dir = True
            zip_name = fileutils.pack_dir(pckg_path)
        else:
            msg = (_LE("There is no zip archive or directory by this path:"
                       " %s") % pckg_path)
            raise exceptions.ContextSetupFailure(msg=msg,
                                                 ctx_name=self.get_name())

        for user, tenant_id in utils.iterate_per_tenants(
                self.context["users"]):
            clients = osclients.Clients(user["credential"])
            self.context["tenants"][tenant_id]["packages"] = []
            if is_config_app_dir:
                self.context["tenants"][tenant_id]["murano_ctx"] = zip_name
            package = clients.murano().packages.create(
                {"categories": ["Web"], "tags": ["tag"]},
                {"file": open(zip_name)})

            self.context["tenants"][tenant_id]["packages"].append(package)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Murano packages`"))
    def cleanup(self):
        resource_manager.cleanup(names=["murano.packages"],
                                 users=self.context.get("users", []))
