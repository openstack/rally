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
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.services.image import image
from rally.task import context

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
            "disk_format": {
                "enum": ["qcow2", "raw", "vhd", "vmdk", "vdi", "iso", "aki",
                         "ari", "ami"]
            },
            "image_container": {
                "type": "string",
            },
            "container_format": {
                "enum": ["aki", "ami", "ari", "bare", "docker", "ova", "ovf"]
            },
            "image_name": {
                "type": "string",
            },
            "min_ram": {
                "description": "Amount of RAM in MB",
                "type": "integer",
                "minimum": 0
            },
            "min_disk": {
                "description": "Amount of disk space in GB",
                "type": "integer",
                "minimum": 0
            },
            "visibility": {
                "enum": ["public", "private", "shared", "community"]
            },
            "images_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "image_args": {
                "description": "This param is deprecated from Rally-0.10.0",
                "type": "object",
                "additionalProperties": True
            }
        },
        "oneOf": [{"description": "It is been used since Rally 0.10.0",
                   "required": ["image_url", "disk_format",
                                "container_format", "images_per_tenant"]},
                  {"description": "One of backward compatible way",
                   "required": ["image_url", "image_type",
                                "container_format", "images_per_tenant"]},
                  {"description": "One of backward compatible way",
                   "required": ["image_url", "disk_format",
                                "image_container", "images_per_tenant"]},
                  {"description": "One of backward compatible way",
                   "required": ["image_url", "image_type",
                                "image_container", "images_per_tenant"]}],
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Images`"))
    def setup(self):
        image_url = self.config.get("image_url")
        image_type = self.config.get("image_type")
        disk_format = self.config.get("disk_format")
        image_container = self.config.get("image_container")
        container_format = self.config.get("container_format")
        images_per_tenant = self.config.get("images_per_tenant")
        image_name = self.config.get("image_name")
        visibility = self.config.get("visibility", "private")
        min_disk = self.config.get("min_disk", 0)
        min_ram = self.config.get("min_ram", 0)
        image_args = self.config.get("image_args", {})
        is_public = image_args.get("is_public")

        if is_public:
            LOG.warning(_("The 'is_public' argument is deprecated "
                          "since Rally 0.10.0; specify visibility "
                          "arguments instead"))
            if "visibility" not in self.config:
                visibility = "public" if is_public else "private"

        if image_type:
            LOG.warning(_("The 'image_type' argument is deprecated "
                          "since Rally 0.10.0; specify disk_format "
                          "arguments instead"))
            disk_format = image_type

        if image_container:
            LOG.warning(_("The 'image_container' argument is deprecated "
                          "since Rally 0.10.0; specify container_format "
                          "arguments instead"))
            container_format = image_container

        if image_args:
            LOG.warning(_("The 'kwargs' argument is deprecated since "
                          "Rally 0.10.0; specify exact arguments instead"))

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            current_images = []
            clients = osclients.Clients(
                user["credential"],
                api_info=self.context["config"].get("api_versions"))
            image_service = image.Image(
                clients,
                name_generator=self.generate_random_name)

            for i in range(images_per_tenant):
                if image_name and i > 0:
                    cur_name = image_name + str(i)
                elif image_name:
                    cur_name = image_name
                else:
                    cur_name = self.generate_random_name()

                image_obj = image_service.create_image(
                    image_name=cur_name,
                    container_format=container_format,
                    image_location=image_url,
                    disk_format=disk_format,
                    visibility=visibility,
                    min_disk=min_disk,
                    min_ram=min_ram)
                current_images.append(image_obj.id)

            self.context["tenants"][tenant_id]["images"] = current_images

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Images`"))
    def cleanup(self):
        resource_manager.cleanup(names=["glance.images"],
                                 users=self.context.get("users", []),
                                 api_versions=self.context["config"].get(
                                     "api_versions"),
                                 superclass=self.__class__,
                                 task_id=self.context["task"]["uuid"])
