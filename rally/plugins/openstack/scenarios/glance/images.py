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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.services.image import glance_v2
from rally.plugins.openstack.services.image import image
from rally.task import types
from rally.task import validation

LOG = logging.getLogger(__name__)

"""Scenarios for Glance images."""


class GlanceBasic(scenario.OpenStackScenario):
    def __init__(self, context=None, admin_clients=None, clients=None):
        super(GlanceBasic, self).__init__(context, admin_clients, clients)
        if hasattr(self, "_admin_clients"):
            self.admin_glance = image.Image(
                self._admin_clients, name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())
        if hasattr(self, "_clients"):
            self.glance = image.Image(
                self._clients, name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())


@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@types.convert(image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance"]},
                    name="GlanceImages.create_and_list_image",
                    platform="openstack")
class CreateAndListImage(GlanceBasic):

    def run(self, container_format, image_location, disk_format,
            visibility="private", min_disk=0, min_ram=0, properties=None):
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
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: A dict of image metadata properties to set
                           on the image
        """
        image = self.glance.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)
        self.assertTrue(image)
        image_list = self.glance.list_images()
        self.assertIn(image.id, [i.id for i in image_list])


@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@types.convert(image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance"]},
                    name="GlanceImages.create_and_get_image",
                    platform="openstack")
class CreateAndGetImage(GlanceBasic):

    def run(self, container_format, image_location, disk_format,
            visibility="private", min_disk=0, min_ram=0, properties=None):
        """Create and get detailed information of an image.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: A dict of image metadata properties to set
                           on the image
        """
        image = self.glance.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)
        self.assertTrue(image)
        image_info = self.glance.get_image(image)
        self.assertEqual(image.id, image_info.id)


@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="GlanceImages.list_images",
                    platform="openstack")
class ListImages(GlanceBasic):

    def run(self):
        """List all images.

        This simple scenario tests the glance image-list command by listing
        all the images.

        Suppose if we have 2 users in context and each has 2 images
        uploaded for them we will be able to test the performance of
        glance image-list command in this case.
        """
        self.glance.list_images()


@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@types.convert(image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance"]},
                    name="GlanceImages.create_and_delete_image",
                    platform="openstack")
class CreateAndDeleteImage(GlanceBasic):

    def run(self, container_format, image_location, disk_format,
            visibility="private", min_disk=0, min_ram=0, properties=None):
        """Create and then delete an image.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: A dict of image metadata properties to set
                           on the image
        """
        image = self.glance.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)
        self.glance.delete_image(image.id)


@types.convert(flavor={"type": "nova_flavor"},
               image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@validation.add("restricted_parameters", param_names=["image_name", "name"])
@validation.add("flavor_exists", param_name="flavor")
@validation.add("required_services", services=[consts.Service.GLANCE,
                                               consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance", "nova"]},
                    name="GlanceImages.create_image_and_boot_instances",
                    platform="openstack")
class CreateImageAndBootInstances(GlanceBasic, nova_utils.NovaScenario):

    def run(self, container_format, image_location, disk_format,
            flavor, number_instances, visibility="private", min_disk=0,
            min_ram=0, properties=None, boot_server_kwargs=None, **kwargs):
        """Create an image and boot several instances from it.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: A dict of image metadata properties to set
                           on the image
        :param flavor: Nova flavor to be used to launch an instance
        :param number_instances: number of Nova servers to boot
        :param boot_server_kwargs: optional parameters to boot server
        :param kwargs: optional parameters to create server (deprecated)
        """
        boot_server_kwargs = boot_server_kwargs or kwargs or {}

        if kwargs:
            LOG.warning("'kwargs' is deprecated in Rally v0.8.0: Use "
                        "'boot_server_kwargs' for additional parameters when "
                        "booting servers.")

        image = self.glance.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)

        self._boot_servers(image.id, flavor, number_instances,
                           **boot_server_kwargs)


@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@types.convert(image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance"]},
                    name="GlanceImages.create_and_update_image",
                    platform="openstack")
class CreateAndUpdateImage(GlanceBasic):

    def run(self, container_format, image_location, disk_format,
            remove_props=None, visibility="private", create_min_disk=0,
            create_min_ram=0, create_properties=None,
            update_min_disk=0, update_min_ram=0):
        """Create an image then update it.

        Measure the "glance image-create" and "glance image-update" commands
        performance.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param remove_props: List of property names to remove.
                             (It is only supported by Glance v2.)
        :param visibility: The access permission for the created image
        :param create_min_disk: The min disk of created images
        :param create_min_ram: The min ram of created images
        :param create_properties: A dict of image metadata properties to set
                                  on the created image
        :param update_min_disk: The min disk of updated images
        :param update_min_ram: The min ram of updated images
        """
        image = self.glance.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=create_min_disk,
            min_ram=create_min_ram,
            properties=create_properties)

        self.glance.update_image(image.id,
                                 min_disk=update_min_disk,
                                 min_ram=update_min_ram,
                                 remove_props=remove_props)


@validation.add("required_services", services=(consts.Service.GLANCE, ))
@validation.add("required_platform", platform="openstack", users=True)
@validation.add("required_api_versions", component="glance", versions=["2"])
@scenario.configure(context={"cleanup@openstack": ["glance"]},
                    name="GlanceImages.create_and_deactivate_image",
                    platform="openstack")
class CreateAndDeactivateImage(GlanceBasic):
    def run(self, container_format, image_location, disk_format,
            visibility="private", min_disk=0, min_ram=0):
        """Create an image, then deactivate it.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        """
        service = glance_v2.GlanceV2Service(self._clients,
                                            self.generate_random_name,
                                            atomic_inst=self.atomic_actions())

        image = service.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram)
        service.deactivate_image(image.id)


@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@types.convert(image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance"]},
                    name="GlanceImages.create_and_download_image",
                    platform="openstack")
class CreateAndDownloadImage(GlanceBasic):

    def run(self, container_format, image_location, disk_format,
            visibility="private", min_disk=0, min_ram=0, properties=None):
        """Create an image, then download data of the image.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param properties: A dict of image metadata properties to set
                           on the image
        """
        image = self.glance.create_image(
            container_format=container_format,
            image_location=image_location,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram,
            properties=properties)

        self.glance.download_image(image.id)
