# Copyright 2014: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import requests

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="sahara_edp", order=442)
class SaharaEDP(context.Context):
    """Context class for setting up the environment for an EDP job."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "input_type": {
                "enum": ["swift", "hdfs"],
            },
            "input_url": {
                "type": "string",
            },
            "output_type": {
                "enum": ["swift", "hdfs"],
            },
            "output_url_prefix": {
                "type": "string",
            },
            "mains": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "download_url": {
                            "type": "string"
                        }
                    },
                    "additionalProperties": False,
                    "required": ["name", "download_url"]
                }
            },
            "libs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "download_url": {
                            "type": "string"
                        }
                    },
                    "additionalProperties": False,
                    "required": ["name", "download_url"]
                }
            }
        },
        "additionalProperties": False,
        "required": ["input_type", "input_url",
                     "output_type", "output_url_prefix"]
    }

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Sahara EDP`"))
    def setup(self):
        self.context["sahara_output_conf"] = {
            "output_type": self.config["output_type"],
            "output_url_prefix": self.config["output_url_prefix"]
        }
        self.context["sahara_mains"] = {}
        self.context["sahara_libs"] = {}

        input_type = self.config["input_type"]
        input_url = self.config["input_url"]
        mains = self.config.get("mains", [])
        libs = self.config.get("libs", [])

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            clients = osclients.Clients(user["endpoint"])
            sahara = clients.sahara()

            self.setup_inputs(sahara, tenant_id, input_type, input_url)

            self.context["tenants"][tenant_id]["sahara_mains"] = []
            self.context["tenants"][tenant_id]["sahara_libs"] = []

            for main in mains:
                self.download_and_save_lib(
                    sahara=sahara,
                    lib_type="sahara_mains",
                    name=main["name"],
                    download_url=main["download_url"],
                    tenant_id=tenant_id)

            for lib in libs:
                self.download_and_save_lib(
                    sahara=sahara,
                    lib_type="sahara_libs",
                    name=lib["name"],
                    download_url=lib["download_url"],
                    tenant_id=tenant_id)

    def setup_inputs(self, sahara, tenant_id, input_type, input_url):
        if input_type == "swift":
            raise exceptions.RallyException(
                _("Swift Data Sources are not implemented yet"))
        # Todo(nkonovalov): Add swift credentials parameters and data upload
        input_ds = sahara.data_sources.create(
            name="input_ds",
            description="",
            data_source_type=input_type,
            url=input_url)

        self.context["tenants"][tenant_id]["sahara_input"] = input_ds.id

    def download_and_save_lib(self, sahara, lib_type, name, download_url,
                              tenant_id):
        lib_data = requests.get(download_url).content

        job_binary_internal = sahara.job_binary_internals.create(
            name=name,
            data=lib_data)

        url = "internal-db://%s" % job_binary_internal.id
        job_binary = sahara.job_binaries.create(name=name,
                                                url=url,
                                                description="",
                                                extra={})

        self.context["tenants"][tenant_id][lib_type].append(job_binary.id)

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Sahara EDP`"))
    def cleanup(self):
        resources = ["job_executions", "jobs", "job_binary_internals",
                     "job_binaries", "data_sources"]

        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(
            names=["sahara.%s" % res for res in resources],
            users=self.context.get("users", []))
