# Copyright 2015: Mirantis Inc.
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

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.task import context

LOG = logging.getLogger(__name__)


@context.configure(name="sahara_data_sources", order=443)
class SaharaDataSources(context.Context):
    """Context class for setting up Data Sources for an EDP job."""

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
            }
        },
        "additionalProperties": False,
        "required": ["input_type", "input_url",
                     "output_type", "output_url_prefix"]
    }

    @rutils.log_task_wrapper(LOG.info,
                             _("Enter context: `Sahara Data Sources`"))
    def setup(self):
        self.context["sahara_output_conf"] = {
            "output_type": self.config["output_type"],
            "output_url_prefix": self.config["output_url_prefix"]
        }
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            clients = osclients.Clients(user["endpoint"])
            sahara = clients.sahara()

            self.setup_inputs(sahara, tenant_id, self.config["input_type"],
                              self.config["input_url"])

    def setup_inputs(self, sahara, tenant_id, input_type, input_url):
        if input_type == "swift":
            raise exceptions.RallyException(
                _("Swift Data Sources are not implemented yet"))
        # Todo(nkonovalov): Add swift credentials parameters and data upload
        input_ds = sahara.data_sources.create(
            name=self.generate_random_name(),
            description="",
            data_source_type=input_type,
            url=input_url)

        self.context["tenants"][tenant_id]["sahara_input"] = input_ds.id

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Sahara EDP`"))
    def cleanup(self):
        resources = ["job_executions", "jobs", "data_sources"]

        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(
            names=["sahara.%s" % res for res in resources],
            users=self.context.get("users", []))
