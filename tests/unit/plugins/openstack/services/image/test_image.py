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

import ddt
import mock

from rally.plugins.openstack.services.image import glance_v1
from rally.plugins.openstack.services.image import glance_v2
from rally.plugins.openstack.services.image import image
from tests.unit import test


@ddt.ddt
class ImageTestCase(test.TestCase):

    def setUp(self):
        super(ImageTestCase, self).setUp()
        self.clients = mock.MagicMock()

    def get_service_with_fake_impl(self):
        path = "rally.plugins.openstack.services.image.image"
        with mock.patch("%s.Image.discover_impl" % path) as mock_discover:
            mock_discover.return_value = mock.MagicMock(), None
            service = image.Image(self.clients)
        return service

    @ddt.data(("image_name", "container_format", "image_location",
               "disk_format", "visibility", "min_disk", "min_ram"))
    def test_create_image(self, params):
        (image_name, container_format, image_location, disk_format,
         visibility, min_disk, min_ram) = params
        service = self.get_service_with_fake_impl()
        properties = {"fakeprop": "fake"}

        service.create_image(image_name=image_name,
                             container_format=container_format,
                             image_location=image_location,
                             disk_format=disk_format,
                             visibility=visibility,
                             min_disk=min_disk,
                             min_ram=min_ram,
                             properties=properties)

        service._impl.create_image.assert_called_once_with(
            image_name=image_name, container_format=container_format,
            image_location=image_location, disk_format=disk_format,
            visibility=visibility, min_disk=min_disk, min_ram=min_ram,
            properties=properties)

    @ddt.data(("image_id", "image_name", "min_disk", "min_ram",
               "remove_props"))
    def test_update_image(self, params):
        (image_id, image_name, min_disk, min_ram, remove_props) = params
        service = self.get_service_with_fake_impl()
        service.update_image(image_id,
                             image_name=image_name,
                             min_disk=min_disk,
                             min_ram=min_ram,
                             remove_props=remove_props)
        service._impl.update_image.assert_called_once_with(
            image_id, image_name=image_name, min_disk=min_disk,
            min_ram=min_ram, remove_props=remove_props)

    @ddt.data("image_id")
    def test_get_image(self, param):
        image_id = param
        service = self.get_service_with_fake_impl()
        service.get_image(image=image_id)
        service._impl.get_image.assert_called_once_with(image_id)

    @ddt.data(("status", "visibility", "owner"))
    def test_list_images(self, params):
        status, visibility, owner = params
        service = self.get_service_with_fake_impl()
        service.list_images(status=status, visibility=visibility, owner=owner)
        service._impl.list_images.assert_called_once_with(
            status=status, visibility=visibility, owner=owner)

    @ddt.data(("image_id", "visibility"))
    def test_set_visibility(self, params):
        image_id, visibility = params
        service = self.get_service_with_fake_impl()
        service.set_visibility(image_id=image_id, visibility=visibility)
        service._impl.set_visibility.assert_called_once_with(
            image_id, visibility=visibility)

    def test_delete_image(self):
        image_id = "image_id"
        service = self.get_service_with_fake_impl()
        service.delete_image(image_id=image_id)
        service._impl.delete_image.assert_called_once_with(image_id)

    def test_download_image(self):
        image_id = "image_id"
        service = self.get_service_with_fake_impl()
        service.download_image(image=image_id, do_checksum=True)
        service._impl.download_image.assert_called_once_with(image_id,
                                                             do_checksum=True)

    def test_is_applicable(self):
        clients = mock.Mock()

        clients.glance().version = "1.0"
        self.assertTrue(
            glance_v1.UnifiedGlanceV1Service.is_applicable(clients))

        clients.glance().version = "2.0"
        self.assertTrue(
            glance_v2.UnifiedGlanceV2Service.is_applicable(clients))
