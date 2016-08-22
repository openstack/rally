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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.glance import utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import types
from rally.task import validation


"""Scenarios for Glance images."""


@types.convert(image_location={"type": "path_or_url"})
@validation.required_services(consts.Service.GLANCE)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["glance"]},
                    name="GlanceImages.create_and_list_image")
class CreateAndListImage(utils.GlanceScenario, nova_utils.NovaScenario):

    def run(self, container_format, image_location, disk_format, **kwargs):
        """Create an image and then list all images.

        Measure the "glance image-list" command performance.

        If you have only 1 user in your context, you will
        add 1 image on every iteration. So you will have more
        and more images and will be able to measure the
        performance of the "glance image-list" command depending on
        the number of images owned by users.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param kwargs: optional parameters to create image
        """
        self._create_image(container_format,
                           image_location,
                           disk_format,
                           **kwargs)
        self._list_images()


@validation.required_services(consts.Service.GLANCE)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["glance"]},
                    name="GlanceImages.list_images")
class ListImages(utils.GlanceScenario, nova_utils.NovaScenario):

    def run(self):
        """List all images.

        This simple scenario tests the glance image-list command by listing
        all the images.

        Suppose if we have 2 users in context and each has 2 images
        uploaded for them we will be able to test the performance of
        glance image-list command in this case.
        """
        self._list_images()


@validation.required_services(consts.Service.GLANCE)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["glance"]},
                    name="GlanceImages.create_and_delete_image")
class CreateAndDeleteImage(utils.GlanceScenario, nova_utils.NovaScenario):

    def run(self, container_format, image_location, disk_format, **kwargs):
        """Create and then delete an image.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param kwargs: optional parameters to create image
        """
        image = self._create_image(container_format,
                                   image_location,
                                   disk_format,
                                   **kwargs)
        self._delete_image(image)


@types.convert(flavor={"type": "nova_flavor"})
@validation.flavor_exists("flavor")
@validation.required_services(consts.Service.GLANCE, consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["glance", "nova"]},
                    name="GlanceImages.create_image_and_boot_instances")
class CreateImageAndBootInstances(utils.GlanceScenario,
                                  nova_utils.NovaScenario):

    def run(self, container_format, image_location, disk_format,
            flavor, number_instances, **kwargs):
        """Create an image and boot several instances from it.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param flavor: Nova flavor to be used to launch an instance
        :param number_instances: number of Nova servers to boot
        :param kwargs: optional parameters to create server
        """
        image = self._create_image(container_format,
                                   image_location,
                                   disk_format)
        image_id = image.id
        self._boot_servers(image_id, flavor, number_instances, **kwargs)
