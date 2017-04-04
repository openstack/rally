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

from glanceclient import exc as glance_exc
from oslo_config import cfg
import requests

from rally.common import utils as rutils
from rally import exceptions
from rally.plugins.openstack import service
from rally.plugins.openstack.services.image import image
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF


@service.service("glance", service_type="image", version="2")
class GlanceV2Service(service.Service):

    @atomic.action_timer("glance_v2.create_image")
    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility=None, min_disk=0,
                     min_ram=0):
        """Creates new image.

        :param image_name: Image name for which need to be created
        :param container_format: Container format
        :param image_location: The new image's location
        :param disk_format: Disk format
        :param visibility: The created image's visible status.
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        """
        image_name = image_name or self.generate_random_name()

        image_obj = self._clients.glance("2").images.create(
            name=image_name,
            container_format=container_format,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram)

        image_location = os.path.expanduser(image_location)
        rutils.interruptable_sleep(CONF.benchmark.
                                   glance_image_create_prepoll_delay)

        start = time.time()
        image_obj = utils.wait_for_status(
            image_obj.id, ["queued"],
            update_resource=self.get_image,
            timeout=CONF.benchmark.glance_image_create_timeout,
            check_interval=CONF.benchmark.glance_image_create_poll_interval)
        timeout = time.time() - start

        image_data = None
        response = None
        try:
            if os.path.isfile(image_location):
                image_data = open(image_location)
            else:
                response = requests.get(image_location, stream=True)
                image_data = response.raw
            self._clients.glance("2").images.upload(image_obj.id, image_data)
        finally:
            if image_data is not None:
                image_data.close()
            if response is not None:
                response.close()

        image_obj = utils.wait_for_status(
            image_obj, ["active"],
            update_resource=self.get_image,
            timeout=timeout,
            check_interval=CONF.benchmark.glance_image_create_poll_interval)
        return image_obj

    @atomic.action_timer("glance_v2.get_image")
    def get_image(self, image):
        """Get specified image.

        :param image: ID or object with ID of image to obtain.
        """
        image_id = getattr(image, "id", image)
        try:
            return self._clients.glance("2").images.get(image_id)
        except glance_exc.HTTPNotFound:
            raise exceptions.GetResourceNotFound(resource=image)

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
        images = self._clients.glance("2").images.list(filters=filters)
        return images

    @atomic.action_timer("glance_v2.set_visibility")
    def set_visibility(self, image_id, visibility="shared"):
        """Update visibility.

        :param image_id: ID of image to update
        :param visibility: The visibility of specified image
        """
        self._clients.glance("2").images.update(image_id,
                                                visibility=visibility)

    @atomic.action_timer("glance_v2.delete_image")
    def delete_image(self, image_id):
        """Delete image."""
        self._clients.glance("2").images.delete(image_id)


@service.compat_layer(GlanceV2Service)
class UnifiedGlanceV2Service(image.Image):
    """Compatibility layer for Glance V2."""

    @staticmethod
    def _check_v2_visibility(visibility):
        visibility_values = ["public", "private", "shared", "community"]
        if visibility and visibility not in visibility_values:
            raise image.VisibilityException("Improper visibility value: %s "
                                            "in glance_v2" % visibility)

    def create_image(self, image_name=None, container_format=None,
                     image_location=None, disk_format=None,
                     visibility=None, min_disk=0,
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
        image_obj = self._impl.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram)
        return self._unify_image(image_obj)

    def list_images(self, status="active", visibility=None, owner=None):
        """List images.

        :param status: Filter in images for the specified status
        :param visibility: Filter in images for the specified visibility
        :param owner: Filter in images for tenant ID
        """
        self._check_v2_visibility(visibility)

        images = self._impl.list_images(status=status, visibility=visibility)
        return [self._unify_image(i) for i in images]

    def set_visibility(self, image_id, visibility="shared"):
        """Update visibility.

        :param image_id: ID of image to update
        :param visibility: The visibility of specified image
        """
        self._check_v2_visibility(visibility)

        self._impl.set_visibility(image_id=image_id, visibility=visibility)

    def get_image(self, image):
        """Get specified image.

        :param image: ID or object with ID of image to obtain.
          """
        image_obj = self._impl.get_image(image=image)
        return self._unify_image(image_obj)

    def delete_image(self, image_id):
        """Delete image."""
        self._impl.delete_image(image_id=image_id)
