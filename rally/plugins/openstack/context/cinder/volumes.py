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
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.task import context
from rally.task import scenario


LOG = logging.getLogger(__name__)


@context.configure(name="volumes", order=420)
class VolumeGenerator(context.Context):
    """Context class for adding volumes to each user for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "size": {
                "type": "integer",
                "minimum": 1
            },
            "volumes_per_tenant": {
                "type": "integer",
                "minimum": 1
            }
        },
        "required": ["size"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "volumes_per_tenant": 1
    }

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Volumes`"))
    def setup(self):
        size = self.config["size"]
        volumes_per_tenant = self.config["volumes_per_tenant"]

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id].setdefault("volumes", [])
            cinder_util = cinder_utils.CinderScenario({"user": user})
            for i in range(volumes_per_tenant):
                rnd_name = scenario.Scenario._generate_random_name(
                    prefix="ctx_rally_volume_")
                vol = cinder_util._create_volume(size, display_name=rnd_name)
                self.context["tenants"][tenant_id]["volumes"].append(vol._info)

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Volumes`"))
    def cleanup(self):
        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(names=["cinder.volumes"],
                                 users=self.context.get("users", []))
