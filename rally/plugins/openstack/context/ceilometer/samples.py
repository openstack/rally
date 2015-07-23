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
from rally.plugins.openstack.scenarios.ceilometer import utils as ceilo_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="ceilometer", order=450)
class CeilometerSampleGenerator(context.Context):
    """Context for creating samples and collecting resources for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "counter_name": {
                "type": "string"
            },
            "counter_type": {
                "type": "string"
            },
            "counter_unit": {
                "type": "string"
            },
            "counter_volume": {
                "type": "number",
                "minimum": 0
            },
            "resources_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "samples_per_resource": {
                "type": "integer",
                "minimum": 1
            },
        },
        "required": ["counter_name", "counter_type", "counter_unit",
                     "counter_volume"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "resources_per_tenant": 5,
        "samples_per_resource": 5
    }

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Ceilometer`"))
    def setup(self):
        counter_name = self.config["counter_name"]
        counter_type = self.config["counter_type"]
        counter_unit = self.config["counter_unit"]
        counter_volume = self.config["counter_volume"]
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id]["samples"] = []
            self.context["tenants"][tenant_id]["resources"] = []
            scenario = ceilo_utils.CeilometerScenario({"user": user})
            for i in range(self.config["resources_per_tenant"]):
                for j in range(self.config["samples_per_resource"]):
                    sample = scenario._create_sample(counter_name,
                                                     counter_type,
                                                     counter_unit,
                                                     counter_volume)
                    self.context["tenants"][tenant_id]["samples"].append(
                        sample[0].to_dict())

                self.context["tenants"][tenant_id]["resources"].append(
                    sample[0].resource_id)

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Ceilometer`"))
    def cleanup(self):
        # We don't have API for removal of samples and resources
        pass
