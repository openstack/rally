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

from rally.plugins.openstack.scenarios.glance import images
from tests.unit import fakes
from tests.unit import test

BASE = "rally.plugins.openstack.scenarios.glance.images"


class GlanceImagesTestCase(test.ScenarioTestCase):

    @mock.patch("%s.CreateAndListImage._list_images" % BASE)
    @mock.patch("%s.CreateAndListImage._create_image" % BASE)
    @mock.patch("%s.CreateAndListImage.generate_random_name" % BASE,
                return_value="test-rally-image")
    def test_create_and_list_image(self,
                                   mock_random_name,
                                   mock_create_image,
                                   mock_list_images):
        images.CreateAndListImage(self.context).run(
            "cf", "url", "df", fakearg="f")
        mock_create_image.assert_called_once_with(
            "cf", "url", "df", fakearg="f")
        mock_list_images.assert_called_once_with()

    @mock.patch("%s.ListImages._list_images" % BASE)
    def test_list_images(self, mock_list_images__list_images):
        images.ListImages(self.context).run()
        mock_list_images__list_images.assert_called_once_with()

    @mock.patch("%s.CreateAndDeleteImage._delete_image" % BASE)
    @mock.patch("%s.CreateAndDeleteImage._create_image" % BASE)
    @mock.patch("%s.CreateAndDeleteImage.generate_random_name" % BASE,
                return_value="test-rally-image")
    def test_create_and_delete_image(self,
                                     mock_random_name,
                                     mock_create_image,
                                     mock_delete_image):
        fake_image = object()
        mock_create_image.return_value = fake_image

        images.CreateAndDeleteImage(self.context).run(
            "cf", "url", "df", fakearg="f")

        mock_create_image.assert_called_once_with(
            "cf", "url", "df", fakearg="f")
        mock_delete_image.assert_called_once_with(fake_image)

    @mock.patch("%s.CreateImageAndBootInstances._boot_servers" % BASE)
    @mock.patch("%s.CreateImageAndBootInstances._create_image" % BASE)
    def test_create_image_and_boot_instances(self,
                                             mock_create_image,
                                             mock_boot_servers):
        fake_image = fakes.FakeImage()
        fake_servers = [mock.Mock() for i in range(5)]
        mock_create_image.return_value = fake_image
        mock_boot_servers.return_value = fake_servers
        create_image_kwargs = {"fakeimagearg": "f"}
        boot_server_kwargs = {"fakeserverarg": "f"}

        images.CreateImageAndBootInstances(self.context).run(
            "cf", "url", "df", "fid", 5,
            create_image_kwargs=create_image_kwargs,
            boot_server_kwargs=boot_server_kwargs)
        mock_create_image.assert_called_once_with("cf", "url", "df",
                                                  **create_image_kwargs)
        mock_boot_servers.assert_called_once_with("image-id-0", "fid",
                                                  5, **boot_server_kwargs)
