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
from rally.plugins.openstack.scenarios.glance import utils as glance_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="images", order=410)
class ImageGenerator(context.Context):
    """Context class for adding images to each user for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image_url": {
                "type": "string",
            },
            "image_type": {
                "enum": ["qcow2", "raw", "vhd", "vmdk", "vdi", "iso", "aki",
                         "ari", "ami"],
            },
            "image_container": {
                "type": "string",
            },
            "image_name": {
                "type": "string",
            },
            "min_ram": {  # megabytes
                "type": "integer",
                "minimum": 0
            },
            "min_disk": {  # gigabytes
                "type": "integer",
                "minimum": 0
            },
            "images_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
        },
        "required": ["image_url", "image_type", "image_container",
                     "images_per_tenant"],
        "additionalProperties": False
    }

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Images`"))
    def setup(self):
        image_url = self.config["image_url"]
        image_type = self.config["image_type"]
        image_container = self.config["image_container"]
        images_per_tenant = self.config["images_per_tenant"]
        image_name = self.config.get("image_name")

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            current_images = []
            glance_scenario = glance_utils.GlanceScenario({"user": user})
            for i in range(images_per_tenant):
                if image_name and i > 0:
                    cur_name = image_name + str(i)
                elif image_name:
                    cur_name = image_name
                else:
                    cur_name = None

                image = glance_scenario._create_image(
                    image_container, image_url, image_type,
                    name=cur_name, prefix="rally_ctx_image_",
                    min_ram=self.config.get("min_ram", 0),
                    min_disk=self.config.get("min_disk", 0))
                current_images.append(image.id)

            self.context["tenants"][tenant_id]["images"] = current_images

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Images`"))
    def cleanup(self):
        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(names=["glance.images"],
                                 users=self.context.get("users", []))
