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
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.glance import utils as glance_utils
from rally.plugins.openstack.scenarios.sahara import utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="sahara_image", order=440)
class SaharaImage(context.Context):
    """Context class for adding and tagging Sahara images."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image_uuid": {
                "type": "string"
            },
            "image_url": {
                "type": "string",
            },
            "username": {
                "type": "string"
            },
            "plugin_name": {
                "type": "string",
            },
            "hadoop_version": {
                "type": "string",
            }
        },
        "oneOf": [
            {"required": ["image_url", "username", "plugin_name",
                          "hadoop_version"]},
            {"required": ["image_uuid"]}
        ],
        "additionalProperties": False
    }

    def _create_image(self, hadoop_version, image_url, plugin_name, user,
                      user_name):
        scenario = glance_utils.GlanceScenario(
            {"user": user, "task": self.context["task"]})
        image_name = self.generate_random_name()
        image = scenario._create_image(name=image_name,
                                       container_format="bare",
                                       image_location=image_url,
                                       disk_format="qcow2")
        scenario.clients("sahara").images.update_image(
            image_id=image.id, user_name=user_name, desc="")
        scenario.clients("sahara").images.update_tags(
            image_id=image.id, new_tags=[plugin_name, hadoop_version])
        return image.id

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Sahara Image`"))
    def setup(self):
        utils.init_sahara_context(self)
        self.context["sahara"]["images"] = {}

        # The user may want to use the existing image. In this case he should
        # make sure that the image is public and has all required metadata.
        image_uuid = self.config.get("image_uuid")

        self.context["sahara"]["need_image_cleanup"] = not image_uuid

        if image_uuid:
            # Using the first user to check the existing image.
            user = self.context["users"][0]
            clients = osclients.Clients(user["credential"])

            image = clients.glance().images.get(image_uuid)

            visibility = None
            if hasattr(image, "is_public"):
                visibility = "public" if image.is_public else "private"
            else:
                visibility = image["visibility"]

            if visibility != "public":
                raise exceptions.BenchmarkSetupFailure(
                    "Image provided in the Sahara context should be public.")
            image_id = image_uuid

            for user, tenant_id in rutils.iterate_per_tenants(
                    self.context["users"]):
                self.context["tenants"][tenant_id]["sahara"]["image"] = (
                    image_id)
        else:
            for user, tenant_id in rutils.iterate_per_tenants(
                    self.context["users"]):

                image_id = self._create_image(
                    hadoop_version=self.config["hadoop_version"],
                    image_url=self.config["image_url"],
                    plugin_name=self.config["plugin_name"],
                    user=user,
                    user_name=self.config["username"])

                self.context["tenants"][tenant_id]["sahara"]["image"] = (
                    image_id)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Sahara Image`"))
    def cleanup(self):

        # TODO(boris-42): Delete only resources created by this context
        if self.context["sahara"]["need_image_cleanup"]:
            resource_manager.cleanup(names=["glance.images"],
                                     users=self.context.get("users", []))
