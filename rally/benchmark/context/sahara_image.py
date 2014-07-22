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

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import utils as cleanup_utils
from rally.benchmark.scenarios import base as scenarios_base
from rally.benchmark.scenarios.glance import utils as glance_utils
from rally import exceptions
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class SaharaImage(base.Context):
    """Context class for adding and tagging Sahara images."""

    __ctx_name__ = "sahara_image"
    __ctx_order__ = 412
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
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
            },
        },
        "additionalProperties": False,
        "required": ["image_url", "username", "plugin_name", "hadoop_version"]
    }

    def __init__(self, context):
        super(SaharaImage, self).__init__(context)
        self.context["sahara_images"] = {}

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Sahara Image`"))
    def setup(self):
        image_url = self.config["image_url"]
        plugin_name = self.config["plugin_name"]
        hadoop_version = self.config["hadoop_version"]
        user_name = self.config["username"]

        for user in self.context.get("users", []):
            tenant_id = user["tenant_id"]
            if tenant_id not in self.context["sahara_images"]:

                clients = osclients.Clients(user["endpoint"])
                glance_util_class = glance_utils.GlanceScenario(
                    clients=clients)

                image_name = scenarios_base.Scenario._generate_random_name(
                    prefix="sahara_image_", length=15)
                image = glance_util_class._create_image(image_name,
                                                        "bare",
                                                        image_url,
                                                        "qcow2")

                clients.sahara().images.update_image(image_id=image.id,
                                                     user_name=user_name,
                                                     desc="")

                clients.sahara().images.update_tags(image_id=image.id,
                                                    new_tags=[plugin_name,
                                                              hadoop_version])

                self.context["sahara_images"][tenant_id] = image.id

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Sahara Image`"))
    def cleanup(self):
        clean_tenants = set([])
        for user in self.context.get("users", []):
            tenant_id = user["tenant_id"]
            if tenant_id not in clean_tenants:
                clean_tenants.add(tenant_id)

                try:
                    glance = osclients.Clients(user["endpoint"]).glance()
                    cleanup_utils.delete_glance_resources(glance,
                                                          user["tenant_id"])
                except Exception as e:
                    LOG.error(e)
                    raise exceptions.ImageCleanUpException()
