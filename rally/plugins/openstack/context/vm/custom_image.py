# Copyright 2015: Mirantis Inc.
# All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import abc

import six

from rally.common import broker
from rally.common import logging
from rally.common import utils
from rally import consts
from rally.plugins.openstack import osclients
from rally.plugins.openstack.scenarios.vm import vmtasks
from rally.plugins.openstack.services.image import image
from rally.plugins.openstack import types
from rally.task import context

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseCustomImageGenerator(context.Context):
    """Base plugin for the contexts providing customized image with.

    Every context plugin for the specific customization must implement
    the method `_customize_image` that is able to connect to the server
    using SSH and install applications inside it.

    This base context plugin provides a way to prepare an image with
    custom preinstalled applications. Basically, this code boots a VM, calls
    the `_customize_image` and then snapshots the VM disk, removing the VM
    afterwards. The image UUID is stored in the user["custom_image"]["id"]
    and can be used afterwards by scenario.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                },
                "additionalProperties": False
            },
            "flavor": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                },
                "additionalProperties": False
            },
            "username": {
                "type": "string"
            },
            "password": {
                "type": "string"
            },
            "floating_network": {
                "type": "string"
            },
            "internal_network": {
                "type": "string"
            },
            "port": {
                "type": "integer",
                "minimum": 1,
                "maximum": 65535
            },
            "userdata": {
                "type": "string"
            },
            "workers": {
                "type": "integer",
                "minimum": 1,
            }
        },
        "required": ["image", "flavor"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "username": "root",
        "port": 22,
        "workers": 1
    }

    def setup(self):
        """Creates custom image(s) with preinstalled applications.

        When admin is present creates one public image that is usable
        from all the tenants and users. Otherwise create one image
        per user and tenant.
        """

        if "admin" in self.context:
            if self.context["users"]:
                # NOTE(pboldin): Create by first user and make it public by
                #                the admin
                user = self.context["users"][0]
            else:
                user = self.context["admin"]
            tenant = self.context["tenants"][user["tenant_id"]]

            nics = None
            if "networks" in tenant:
                nics = [{"net-id": tenant["networks"][0]["id"]}]

            custom_image = self.create_one_image(user, nics=nics)
            glance_service = image.Image(
                self.context["admin"]["credential"].clients())
            glance_service.set_visibility(custom_image.id)

            for tenant in self.context["tenants"].values():
                tenant["custom_image"] = custom_image
        else:
            def publish(queue):
                users = self.context.get("users", [])
                for user, tenant_id in utils.iterate_per_tenants(users):
                    queue.append((user, tenant_id))

            def consume(cache, args):
                user, tenant_id = args
                tenant = self.context["tenants"][tenant_id]
                tenant["custom_image"] = self.create_one_image(user)

            broker.run(publish, consume, self.config["workers"])

    def create_one_image(self, user, **kwargs):
        """Create one image for the user."""

        clients = osclients.Clients(user["credential"])

        image_id = types.GlanceImage(self.context).pre_process(
            resource_spec=self.config["image"], config={})
        flavor_id = types.Flavor(self.context).pre_process(
            resource_spec=self.config["flavor"], config={})

        vm_scenario = vmtasks.BootRuncommandDelete(self.context,
                                                   clients=clients)

        server, fip = vm_scenario._boot_server_with_fip(
            image=image_id, flavor=flavor_id,
            floating_network=self.config.get("floating_network"),
            userdata=self.config.get("userdata"),
            key_name=user["keypair"]["name"],
            security_groups=[user["secgroup"]["name"]],
            **kwargs)

        try:
            LOG.debug("Installing tools on %r %s" % (server, fip["ip"]))
            self.customize_image(server, fip, user)

            LOG.debug("Stopping server %r" % server)
            vm_scenario._stop_server(server)

            LOG.debug("Creating snapshot for %r" % server)
            custom_image = vm_scenario._create_image(server)
        finally:
            vm_scenario._delete_server_with_fip(server, fip)

        return custom_image

    def cleanup(self):
        """Delete created custom image(s)."""

        if "admin" in self.context:
            user = self.context["users"][0]
            tenant = self.context["tenants"][user["tenant_id"]]
            if "custom_image" in tenant:
                self.delete_one_image(user, tenant["custom_image"])
                tenant.pop("custom_image")
        else:
            def publish(queue):
                users = self.context.get("users", [])
                for user, tenant_id in utils.iterate_per_tenants(users):
                    queue.append((user, tenant_id))

            def consume(cache, args):
                user, tenant_id = args
                tenant = self.context["tenants"][tenant_id]
                if "custom_image" in tenant:
                    self.delete_one_image(user, tenant["custom_image"])
                    tenant.pop("custom_image")

            broker.run(publish, consume, self.config["workers"])

    def delete_one_image(self, user, custom_image):
        """Delete the image created for the user and tenant."""

        with logging.ExceptionLogger(
                LOG, "Unable to delete image %s" % custom_image.id):

            glance_service = image.Image(user["credential"].clients())
            glance_service.delete_image(custom_image.id)

    @logging.log_task_wrapper(LOG.info, "Custom image context: customizing")
    def customize_image(self, server, ip, user):
        return self._customize_image(server, ip, user)

    @abc.abstractmethod
    def _customize_image(self, server, ip, user):
        """Override this method with one that customizes image.

        Basically, code can simply call `VMScenario._run_command` function
        specifying an installation script and interpreter. This script will
        be then executed using SSH.

        :param server: nova.Server instance
        :param ip: dict with server IP details
        :param user: user who started a VM instance. Used to extract keypair
        """
        pass
