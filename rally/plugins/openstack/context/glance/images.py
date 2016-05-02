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

from oslo_config import cfg

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally import osclients
from rally.plugins.openstack.wrappers import glance as glance_wrapper
from rally.task import context
from rally.task import utils

CONF = cfg.CONF
CONF.import_opt("glance_image_delete_timeout",
                "rally.plugins.openstack.scenarios.glance.utils",
                "benchmark")
CONF.import_opt("glance_image_delete_poll_interval",
                "rally.plugins.openstack.scenarios.glance.utils",
                "benchmark")

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
            "image_args": {
                "type": "object",
                "additionalProperties": True
            }
        },
        "required": ["image_url", "image_type", "image_container",
                     "images_per_tenant"],
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Images`"))
    def setup(self):
        image_url = self.config["image_url"]
        image_type = self.config["image_type"]
        image_container = self.config["image_container"]
        images_per_tenant = self.config["images_per_tenant"]
        image_name = self.config.get("image_name")

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            current_images = []
            clients = osclients.Clients(
                user["credential"],
                api_info=self.context["config"].get("api_versions"))
            glance_wrap = glance_wrapper.wrap(clients.glance, self)

            kwargs = self.config.get("image_args", {})
            if self.config.get("min_ram") is not None:
                LOG.warning("The 'min_ram' argument is deprecated; specify "
                            "arbitrary arguments with 'image_args' instead")
                kwargs["min_ram"] = self.config["min_ram"]
            if self.config.get("min_disk") is not None:
                LOG.warning("The 'min_disk' argument is deprecated; specify "
                            "arbitrary arguments with 'image_args' instead")
                kwargs["min_disk"] = self.config["min_disk"]

            for i in range(images_per_tenant):
                if image_name and i > 0:
                    cur_name = image_name + str(i)
                elif image_name:
                    cur_name = image_name
                else:
                    cur_name = self.generate_random_name()

                image = glance_wrap.create_image(
                    image_container, image_url, image_type,
                    name=cur_name, **kwargs)
                current_images.append(image.id)

            self.context["tenants"][tenant_id]["images"] = current_images

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Images`"))
    def cleanup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            clients = osclients.Clients(
                user["credential"],
                api_info=self.context["config"].get("api_versions"))
            glance_wrap = glance_wrapper.wrap(clients.glance, self)
            for image in self.context["tenants"][tenant_id].get("images", []):
                clients.glance().images.delete(image)
                utils.wait_for_status(
                    clients.glance().images.get(image),
                    ["deleted", "pending_delete"],
                    check_deletion=True,
                    update_resource=glance_wrap.get_image,
                    timeout=CONF.benchmark.glance_image_delete_timeout,
                    check_interval=CONF.benchmark.
                    glance_image_delete_poll_interval)
