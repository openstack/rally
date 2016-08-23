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
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.task import context


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
            "type": {
                "type": ["string", "null"]
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

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Volumes`"))
    def setup(self):
        size = self.config["size"]
        volume_type = self.config.get("type", None)
        volumes_per_tenant = self.config["volumes_per_tenant"]

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id].setdefault("volumes", [])
            cinder_util = cinder_utils.CinderScenario(
                {"user": user,
                 "task": self.context["task"],
                 "config": self.context["config"]})
            for i in range(volumes_per_tenant):
                vol = cinder_util._create_volume(size, volume_type=volume_type)
                self.context["tenants"][tenant_id]["volumes"].append(vol._info)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Volumes`"))
    def cleanup(self):
        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(
            names=["cinder.volumes"],
            users=self.context.get("users", []),
            api_versions=self.context["config"].get("api_versions"))
