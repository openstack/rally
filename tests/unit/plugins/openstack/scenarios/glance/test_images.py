# Copyright 2014: Mirantis Inc.
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

import mock

from rally import exceptions
from rally.plugins.openstack.scenarios.glance import images
from tests.unit import fakes
from tests.unit import test

BASE = "rally.plugins.openstack.scenarios.glance.images"
GLANCE_V2_PATH = ("rally.plugins.openstack.services.image.glance_v2."
                  "GlanceV2Service")


class GlanceBasicTestCase(test.ScenarioTestCase):

    def get_test_context(self):
        context = super(GlanceBasicTestCase, self).get_test_context()
        context.update({
            "admin": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "user": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake_tenant_id",
                       "name": "fake_tenant_name"}
        })
        return context

    def setUp(self):
        super(GlanceBasicTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.image.image.Image")
        self.addCleanup(patch.stop)
        self.mock_image = patch.start()

    def test_create_and_list_image(self):
        image_service = self.mock_image.return_value
        fake_image = mock.Mock(id=1, name="img_2")
        image_service.create_image.return_value = fake_image
        image_service.list_images.return_value = [
            mock.Mock(id=0, name="img_1"),
            fake_image,
            mock.Mock(id=2, name="img_3")]
        properties = {"fakeprop": "fake"}
        call_args = {"container_format": "cf",
                     "image_location": "url",
                     "disk_format": "df",
                     "visibility": "vs",
                     "min_disk": 0,
                     "min_ram": 0,
                     "properties": properties}
        # Positive case
        images.CreateAndListImage(self.context).run(
            "cf", "url", "df", "vs", 0, 0, properties)
        image_service.create_image.assert_called_once_with(**call_args)

        # Negative case: image isn't created
        image_service.create_image.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          images.CreateAndListImage(self.context).run,
                          "cf", "url", "df", "vs", 0, 0, properties)
        image_service.create_image.assert_called_with(**call_args)

        # Negative case: created image n ot in the list of available images
        image_service.create_image.return_value = mock.Mock(
            id=12, name="img_nameN")
        self.assertRaises(exceptions.RallyAssertionError,
                          images.CreateAndListImage(self.context).run,
                          "cf", "url", "df", "vs", 0, 0, properties)
        image_service.create_image.assert_called_with(**call_args)
        image_service.list_images.assert_called_with()

    def test_list_images(self):
        image_service = self.mock_image.return_value

        images.ListImages(self.context).run()
        image_service.list_images.assert_called_once_with()

    def test_create_and_delete_image(self):
        image_service = self.mock_image.return_value

        fake_image = fakes.FakeImage(id=1, name="imagexxx")
        image_service.create_image.return_value = fake_image
        properties = {"fakeprop": "fake"}
        call_args = {"container_format": "cf",
                     "image_location": "url",
                     "disk_format": "df",
                     "visibility": "vs",
                     "min_disk": 0,
                     "min_ram": 0,
                     "properties": properties}

        images.CreateAndDeleteImage(self.context).run(
            "cf", "url", "df", "vs", 0, 0, properties)

        image_service.create_image.assert_called_once_with(**call_args)
        image_service.delete_image.assert_called_once_with(fake_image.id)

    def test_create_and_get_image(self):
        image_service = self.mock_image.return_value

        fake_image = fakes.FakeImage(id=1, name="img_name1")
        image_service.create_image.return_value = fake_image
        fake_image_info = fakes.FakeImage(id=1, name="img_name1",
                                          status="active")
        image_service.get_image.return_value = fake_image_info
        properties = {"fakeprop": "fake"}
        call_args = {"container_format": "cf",
                     "image_location": "url",
                     "disk_format": "df",
                     "visibility": "vs",
                     "min_disk": 0,
                     "min_ram": 0,
                     "properties": properties}

        # Positive case
        images.CreateAndGetImage(self.context).run(
            "cf", "url", "df", "vs", 0, 0, properties)
        image_service.create_image.assert_called_once_with(**call_args)
        image_service.get_image.assert_called_once_with(fake_image)

        # Negative case: image isn't created
        image_service.create_image.reset_mock()
        image_service.create_image.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          images.CreateAndGetImage(self.context).run,
                          "cf", "url", "df", "vs", 0, 0, properties)
        image_service.create_image.assert_called_with(**call_args)

        # Negative case: image obtained in _get_image not the created image
        image_service.create_image.reset_mock()
        image_service.get_image.reset_mock()
        image_service.create_image.return_value = fakes.FakeImage(
            id=12, name="img_nameN")
        self.assertRaises(exceptions.RallyAssertionError,
                          images.CreateAndGetImage(self.context).run,
                          "cf", "url", "df", "vs", 0, 0, properties)
        image_service.create_image.assert_called_with(**call_args)
        image_service.get_image.assert_called_with(
            image_service.create_image.return_value)

    def test_create_and_download_image(self):
        image_service = self.mock_image.return_value

        fake_image = fakes.FakeImage()
        image_service.create_image.return_value = fake_image
        properties = {"fakeprop": "fake"}
        call_args = {"container_format": "cf",
                     "image_location": "url",
                     "disk_format": "df",
                     "visibility": "vs",
                     "min_disk": 0,
                     "min_ram": 0,
                     "properties": properties}

        images.CreateAndDownloadImage(self.context).run(
            "cf", "url", "df", "vs", 0, 0, properties=properties)

        image_service.create_image.assert_called_once_with(**call_args)
        image_service.download_image.assert_called_once_with(fake_image.id)

    @mock.patch("%s.CreateImageAndBootInstances._boot_servers" % BASE)
    def test_create_image_and_boot_instances(self, mock_boot_servers):
        image_service = self.mock_image.return_value

        fake_image = fakes.FakeImage()
        fake_servers = [mock.Mock() for i in range(5)]
        image_service.create_image.return_value = fake_image
        mock_boot_servers.return_value = fake_servers
        boot_server_kwargs = {"fakeserverarg": "f"}
        properties = {"fakeprop": "fake"}
        call_args = {"container_format": "cf",
                     "image_location": "url",
                     "disk_format": "df",
                     "visibility": "vs",
                     "min_disk": 0,
                     "min_ram": 0,
                     "properties": properties}

        images.CreateImageAndBootInstances(self.context).run(
            "cf", "url", "df", "fid", 5, visibility="vs", min_disk=0,
            min_ram=0, properties=properties,
            boot_server_kwargs=boot_server_kwargs)
        image_service.create_image.assert_called_once_with(**call_args)
        mock_boot_servers.assert_called_once_with("image-id-0", "fid",
                                                  5, **boot_server_kwargs)

    def test_create_and_update_image(self):
        image_service = self.mock_image.return_value

        fake_image = fakes.FakeImage(id=1, name="imagexxx")
        image_service.create_image.return_value = fake_image
        properties = {"fakeprop": "fake"}
        create_args = {"container_format": "cf",
                       "image_location": "url",
                       "disk_format": "df",
                       "visibility": "vs",
                       "min_disk": 0,
                       "min_ram": 0,
                       "properties": properties}

        images.CreateAndUpdateImage(self.context).run(
            "cf", "url", "df", None, "vs", 0, 0, properties, 0, 0)

        image_service.create_image.assert_called_once_with(**create_args)
        image_service.update_image.assert_called_once_with(
            fake_image.id, min_disk=0, min_ram=0, remove_props=None)

    @mock.patch("%s.create_image" % GLANCE_V2_PATH)
    @mock.patch("%s.deactivate_image" % GLANCE_V2_PATH)
    def test_create_and_deactivate_image(self, mock_deactivate_image,
                                         mock_create_image):
        fake_image = fakes.FakeImage(id=1, name="img_name1")
        mock_create_image.return_value = fake_image
        call_args = {"container_format": "cf",
                     "image_location": "url",
                     "disk_format": "df",
                     "visibility": "vs",
                     "min_disk": 0,
                     "min_ram": 0}

        images.CreateAndDeactivateImage(self.context).run(
            "cf", "url", "df", "vs", 0, 0)
        mock_create_image.assert_called_once_with(**call_args)
        mock_deactivate_image.assert_called_once_with(fake_image.id)
