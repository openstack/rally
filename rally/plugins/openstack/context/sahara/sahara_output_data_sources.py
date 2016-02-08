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
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally import osclients
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.cleanup import resources as res_cleanup
from rally.plugins.openstack.scenarios.sahara import utils
from rally.plugins.openstack.scenarios.swift import utils as swift_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="sahara_output_data_sources", order=444)
class SaharaOutputDataSources(context.Context):
    """Context class for setting up Output Data Sources for an EDP job."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "output_type": {
                "enum": ["swift", "hdfs"],
            },
            "output_url_prefix": {
                "type": "string",
            }
        },
        "additionalProperties": False,
        "required": ["output_type", "output_url_prefix"]
    }

    @logging.log_task_wrapper(LOG.info,
                              _("Enter context: `Sahara Output Data Sources`"))
    def setup(self):
        utils.init_sahara_context(self)
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            clients = osclients.Clients(user["credential"])
            sahara = clients.sahara()

            if self.config["output_type"] == "swift":
                swift = swift_utils.SwiftScenario(clients=clients,
                                                  context=self.context)
                container_name = self.generate_random_name()
                self.context["tenants"][tenant_id]["sahara"]["container"] = {
                    "name": swift._create_container(
                        container_name=container_name),
                    "output_swift_objects": []
                }
                self.setup_outputs_swift(swift, sahara, tenant_id,
                                         container_name,
                                         user["credential"].username,
                                         user["credential"].password)
            else:
                self.setup_outputs_hdfs(sahara, tenant_id,
                                        self.config["output_url_prefix"])

    def setup_outputs_hdfs(self, sahara, tenant_id, output_url):
        output_ds = sahara.data_sources.create(
            name=self.generate_random_name(),
            description="",
            data_source_type="hdfs",
            url=output_url)

        self.context["tenants"][tenant_id]["sahara"]["output"] = output_ds.id

    def setup_outputs_swift(self, swift, sahara, tenant_id, container_name,
                            username, password):
        output_ds_swift = sahara.data_sources.create(
            name=self.generate_random_name(),
            description="",
            data_source_type="swift",
            url="swift://" + container_name + ".sahara/",
            credential_user=username,
            credential_pass=password)

        self.context["tenants"][tenant_id]["sahara"]["output"] = (
            output_ds_swift.id
        )

    @logging.log_task_wrapper(LOG.info,
                              _("Exit context: `Sahara Output Data Sources`"))
    def cleanup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            if self.context["tenants"][tenant_id].get(
                    "sahara", {}).get("container", {}).get("name") is not None:
                for swift_object in (
                    self.context["tenants"][tenant_id]["sahara"]["container"][
                        "output_swift_objects"]):
                    res_cleanup.SwiftObject(swift_object[1])
            res_cleanup.SwiftContainer(
                self.context["tenants"][tenant_id].get(
                    "sahara", {}).get("container", {}).get("name"))
        resources = ["data_sources"]
        resource_manager.cleanup(
            names=["sahara.%s" % res for res in resources],
            users=self.context.get("users", []))
