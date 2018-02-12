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
import time

import requests

from rally.common import cfg
from rally.common import utils as rutils
from rally.plugins.openstack import service
from rally.plugins.openstack.services.image import glance_common
from rally.plugins.openstack.services.image import image
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF


@service.service("glance", service_type="image", version="2")
class GlanceV2Service(service.Service, glance_common.GlanceMixin):

    @atomic.action_timer("glance_v2.upload_data")
    def upload_data(self, image_id, image_location):
        """Upload the data for an image.

        :param image_id: Image ID to upload data to.
        :param image_location: Location of the data to upload to.
        """
        image_location = os.path.expanduser(image_location)
        image_data = None
        response = None
        try:
            if os.path.isfile(image_location):
                image_data = open(image_location)
            else:
                response = requests.get(image_location, stream=True)
                image_data = response.raw
            self._clients.glance("2").images.upload(image_id, image_data)
        finally:
            if image_data is not None:
                image_data.close()
            if response is not None:
                response.close()

    @atomic.action_timer("glance_v2.create_image")
    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility=None, min_disk=0,
                     min_ram=0, properties=None):
        """Creates new image.

        :param image_name: Image name for which need to be created
        :param container_format: Container format
        :param image_location: The new image's location
        :param disk_format: Disk format
        :param visibility: The created image's visible status.
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: Dict of image properties
        """
        image_name = image_name or self.generate_random_name()

        properties = properties or {}
        image_obj = self._clients.glance("2").images.create(
            name=image_name,
            container_format=container_format,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            **properties)

        rutils.interruptable_sleep(CONF.openstack.
                                   glance_image_create_prepoll_delay)

        start = time.time()
        image_obj = utils.wait_for_status(
            image_obj.id, ["queued"],
            update_resource=self.get_image,
            timeout=CONF.openstack.glance_image_create_timeout,
            check_interval=CONF.openstack.glance_image_create_poll_interval)
        timeout = time.time() - start

        self.upload_data(image_obj.id, image_location=image_location)

        image_obj = utils.wait_for_status(
            image_obj, ["active"],
            update_resource=self.get_image,
            timeout=timeout,
            check_interval=CONF.openstack.glance_image_create_poll_interval)
        return image_obj

    @atomic.action_timer("glance_v2.update_image")
    def update_image(self, image_id, image_name=None, min_disk=0,
                     min_ram=0, remove_props=None):
        """Update image.

        :param image_id: ID of image to update
        :param image_name: Image name to be updated to
        :param min_disk: The min disk of updated image
        :param min_ram: The min ram of updated image
        :param remove_props: List of property names to remove
        """
        image_name = image_name or self.generate_random_name()

        return self._clients.glance("2").images.update(
            image_id=image_id,
            name=image_name,
            min_disk=min_disk,
            min_ram=min_ram,
            remove_props=remove_props)

    @atomic.action_timer("glance_v2.list_images")
    def list_images(self, status="active", visibility=None, owner=None):
        """List images.

        :param status: Filter in images for the specified status
        :param visibility: Filter in images for the specified visibility
        :param owner: Filter in images for tenant ID
        """
        filters = {}
        filters["status"] = status
        if visibility:
            filters["visibility"] = visibility
        if owner:
            filters["owner"] = owner
        # NOTE(boris-42): image.list() is lazy method which doesn't query API
        #                 until it's used, do not remove list().
        return list(self._clients.glance("2").images.list(filters=filters))

    @atomic.action_timer("glance_v2.set_visibility")
    def set_visibility(self, image_id, visibility="shared"):
        """Update visibility.

        :param image_id: ID of image to update
        :param visibility: The visibility of specified image
        """
        self._clients.glance("2").images.update(image_id,
                                                visibility=visibility)

    @atomic.action_timer("glance_v2.deactivate_image")
    def deactivate_image(self, image_id):
        """deactivate image."""
        self._clients.glance("2").images.deactivate(image_id)

    @atomic.action_timer("glance_v2.reactivate_image")
    def reactivate_image(self, image_id):
        """reactivate image."""
        self._clients.glance("2").images.reactivate(image_id)


@service.compat_layer(GlanceV2Service)
class UnifiedGlanceV2Service(glance_common.UnifiedGlanceMixin, image.Image):
    """Compatibility layer for Glance V2."""

    @staticmethod
    def _check_v2_visibility(visibility):
        visibility_values = ["public", "private", "shared", "community"]
        if visibility and visibility not in visibility_values:
            raise image.VisibilityException(
                message="Improper visibility value: %s in glance_v2"
                        % visibility)

    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility=None, min_disk=0,
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
        image_obj = self._impl.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
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
        image_obj = self._impl.update_image(
            image_id=image_id,
            image_name=image_name,
            min_disk=min_disk,
            min_ram=min_ram,
            remove_props=remove_props)
        return self._unify_image(image_obj)

    def list_images(self, status="active", visibility=None, owner=None):
        """List images.

        :param status: Filter in images for the specified status
        :param visibility: Filter in images for the specified visibility
        :param owner: Filter in images for tenant ID
        """
        self._check_v2_visibility(visibility)

        images = self._impl.list_images(
            status=status, visibility=visibility, owner=owner)
        return [self._unify_image(i) for i in images]

    def set_visibility(self, image_id, visibility="shared"):
        """Update visibility.

        :param image_id: ID of image to update
        :param visibility: The visibility of specified image
        """
        self._check_v2_visibility(visibility)

        self._impl.set_visibility(image_id=image_id, visibility=visibility)
