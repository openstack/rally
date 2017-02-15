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

from glanceclient import exc as glance_exc

from rally import exceptions
from rally.plugins.openstack.services.image import image as image_service
from rally.task import atomic


class GlanceMixin(object):

    def _get_client(self):
        return self._clients.glance(self.version)

    def get_image(self, image):
        """Get specified image.

        :param image: ID or object with ID of image to obtain.
        """
        image_id = getattr(image, "id", image)
        try:
            aname = "glance_v%s.get_image" % self.version
            with atomic.ActionTimer(self, aname):
                return self._get_client().images.get(image_id)
        except glance_exc.HTTPNotFound:
            raise exceptions.GetResourceNotFound(resource=image)

    def delete_image(self, image_id):
        """Delete image."""
        aname = "glance_v%s.delete_image" % self.version
        with atomic.ActionTimer(self, aname):
            self._get_client().images.delete(image_id)

    def download_image(self, image_id, do_checksum=True):
        """Retrieve data of an image.

        :param image_id: ID of the image to download.
        :param do_checksum: Enable/disable checksum validation.
        :returns: An iterable body or None
        """
        aname = "glance_v%s.download_image" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().images.data(image_id,
                                                  do_checksum=do_checksum)


class UnifiedGlanceMixin(object):

    @staticmethod
    def _unify_image(image):
        if hasattr(image, "visibility"):
            return image_service.UnifiedImage(id=image.id, name=image.name,
                                              status=image.status,
                                              visibility=image.visibility)
        else:
            return image_service.UnifiedImage(
                id=image.id, name=image.name,
                status=image.status,
                visibility=("public" if image.is_public else "private"))

    def get_image(self, image):
        """Get specified image.

        :param image: ID or object with ID of image to obtain.
        """
        image_obj = self._impl.get_image(image=image)
        return self._unify_image(image_obj)

    def delete_image(self, image_id):
        """Delete image."""
        self._impl.delete_image(image_id=image_id)

    def download_image(self, image_id, do_checksum=True):
        """Download data for an image.

        :param image_id: image id to look up
        :param do_checksum: Enable/disable checksum validation
        :rtype: iterable containing image data or None
        """
        return self._impl.download_image(image_id, do_checksum=do_checksum)
