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

import tempfile

import ddt
import fixtures
import mock

from rally.plugins.openstack.services.image import glance_v1
from rally.plugins.openstack.services.image import image
from tests.unit import test


PATH = ("rally.plugins.openstack.services.image.glance_common."
        "UnifiedGlanceMixin._unify_image")


@ddt.ddt
class GlanceV1ServiceTestCase(test.TestCase):
    _tempfile = tempfile.NamedTemporaryFile()

    def setUp(self):
        super(GlanceV1ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.gc = self.clients.glance.return_value
        self.name_generator = mock.MagicMock()
        self.service = glance_v1.GlanceV1Service(
            self.clients, name_generator=self.name_generator)
        self.mock_wait_for_status = fixtures.MockPatch(
            "rally.task.utils.wait_for_status")
        self.useFixture(self.mock_wait_for_status)

    @ddt.data({"location": "image_location", "is_public": True},
              {"location": _tempfile.name, "is_public": False})
    @ddt.unpack
    @mock.patch("six.moves.builtins.open")
    def test_create_image(self, mock_open, location, is_public):
        image_name = "image_name"
        container_format = "container_format"
        disk_format = "disk_format"
        properties = {"fakeprop": "fake"}

        image = self.service.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=location,
            disk_format=disk_format,
            is_public=is_public,
            properties=properties)

        call_args = {"container_format": container_format,
                     "disk_format": disk_format,
                     "is_public": is_public,
                     "name": image_name,
                     "min_disk": 0,
                     "min_ram": 0,
                     "properties": properties}

        if location.startswith("/"):
            call_args["data"] = mock_open.return_value
            mock_open.assert_called_once_with(location)
            mock_open.return_value.close.assert_called_once_with()
        else:
            call_args["copy_from"] = location

        self.gc.images.create.assert_called_once_with(**call_args)
        self.assertEqual(image, self.mock_wait_for_status.mock.return_value)

    @ddt.data({"image_name": None},
              {"image_name": "test_image_name"})
    @ddt.unpack
    def test_update_image(self, image_name):
        image_id = "image_id"
        min_disk = 0
        min_ram = 0
        expected_image_name = image_name or self.name_generator.return_value

        image = self.service.update_image(image_id=image_id,
                                          image_name=image_name,
                                          min_disk=min_disk,
                                          min_ram=min_ram)
        self.assertEqual(self.gc.images.update.return_value, image)
        self.gc.images.update.assert_called_once_with(image_id,
                                                      name=expected_image_name,
                                                      min_disk=min_disk,
                                                      min_ram=min_ram)

    @ddt.data({"status": "activate", "is_public": True, "owner": "owner"},
              {"status": "activate", "is_public": False, "owner": "owner"},
              {"status": "activate", "is_public": None, "owner": "owner"})
    @ddt.unpack
    def test_list_images(self, status, is_public, owner):
        self.service.list_images(is_public=is_public, status=status,
                                 owner=owner)
        self.gc.images.list.assert_called_once_with(status=status,
                                                    owner=owner,
                                                    is_public=is_public)

    def test_set_visibility(self):
        image_id = "image_id"
        is_public = True
        self.service.set_visibility(image_id=image_id)
        self.gc.images.update.assert_called_once_with(
            image_id, is_public=is_public)


@ddt.ddt
class UnifiedGlanceV1ServiceTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedGlanceV1ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.service = glance_v1.UnifiedGlanceV1Service(self.clients)
        self.service._impl = mock.create_autospec(self.service._impl)

    @ddt.data({"visibility": "public"},
              {"visibility": "private"})
    @ddt.unpack
    @mock.patch(PATH)
    def test_create_image(self, mock_image__unify_image, visibility):
        image_name = "image_name"
        container_format = "container_format"
        image_location = "image_location"
        disk_format = "disk_format"
        properties = {"fakeprop": "fake"}

        image = self.service.create_image(image_name=image_name,
                                          container_format=container_format,
                                          image_location=image_location,
                                          disk_format=disk_format,
                                          visibility=visibility,
                                          properties=properties)

        is_public = visibility == "public"
        callargs = {"image_name": image_name,
                    "container_format": container_format,
                    "image_location": image_location,
                    "disk_format": disk_format,
                    "is_public": is_public,
                    "min_disk": 0,
                    "min_ram": 0,
                    "properties": properties}
        self.service._impl.create_image.assert_called_once_with(**callargs)
        self.assertEqual(mock_image__unify_image.return_value, image)

    @mock.patch(PATH)
    def test_update_image(self, mock_image__unify_image):
        image_id = "image_id"
        image_name = "image_name"
        callargs = {"image_id": image_id,
                    "image_name": image_name,
                    "min_disk": 0,
                    "min_ram": 0}

        image = self.service.update_image(image_id,
                                          image_name=image_name)

        self.assertEqual(mock_image__unify_image.return_value, image)
        self.service._impl.update_image.assert_called_once_with(**callargs)

    @mock.patch(PATH)
    def test_list_images(self, mock_image__unify_image):
        images = [mock.MagicMock()]
        self.service._impl.list_images.return_value = images

        status = "active"
        visibility = "public"
        is_public = visibility == "public"
        self.assertEqual([mock_image__unify_image.return_value],
                         self.service.list_images(status,
                                                  visibility=visibility))
        self.service._impl.list_images.assert_called_once_with(
            status=status,
            is_public=is_public)

    def test_set_visibility(self):
        image_id = "image_id"
        visibility = "private"
        is_public = visibility == "public"
        self.service.set_visibility(image_id=image_id, visibility=visibility)
        self.service._impl.set_visibility.assert_called_once_with(
            image_id=image_id, is_public=is_public)

    def test_set_visibility_failure(self):
        image_id = "image_id"
        visibility = "error"
        self.assertRaises(image.VisibilityException,
                          self.service.set_visibility,
                          image_id=image_id,
                          visibility=visibility)
