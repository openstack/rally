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

import urllib2

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import utils as cleanup_utils
from rally import exceptions
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class SaharaEDP(base.Context):
    """Context class for setting up the environment for an EDP job."""

    __ctx_name__ = "sahara_edp"
    __ctx_order__ = 414
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
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

    def __init__(self, context):
        super(SaharaEDP, self).__init__(context)
        self.context["sahara_inputs"] = {}
        self.context["sahara_output_conf"] = {
            "output_type": self.config["output_type"],
            "output_url_prefix": self.config["output_url_prefix"]
        }
        self.context["sahara_mains"] = {}
        self.context["sahara_libs"] = {}

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Sahara EDP`"))
    def setup(self):

        input_type = self.config["input_type"]
        input_url = self.config["input_url"]
        mains = self.config.get("mains", [])
        libs = self.config.get("libs", [])

        ready_tenants = set()

        for user in self.context.get("users", []):
            tenant_id = user["tenant_id"]
            if tenant_id not in ready_tenants:
                ready_tenants.add(tenant_id)

                clients = osclients.Clients(user["endpoint"])
                sahara = clients.sahara()

                self.setup_inputs(sahara, tenant_id, input_type, input_url)

                self.context["sahara_mains"][tenant_id] = []
                self.context["sahara_libs"][tenant_id] = []

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

        self.context["sahara_inputs"][tenant_id] = input_ds.id

    def download_and_save_lib(self, sahara, lib_type, name, download_url,
                              tenant_id):
        lib_data = urllib2.urlopen(download_url).read()

        job_binary_internal = sahara.job_binary_internals.create(
            name=name,
            data=lib_data)

        url = "internal-db://%s" % job_binary_internal.id
        job_binary = sahara.job_binaries.create(name=name,
                                                url=url,
                                                description="",
                                                extra={})

        self.context[lib_type][tenant_id].append(job_binary.id)

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Sahara EDP`"))
    def cleanup(self):
        clean_tenants = set()
        for user in self.context.get("users", []):
            tenant_id = user["tenant_id"]
            if tenant_id not in clean_tenants:
                clean_tenants.add(tenant_id)

                sahara = osclients.Clients(user["endpoint"]).sahara()

                cleanup_utils.delete_job_executions(sahara)
                cleanup_utils.delete_jobs(sahara)
                cleanup_utils.delete_job_binary_internals(sahara)
                cleanup_utils.delete_job_binaries(sahara)
                cleanup_utils.delete_data_sources(sahara)
