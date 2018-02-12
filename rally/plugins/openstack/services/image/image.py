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

from rally.common import cfg
from rally import exceptions
from rally.task import service


CONF = cfg.CONF

UnifiedImage = service.make_resource_cls(
    "Image", properties=["id", "name", "visibility", "status"])


class VisibilityException(exceptions.RallyException):
    """Wrong visibility value exception.

    """
    error_code = 531


class RemovePropsException(exceptions.RallyException):
    """Remove Props it not supported exception.

    """
    error_code = 560


class Image(service.UnifiedService):
    @classmethod
    def is_applicable(cls, clients):
        cloud_version = str(clients.glance().version).split(".")[0]
        return cloud_version == cls._meta_get("impl")._meta_get("version")

    @service.should_be_overridden
    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility="private", min_disk=0,
                     min_ram=0, properties=None):
        """Creates new image.

        :param image_name: Image name for which need to be created
        :param container_format: Container format
        :param image_location: The new image's location
        :param disk_format: Disk format
        :param visibility: The access permission for the created image.
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: Dict of image properties
        """
        properties = properties or {}
        image = self._impl.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)
        return image

    @service.should_be_overridden
    def update_image(self, image_id, image_name=None,
                     min_disk=0, min_ram=0, remove_props=None):
        """Update image.

        :param image_id: ID of image to update
        :param image_name: Image name to be updated to
        :param min_disk: The min disk of updated image
        :param min_ram: The min ram of updated image
        :param remove_props: List of property names to remove
        """
        return self._impl.update_image(
            image_id,
            image_name=image_name,
            min_disk=min_disk,
            min_ram=min_ram,
            remove_props=remove_props)

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

    @service.should_be_overridden
    def download_image(self, image, do_checksum=True):
        """Download data for an image.

        :param image: image object or id to look up
        :param do_checksum: Enable/disable checksum validation
        :rtype: iterable containing image data or None
        """
        return self._impl.download_image(image, do_checksum=do_checksum)
