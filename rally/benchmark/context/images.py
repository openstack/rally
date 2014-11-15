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

import six

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import manager as resource_manager
from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark.scenarios.glance import utils as glance_utils
from rally import exceptions
from rally.i18n import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class ImageGenerator(base.Context):
    """Context class for adding images to each user for benchmarks."""

    __ctx_name__ = "images"
    __ctx_order__ = 411
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
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
            "images_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
        },
        'required': ['image_url', 'image_type', 'image_container',
                     'images_per_tenant'],
        "additionalProperties": False
    }

    def __init__(self, context):
        super(ImageGenerator, self).__init__(context)
        self.context.setdefault("images", [])

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Images`"))
    def setup(self):
        image_url = self.config["image_url"]
        image_type = self.config["image_type"]
        image_container = self.config["image_container"]
        images_per_tenant = self.config["images_per_tenant"]
        current_tenants = []

        for user in self.context["users"]:
            if user["tenant_id"] not in current_tenants:
                current_tenants.append(user["tenant_id"])
                current_images = []

                clients = osclients.Clients(user["endpoint"])
                glance_util_class = glance_utils.GlanceScenario(
                                        clients=clients)
                for i in range(images_per_tenant):
                    rnd_name = scenario_base.Scenario._generate_random_name()

                    image = glance_util_class._create_image(rnd_name,
                                                            image_container,
                                                            image_url,
                                                            image_type)
                    current_images.append(image.id)

                self.context["images"].append({"image_id": current_images,
                                               "endpoint": user["endpoint"],
                                               "tenant_id": user["tenant_id"]})

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Images`"))
    def cleanup(self):
        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(names=["glance.images"],
                                 users=self.context.get("users", []))

    @classmethod
    def validate_semantic(cls, config, admin, users, task):
        """Check if the image service is available."""
        try:
            glance = users[0].glance()
            list(glance.images.list(limit=0))
        except Exception as e:
            message = _(
                "The image service is unavailable, Reason: %(reason)s") % {
                      "reason": six.text_type(e)}
            raise exceptions.InvalidScenarioArgument(message)
