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

from rally.plugins.openstack.services.image import glance_v2
from tests.unit import test


PATH = "rally.plugins.openstack.services.image"


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
        self.mock_wait_for_status = fixtures.MockPatch(
            "rally.task.utils.wait_for_status")
        self.useFixture(self.mock_wait_for_status)

    @ddt.data({"location": "image_location"},
              {"location": _tempfile.name})
    @ddt.unpack
    @mock.patch("requests.get")
    @mock.patch("six.moves.builtins.open")
    def test_upload(self, mock_open, mock_requests_get, location):
        image_id = "foo"

        self.service.upload_data(image_id, image_location=location)

        if location.startswith("/"):
            mock_open.assert_called_once_with(location)
            mock_open.return_value.close.assert_called_once_with()
            self.gc.images.upload.assert_called_once_with(
                image_id, mock_open.return_value)
        else:
            mock_requests_get.assert_called_once_with(location, stream=True)
            self.gc.images.upload.assert_called_once_with(
                image_id, mock_requests_get.return_value.raw)

    @mock.patch("%s.glance_v2.GlanceV2Service.upload_data" % PATH)
    def test_create_image(self, mock_upload_data):
        image_name = "image_name"
        container_format = "container_format"
        disk_format = "disk_format"
        visibility = "public"
        properties = {"fakeprop": "fake"}
        location = "location"

        image = self.service.create_image(
            image_name=image_name,
            container_format=container_format,
            image_location=location,
            disk_format=disk_format,
            visibility=visibility,
            properties=properties)

        call_args = {"container_format": container_format,
                     "disk_format": disk_format,
                     "name": image_name,
                     "visibility": visibility,
                     "min_disk": 0,
                     "min_ram": 0,
                     "fakeprop": "fake"}
        self.gc.images.create.assert_called_once_with(**call_args)
        self.assertEqual(image, self.mock_wait_for_status.mock.return_value)
        mock_upload_data.assert_called_once_with(
            self.mock_wait_for_status.mock.return_value.id,
            image_location=location)

    def test_update_image(self):
        image_id = "image_id"
        image_name1 = self.name_generator.return_value
        image_name2 = "image_name"
        min_disk = 0
        min_ram = 0
        remove_props = None

        # case: image_name is None:
        call_args1 = {"image_id": image_id,
                      "name": image_name1,
                      "min_disk": min_disk,
                      "min_ram": min_ram,
                      "remove_props": remove_props}
        image1 = self.service.update_image(image_id=image_id,
                                           image_name=None,
                                           min_disk=min_disk,
                                           min_ram=min_ram,
                                           remove_props=remove_props)
        self.assertEqual(self.gc.images.update.return_value, image1)
        self.gc.images.update.assert_called_once_with(**call_args1)

        # case: image_name is not None:
        call_args2 = {"image_id": image_id,
                      "name": image_name2,
                      "min_disk": min_disk,
                      "min_ram": min_ram,
                      "remove_props": remove_props}
        image2 = self.service.update_image(image_id=image_id,
                                           image_name=image_name2,
                                           min_disk=min_disk,
                                           min_ram=min_ram,
                                           remove_props=remove_props)
        self.assertEqual(self.gc.images.update.return_value, image2)
        self.gc.images.update.assert_called_with(**call_args2)

    def test_list_images(self):
        status = "active"
        kwargs = {"status": status}
        filters = {"filters": kwargs}
        self.gc.images.list.return_value = iter([1, 2, 3])

        self.assertEqual([1, 2, 3], self.service.list_images())
        self.gc.images.list.assert_called_once_with(**filters)

    def test_set_visibility(self):
        image_id = "image_id"
        visibility = "shared"
        self.service.set_visibility(image_id=image_id)
        self.gc.images.update.assert_called_once_with(
            image_id,
            visibility=visibility)

    def test_deactivate_image(self):
        image_id = "image_id"
        self.service.deactivate_image(image_id)
        self.gc.images.deactivate.assert_called_once_with(image_id)

    def test_reactivate_image(self):
        image_id = "image_id"
        self.service.reactivate_image(image_id)
        self.gc.images.reactivate.assert_called_once_with(image_id)


@ddt.ddt
class UnifiedGlanceV2ServiceTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedGlanceV2ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.service = glance_v2.UnifiedGlanceV2Service(self.clients)
        self.service._impl = mock.create_autospec(self.service._impl)

    @mock.patch("%s.glance_common.UnifiedGlanceMixin._unify_image" % PATH)
    def test_create_image(self, mock_image__unify_image):
        image_name = "image_name"
        container_format = "container_format"
        image_location = "image_location"
        disk_format = "disk_format"
        visibility = "public"
        properties = {"fakeprop": "fake"}
        callargs = {"image_name": image_name,
                    "container_format": container_format,
                    "image_location": image_location,
                    "disk_format": disk_format,
                    "visibility": visibility,
                    "min_disk": 0,
                    "min_ram": 0,
                    "properties": properties}

        image = self.service.create_image(image_name=image_name,
                                          container_format=container_format,
                                          image_location=image_location,
                                          disk_format=disk_format,
                                          visibility=visibility,
                                          properties=properties)

        self.assertEqual(mock_image__unify_image.return_value, image)
        self.service._impl.create_image.assert_called_once_with(**callargs)

    @mock.patch("%s.glance_common.UnifiedGlanceMixin._unify_image" % PATH)
    def test_update_image(self, mock_image__unify_image):
        image_id = "image_id"
        image_name = "image_name"
        callargs = {"image_id": image_id,
                    "image_name": image_name,
                    "min_disk": 0,
                    "min_ram": 0,
                    "remove_props": None}

        image = self.service.update_image(image_id,
                                          image_name=image_name)

        self.assertEqual(mock_image__unify_image.return_value, image)
        self.service._impl.update_image.assert_called_once_with(**callargs)

    @mock.patch("%s.glance_common.UnifiedGlanceMixin._unify_image" % PATH)
    def test_list_images(self, mock_image__unify_image):
        images = [mock.MagicMock()]
        self.service._impl.list_images.return_value = images

        status = "active"
        self.assertEqual([mock_image__unify_image.return_value],
                         self.service.list_images(owner="foo",
                                                  visibility="shared"))
        self.service._impl.list_images.assert_called_once_with(
            status=status,
            visibility="shared",
            owner="foo"
        )

    def test_set_visibility(self):
        image_id = "image_id"
        visibility = "private"

        self.service.set_visibility(image_id=image_id, visibility=visibility)
        self.service._impl.set_visibility.assert_called_once_with(
            image_id=image_id, visibility=visibility)
