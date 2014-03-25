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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.glance import utils
from rally.benchmark.scenarios.nova import utils as nova_utils
from rally.benchmark import validation


class GlanceImages(utils.GlanceScenario, nova_utils.NovaScenario):

    @base.scenario
    def create_and_list_image(self, container_format,
                              image_location, disk_format, **kwargs):
        """Test adding an image and then listing all images.

        This scenario is a very useful tool to measure
        the "glance image-list" command performance.

        If you have only 1 user in your context, you will
        add 1 image on every iteration. So you will have more
        and more images and will be able to measure the
        performance of the "glance image-list" command depending on
        the number of images owned by users.
        """

        image_name = self._generate_random_name(16)
        self._create_image(image_name,
                           container_format,
                           image_location,
                           disk_format,
                           **kwargs)
        self._list_images()

    @base.scenario
    def create_and_delete_image(self, container_format,
                                image_location, disk_format, **kwargs):
        """Test adds and then deletes image."""
        image_name = self._generate_random_name(16)
        image = self._create_image(image_name,
                                   container_format,
                                   image_location,
                                   disk_format,
                                   **kwargs)
        self._delete_image(image)

    @validation.add_validator(validation.flavor_exists("flavor_id"))
    @base.scenario
    def create_image_and_boot_instances(self, container_format,
                                        image_location, disk_format,
                                        flavor_id, number_instances,
                                        **kwargs):
        """Test adds image, boots instance from it and then deletes them."""
        image_name = self._generate_random_name(16)
        image = self._create_image(image_name,
                                   container_format,
                                   image_location,
                                   disk_format,
                                   **kwargs)
        image_id = image.id
        server_name = self._generate_random_name(16)
        self._boot_servers(server_name, image_id,
                           flavor_id, number_instances, **kwargs)
