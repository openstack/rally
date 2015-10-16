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

GLANCE_IMAGES = "rally.plugins.openstack.scenarios.glance.images.GlanceImages"


class GlanceImagesTestCase(test.ScenarioTestCase):

    @mock.patch(GLANCE_IMAGES + ".generate_random_name")
    @mock.patch(GLANCE_IMAGES + "._list_images")
    @mock.patch(GLANCE_IMAGES + "._create_image")
    def test_create_and_list_image(self, mock__create_image,
                                   mock__list_images,
                                   mock_generate_random_name):
        glance_scenario = images.GlanceImages(self.context)
        mock_generate_random_name.return_value = "test-rally-image"
        glance_scenario.create_and_list_image("cf", "url", "df",
                                              fakearg="f")
        mock__create_image.assert_called_once_with(
            "cf", "url", "df", fakearg="f")
        mock__list_images.assert_called_once_with()

    @mock.patch(GLANCE_IMAGES + "._list_images")
    def test_list_images(self, mock__list_images):
        glance_scenario = images.GlanceImages(self.context)
        glance_scenario.list_images()
        mock__list_images.assert_called_once_with()

    @mock.patch(GLANCE_IMAGES + ".generate_random_name")
    @mock.patch(GLANCE_IMAGES + "._delete_image")
    @mock.patch(GLANCE_IMAGES + "._create_image")
    def test_create_and_delete_image(
            self, mock__create_image, mock__delete_image,
            mock_generate_random_name):
        glance_scenario = images.GlanceImages(self.context)
        fake_image = object()
        mock__create_image.return_value = fake_image
        mock_generate_random_name.return_value = "test-rally-image"
        glance_scenario.create_and_delete_image("cf", "url", "df",
                                                fakearg="f")

        mock__create_image.assert_called_once_with(
            "cf", "url", "df", fakearg="f")
        mock__delete_image.assert_called_once_with(fake_image)

    @mock.patch(GLANCE_IMAGES + "._boot_servers")
    @mock.patch(GLANCE_IMAGES + "._create_image")
    def test_create_image_and_boot_instances(
            self, mock__create_image, mock__boot_servers):
        glance_scenario = images.GlanceImages(self.context)
        fake_image = fakes.FakeImage()
        fake_servers = [mock.Mock() for i in range(5)]
        mock__create_image.return_value = fake_image
        mock__boot_servers.return_value = fake_servers
        kwargs = {"fakearg": "f"}

        glance_scenario.create_image_and_boot_instances("cf", "url",
                                                        "df", "fid",
                                                        5, **kwargs)
        mock__create_image.assert_called_once_with(
            "cf", "url", "df")
        mock__boot_servers.assert_called_once_with(
            "image-id-0", "fid", 5, **kwargs)
