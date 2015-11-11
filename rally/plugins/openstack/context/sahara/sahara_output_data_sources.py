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
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id]["sahara_output_conf"] = {
                "output_type": self.config["output_type"],
                "output_url_prefix": self.config["output_url_prefix"]}

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Sahara Output Data"
                                          "Sources`"))
    def cleanup(self):
        # TODO(esikachev): Cleanup must iterate by output_url_prefix of
        # resources from setup() and delete them
        pass
