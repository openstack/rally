# All Rights Reserved.
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

import os

from rally.common import cfg
from rally.common import utils as rutils
from rally.plugins.openstack import service
from rally.plugins.openstack.services.image import glance_common
from rally.plugins.openstack.services.image import image
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF


@service.service("glance", service_type="image", version="1")
class GlanceV1Service(service.Service, glance_common.GlanceMixin):

    @atomic.action_timer("glance_v1.create_image")
    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     is_public=True, min_disk=0, min_ram=0,
                     properties=None):
        """Creates new image.

        :param image_name: Image name for which need to be created
        :param container_format: Container format
        :param image_location: The new image's location
        :param disk_format: Disk format
        :param is_public: The created image's public status
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: Dict of image properties
        """
        image_location = os.path.expanduser(image_location)
        image_name = image_name or self.generate_random_name()
        kwargs = {}

        try:
            if os.path.isfile(image_location):
                kwargs["data"] = open(image_location)
            else:
                kwargs["copy_from"] = image_location

            image_obj = self._clients.glance("1").images.create(
                name=image_name,
                container_format=container_format,
                disk_format=disk_format,
                is_public=is_public,
                min_disk=min_disk,
                min_ram=min_ram,
                properties=properties,
                **kwargs)

            rutils.interruptable_sleep(CONF.openstack.
                                       glance_image_create_prepoll_delay)

            image_obj = utils.wait_for_status(
                image_obj, ["active"],
                update_resource=self.get_image,
                timeout=CONF.openstack.glance_image_create_timeout,
                check_interval=CONF.openstack.glance_image_create_poll_interval
            )

        finally:
            if "data" in kwargs:
                kwargs["data"].close()

        return image_obj

    @atomic.action_timer("glance_v1.update_image")
    def update_image(self, image_id, image_name=None, min_disk=0,
                     min_ram=0):
        """Update image.

        :param image_id: ID of image to update
        :param image_name: Image name to be updated to
        :param min_disk: The min disk of updated image
        :param min_ram: The min ram of updated image
        """
        image_name = image_name or self.generate_random_name()

        return self._clients.glance("1").images.update(image_id,
                                                       name=image_name,
                                                       min_disk=min_disk,
                                                       min_ram=min_ram)

    @atomic.action_timer("glance_v1.list_images")
    def list_images(self, status="active", is_public=None, owner=None):
        """List images.

        :param status: Filter in images for the specified status
        :param is_public: Filter in images for the specified public status
        :param owner: Filter in images for tenant ID
        """
        # NOTE(boris-42): image.list() is lazy method which doesn't query API
        #                 until it's used, do not remove list().
        return list(self._clients.glance("1").images.list(status=status,
                                                          owner=owner,
                                                          is_public=is_public))

    @atomic.action_timer("glance_v1.set_visibility")
    def set_visibility(self, image_id, is_public=True):
        """Update visibility.

        :param image_id: ID of image to update
        :param is_public: Image is public or not
        """
        self._clients.glance("1").images.update(image_id, is_public=is_public)


@service.compat_layer(GlanceV1Service)
class UnifiedGlanceV1Service(glance_common.UnifiedGlanceMixin, image.Image):
    """Compatibility layer for Glance V1."""

    @staticmethod
    def _check_v1_visibility(visibility):
        visibility_values = ["public", "private"]
        if visibility and visibility not in visibility_values:
            raise image.VisibilityException(
                message="Improper visibility value: %s in glance_v1"
                        % visibility)

    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility="public", min_disk=0,
                     min_ram=0, properties=None):
        """Creates new image.

        :param image_name: Image name for which need to be created
        :param container_format: Container format
        :param image_location: The new image's location
        :param disk_format: Disk format
        :param visibility: The created image's visible status
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: Dict of image properties
        """
        self._check_v1_visibility(visibility)

        is_public = visibility != "private"
        image_obj = self._impl.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            is_public=is_public,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)
        return self._unify_image(image_obj)

    def update_image(self, image_id, image_name=None, min_disk=0,
                     min_ram=0, remove_props=None):
        """Update image.

        :param image_id: ID of image to update
        :param image_name: Image name to be updated to
        :param min_disk: The min disk of updated image
        :param min_ram: The min ram of updated image
        :param remove_props: List of property names to remove
        """
        if remove_props is not None:
            raise image.RemovePropsException("Remove prop: %s is not"
                                             "supported in"
                                             "glance_v1" % remove_props)
        image_obj = self._impl.update_image(
            image_id=image_id,
            image_name=image_name,
            min_disk=min_disk,
            min_ram=min_ram)
        return self._unify_image(image_obj)

    def list_images(self, status="active", visibility=None, owner=None):
        """List images.

        :param status: Filter in images for the specified status
        :param visibility: Filter in images for the specified visibility
        :param owner: Filter in images for tenant ID
        """
        self._check_v1_visibility(visibility)

        is_public = visibility != "private"

        images = self._impl.list_images(status=status, is_public=is_public)
        return [self._unify_image(i) for i in images]

    def set_visibility(self, image_id, visibility="public"):
        """Update visibility.

        :param image_id: ID of image to update
        :param visibility: The visibility of specified image
        """
        self._check_v1_visibility(visibility)

        is_public = visibility != "private"
        self._impl.set_visibility(image_id=image_id, is_public=is_public)
