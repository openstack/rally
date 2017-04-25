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
from rally.common import validation
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


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="images", order=410)
class ImageGenerator(context.Context):
    """Context class for adding images to each user for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image_url": {
                "type": "string",
                "description": "Location of the source to create image from."
            },
            "disk_format": {
                "description": "The format of the disk.",
                "enum": ["qcow2", "raw", "vhd", "vmdk", "vdi", "iso", "aki",
                         "ari", "ami"]
            },
            "container_format": {
                "description": "Format of the image container.",
                "enum": ["aki", "ami", "ari", "bare", "docker", "ova", "ovf"]
            },
            "image_name": {
                "type": "string",
                "description": "The name of image to create. NOTE: it will be "
                               "ignored in case when `images_per_tenant` is "
                               "bigger then 1."
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
                "description": "Visibility for this image ('shared' and "
                               "'community' are available only in case of "
                               "Glance V2).",
                "enum": ["public", "private", "shared", "community"]
            },
            "images_per_tenant": {
                "description": "The number of images to create per one single "
                               "tenant.",
                "type": "integer",
                "minimum": 1
            },
            "image_args": {
                "description": "This param is deprecated since Rally-0.10.0, "
                               "specify exact arguments in a root section of "
                               "context instead.",
                "type": "object",
                "additionalProperties": True
            },
            "image_container": {
                "description": "This param is deprecated since Rally-0.10.0, "
                               "use `container_format` instead.",
                "type": "string",
            },
            "image_type": {
                "description": "This param is deprecated since Rally-0.10.0, "
                               "use `disk_format` instead.",
                "enum": ["qcow2", "raw", "vhd", "vmdk", "vdi", "iso", "aki",
                         "ari", "ami"],
            },
        },
        "oneOf": [{"description": "It is been used since Rally 0.10.0",
                   "required": ["image_url", "disk_format",
                                "container_format"]},
                  {"description": "One of backward compatible way",
                   "required": ["image_url", "image_type",
                                "container_format"]},
                  {"description": "One of backward compatible way",
                   "required": ["image_url", "disk_format",
                                "image_container"]},
                  {"description": "One of backward compatible way",
                   "required": ["image_url", "image_type",
                                "image_container"]}],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {"images_per_tenant": 1}

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Images`"))
    def setup(self):
        image_url = self.config.get("image_url")
        disk_format = self.config.get("disk_format")
        container_format = self.config.get("container_format")
        images_per_tenant = self.config.get("images_per_tenant")
        visibility = self.config.get("visibility", "private")
        min_disk = self.config.get("min_disk", 0)
        min_ram = self.config.get("min_ram", 0)
        image_args = self.config.get("image_args", {})

        if "image_type" in self.config:
            LOG.warning(_("The 'image_type' argument is deprecated "
                          "since Rally 0.10.0, use disk_format "
                          "arguments instead."))
            if not disk_format:
                disk_format = self.config["image_type"]

        if "image_container" in self.config:
            LOG.warning(_("The 'image_container' argument is deprecated "
                          "since Rally 0.10.0; use container_format "
                          "arguments instead"))
            if not container_format:
                container_format = self.config["image_container"]

        if image_args:
            LOG.warning(_("The 'image_args' argument is deprecated since "
                          "Rally 0.10.0; specify exact arguments in a root "
                          "section of context instead."))

            if "is_public" in image_args:
                if "visibility" not in self.config:
                    visibility = ("public" if image_args["is_public"]
                                  else "private")
            if "min_ram" in image_args:
                if "min_ram" not in self.config:
                    min_ram = image_args["min_ram"]

            if "min_disk" in image_args:
                if "min_disk" not in self.config:
                    min_disk = image_args["min_disk"]

        # None image_name means that image.Image will generate a random name
        image_name = None
        if "image_name" in self.config and images_per_tenant == 1:
            image_name = self.config["image_name"]

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            current_images = []
            clients = osclients.Clients(
                user["credential"],
                api_info=self.context["config"].get("api_versions"))
            image_service = image.Image(
                clients, name_generator=self.generate_random_name)

            for i in range(images_per_tenant):
                image_obj = image_service.create_image(
                    image_name=image_name,
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
        if self.context.get("admin", {}):
            admin = self.context["admin"]
            admin_required = None
        else:
            admin = None
            admin_required = False

        if "image_name" in self.config:
            matcher = rutils.make_name_matcher(self.config["image_name"])
        else:
            matcher = self.__class__

        resource_manager.cleanup(names=["glance.images",
                                        "cinder.image_volumes_cache"],
                                 admin=admin,
                                 admin_required=admin_required,
                                 users=self.context.get("users", []),
                                 api_versions=self.context["config"].get(
                                     "api_versions"),
                                 superclass=matcher,
                                 task_id=self.get_owner_id())
