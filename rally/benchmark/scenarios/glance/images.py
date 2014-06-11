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
from rally.benchmark import types as types
from rally.benchmark import validation


class GlanceImages(utils.GlanceScenario, nova_utils.NovaScenario):

    RESOURCE_NAME_PREFIX = "rally_image_"
    RESOURCE_NAME_LENGTH = 16

    @base.scenario(context={"cleanup": ["glance"]})
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
        self._create_image(self._generate_random_name(),
                           container_format,
                           image_location,
                           disk_format,
                           **kwargs)
        self._list_images()

    @base.scenario(context={"cleanup": ["glance"]})
    def create_and_delete_image(self, container_format,
                                image_location, disk_format, **kwargs):
        """Test adds and then deletes image."""
        image_name = self._generate_random_name()
        image = self._create_image(image_name,
                                   container_format,
                                   image_location,
                                   disk_format,
                                   **kwargs)
        self._delete_image(image)

    @types.set(flavor=types.FlavorResourceType)
    @validation.add(validation.flavor_exists("flavor"))
    @base.scenario(context={"cleanup": ["glance", "nova"]})
    def create_image_and_boot_instances(self, container_format,
                                        image_location, disk_format,
                                        flavor, number_instances,
                                        **kwargs):
        """Test adds image, boots instance from it and then deletes them."""
        image_name = self._generate_random_name()
        image = self._create_image(image_name,
                                   container_format,
                                   image_location,
                                   disk_format,
                                   **kwargs)
        image_id = image.id
        server_name = self._generate_random_name(prefix="rally_novaserver_")
        self._boot_servers(server_name, image_id,
                           flavor, number_instances, **kwargs)
