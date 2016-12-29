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
from glanceclient import exc as glance_exc
import mock

from rally import exceptions
from rally.plugins.openstack.services.image import glance_v2
from tests.unit import test

from oslotest import mockpatch

PATH = "rally.plugins.openstack.services.image.image.Image._unify_image"


@ddt.ddt
class GlanceV2ServiceTestCase(test.TestCase):
    _tempfile = tempfile.NamedTemporaryFile()

    def setUp(self):
        super(GlanceV2ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.gc = self.clients.glance.return_value
        self.name_generator = mock.MagicMock()
        self.service = glance_v2.GlanceV2Service(
            self.clients, name_generator=self.name_generator)
        self.mock_wait_for_status = mockpatch.Patch(
            "rally.task.utils.wait_for_status")
        self.useFixture(self.mock_wait_for_status)

    @ddt.data({"location": "image_location"},
              {"location": _tempfile.name})
    @ddt.unpack
    @mock.patch("requests.get")
    @mock.patch("six.moves.builtins.open")
    def test_create_image(self, mock_open, mock_requests_get, location):
        image_name = "image_name"
        container_format = "container_format"
        disk_format = "disk_format"
        visibility = "public"

        image = self.service.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=location,
            disk_format=disk_format,
            visibility=visibility)

        call_args = {"container_format": container_format,
                     "disk_format": disk_format,
                     "name": image_name,
                     "visibility": visibility,
                     "min_disk": 0,
                     "min_ram": 0}

        if location.startswith("/"):
            mock_open.assert_called_once_with(location)
            mock_open.return_value.close.assert_called_once_with()
        else:
            mock_requests_get.assert_called_once_with(location, stream=True)
        self.gc.images.create.assert_called_once_with(**call_args)
        self.assertEqual(image, self.mock_wait_for_status.mock.return_value)

    def test_get_image(self):
        image_id = "image_id"
        self.service.get_image(image_id)
        self.gc.images.get.assert_called_once_with(image_id)

    def test_get_image_exception(self):
        image_id = "image_id"
        self.clients.glance(
            "1").images.get.side_effect = glance_exc.HTTPNotFound

        self.assertRaises(exceptions.GetResourceNotFound,
                          self.service.get_image, image_id)

    def test_list_images(self):
        status = "active"
        kwargs = {"status": status}

        self.assertEqual(self.gc.images.list.return_value,
                         self.service.list_images())
        self.gc.images.list.assert_called_once_with(**kwargs)

    def test_set_visibility(self):
        image_id = "image_id"
        visibility = "shared"
        self.service.set_visibility(image_id=image_id)
        self.gc.images.update.assert_called_once_with(
            image_id,
            visibility=visibility)

    def test_delete_image(self):
        image_id = "image_id"
        self.service.delete_image(image_id)
        self.gc.images.delete.assert_called_once_with(image_id)


@ddt.ddt
class UnifiedGlanceV2ServiceTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedGlanceV2ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.service = glance_v2.UnifiedGlanceV2Service(self.clients)
        self.service._impl = mock.MagicMock()

    @mock.patch(PATH)
    def test_create_image(self, mock_image__unify_image):
        image_name = "image_name"
        container_format = "container_format"
        image_location = "image_location"
        disk_format = "disk_format"
        visibility = "public"
        callargs = {"image_name": image_name,
                    "container_format": container_format,
                    "image_location": image_location,
                    "disk_format": disk_format,
                    "visibility": visibility,
                    "min_disk": 0,
                    "min_ram": 0}

        image = self.service.create_image(image_name=image_name,
                                          container_format=container_format,
                                          image_location=image_location,
                                          disk_format=disk_format,
                                          visibility=visibility)

        self.assertEqual(mock_image__unify_image.return_value, image)
        self.service._impl.create_image.assert_called_once_with(**callargs)

    @mock.patch(PATH)
    def test_get_image(self, mock_image__unify_image):
        image_id = "image_id"
        image = self.service.get_image(image_id=image_id)

        self.assertEqual(mock_image__unify_image.return_value, image)
        self.service._impl.get_image.assert_called_once_with(
            image_id=image_id)

    @mock.patch(PATH)
    def test_list_images(self, mock_image__unify_image):
        images = [mock.MagicMock()]
        self.service._impl.list_images.return_value = images

        status = "active"
        self.assertEqual([mock_image__unify_image.return_value],
                         self.service.list_images())
        self.service._impl.list_images.assert_called_once_with(
            status=status,
            visibility=None)

    def test_set_visibility(self):
        image_id = "image_id"
        visibility = "private"

        self.service.set_visibility(image_id=image_id, visibility=visibility)
        self.service._impl.set_visibility.assert_called_once_with(
            image_id=image_id, visibility=visibility)

    def test_delete_image(self):
        image_id = "image_id"
        self.service.delete_image(image_id)
        self.service._impl.delete_image.assert_called_once_with(
            image_id=image_id)
