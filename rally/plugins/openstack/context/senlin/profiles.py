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

from rally.common import utils as rutils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.scenarios.senlin import utils as senlin_utils
from rally.task import context


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="profiles", platform="openstack", order=190)
class ProfilesGenerator(context.Context):
    """Context creates a temporary profile for Senlin test."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string",
            },
            "version": {
                "type": "string",
            },
            "properties": {
                "type": "object",
                "additionalProperties": True,
            }
        },
        "additionalProperties": False,
        "required": ["type", "version", "properties"]
    }

    def setup(self):
        """Create test profiles."""
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            senlin_scenario = senlin_utils.SenlinScenario({
                "user": user,
                "task": self.context["task"],
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            profile = senlin_scenario._create_profile(self.config)

            self.context["tenants"][tenant_id]["profile"] = profile.id

    def cleanup(self):
        """Delete created test profiles."""
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            senlin_scenario = senlin_utils.SenlinScenario({
                "user": user,
                "task": self.context["task"],
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            senlin_scenario._delete_profile(
                self.context["tenants"][tenant_id]["profile"])
