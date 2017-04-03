#
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

import collections

from rally.plugins.openstack import service

from oslo_config import cfg

GLANCE_BENCHMARK_OPTS = [
    cfg.FloatOpt("glance_image_create_prepoll_delay",
                 default=2.0,
                 help="Time to sleep after creating a resource before "
                      "polling for it status"),
    cfg.FloatOpt("glance_image_create_poll_interval",
                 default=1.0,
                 help="Interval between checks when waiting for image "
                      "creation.")
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(GLANCE_BENCHMARK_OPTS, group=benchmark_group)

UnifiedImage = collections.namedtuple("Image", ["id", "name", "visibility",
                                                "status"])


class VisibilityException(Exception):
    """Wrong visibility value exception.

    """


class Image(service.UnifiedOpenStackService):
    @classmethod
    def is_applicable(cls, clients):
        cloud_version = str(clients.glance().version).split(".")[0]
        return cloud_version == cls._meta_get("impl")._meta_get("version")

    @staticmethod
    def _unify_image(image):
        if hasattr(image, "visibility"):
            return UnifiedImage(id=image.id, name=image.name,
                                status=image.status,
                                visibility=image.visibility)
        else:
            return UnifiedImage(
                id=image.id, name=image.name,
                status=image.status,
                visibility=("public" if image.is_public else "private"))

    @service.should_be_overridden
    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility="private", min_disk=0,
                     min_ram=0):
        """Creates new image.

        :param image_name: Image name for which need to be created
        :param container_format: Container format
        :param image_location: The new image's location
        :param disk_format: Disk format
        :param visibility: The access permission for the created image.
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        """
        image = self._impl.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram)
        return image

    @service.should_be_overridden
    def list_images(self, status="active", visibility=None, owner=None):
        """List images.

        :param status: Filter in images for the specified status
        :param visibility: Filter in images for the specified visibility
        :param owner: Filter in images for tenant ID
        """
        return self._impl.list_images(status=status,
                                      visibility=visibility,
                                      owner=owner)

    @service.should_be_overridden
    def set_visibility(self, image_id, visibility="public"):
        """Update visibility.

        :param image_id: ID of image to update
        :param visibility: The visibility of specified image
        """
        self._impl.set_visibility(image_id, visibility=visibility)

    @service.should_be_overridden
    def get_image(self, image):
        """Get specified image.

        :param image: ID or object with ID of image to obtain.
        """
        return self._impl.get_image(image)

    @service.should_be_overridden
    def delete_image(self, image_id):
        """delete image."""
        self._impl.delete_image(image_id)
