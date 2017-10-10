# Copyright 2017: Mirantis Inc.
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

import os
import re

import requests
from six.moves import configparser

from rally.common import logging
from rally import exceptions
from rally.plugins.openstack.services.image import image
from rally.plugins.openstack.verification.tempest import config as conf
from rally.plugins.openstack.wrappers import network
from rally.task import utils as task_utils
from rally.verification import context
from rally.verification import utils


LOG = logging.getLogger(__name__)


@context.configure("tempest", order=900)
class TempestContext(context.VerifierContext):
    """Context class to create/delete resources needed for Tempest."""

    RESOURCE_NAME_FORMAT = "rally_verify_XXXXXXXX_XXXXXXXX"

    def __init__(self, ctx):
        super(TempestContext, self).__init__(ctx)

        creds = self.verifier.deployment.get_credentials_for("openstack")
        self.clients = creds["admin"].clients()
        self.available_services = self.clients.services().values()

        self.conf = configparser.ConfigParser()
        self.conf_path = self.verifier.manager.configfile

        self.data_dir = self.verifier.manager.home_dir
        self.image_name = "tempest-image"

        self._created_roles = []
        self._created_images = []
        self._created_flavors = []
        self._created_networks = []

    def setup(self):
        self.conf.read(self.conf_path)

        utils.create_dir(self.data_dir)

        self._create_tempest_roles()

        self._configure_option("DEFAULT", "log_file",
                               os.path.join(self.data_dir, "tempest.log"))
        self._configure_option("oslo_concurrency", "lock_path",
                               os.path.join(self.data_dir, "lock_files"))
        self._configure_option("scenario", "img_dir", self.data_dir)
        self._configure_option("scenario", "img_file", self.image_name,
                               helper_method=self._download_image)
        self._configure_option("compute", "image_ref",
                               helper_method=self._discover_or_create_image)
        self._configure_option("compute", "image_ref_alt",
                               helper_method=self._discover_or_create_image)
        self._configure_option("compute", "flavor_ref",
                               helper_method=self._discover_or_create_flavor,
                               flv_ram=conf.CONF.openstack.flavor_ref_ram)
        self._configure_option("compute", "flavor_ref_alt",
                               helper_method=self._discover_or_create_flavor,
                               flv_ram=conf.CONF.openstack.flavor_ref_alt_ram)
        if "neutron" in self.available_services:
            neutronclient = self.clients.neutron()
            if neutronclient.list_networks(shared=True)["networks"]:
                # If the OpenStack cloud has some shared networks, we will
                # create our own shared network and specify its name in the
                # Tempest config file. Such approach will allow us to avoid
                # failures of Tempest tests with error "Multiple possible
                # networks found". Otherwise the default behavior defined in
                # Tempest will be used and Tempest itself will manage network
                # resources.
                LOG.debug("Shared networks found. "
                          "'fixed_network_name' option should be configured.")
                self._configure_option(
                    "compute", "fixed_network_name",
                    helper_method=self._create_network_resources)
        if "heat" in self.available_services:
            self._configure_option(
                "orchestration", "instance_type",
                helper_method=self._discover_or_create_flavor,
                flv_ram=conf.CONF.openstack.heat_instance_type_ram)

        with open(self.conf_path, "w") as configfile:
            self.conf.write(configfile)

    def cleanup(self):
        # Tempest tests may take more than 1 hour and we should remove all
        # cached clients sessions to avoid tokens expiration when deleting
        # Tempest resources.
        self.clients.clear()

        self._cleanup_tempest_roles()
        self._cleanup_images()
        self._cleanup_flavors()
        if "neutron" in self.available_services:
            self._cleanup_network_resources()

        with open(self.conf_path, "w") as configfile:
            self.conf.write(configfile)

    def _create_tempest_roles(self):
        keystoneclient = self.clients.verified_keystone()
        roles = [conf.CONF.openstack.swift_operator_role,
                 conf.CONF.openstack.swift_reseller_admin_role,
                 conf.CONF.openstack.heat_stack_owner_role,
                 conf.CONF.openstack.heat_stack_user_role]
        existing_roles = set(role.name for role in keystoneclient.roles.list())

        for role in roles:
            if role not in existing_roles:
                LOG.debug("Creating role '%s'." % role)
                self._created_roles.append(keystoneclient.roles.create(role))

    def _configure_option(self, section, option, value=None,
                          helper_method=None, *args, **kwargs):
        option_value = self.conf.get(section, option)
        if not option_value:
            LOG.debug("Option '%s' from '%s' section is not configured."
                      % (option, section))
            if helper_method:
                res = helper_method(*args, **kwargs)
                if res:
                    value = res["name"] if "network" in option else res.id
            LOG.debug("Setting value '%s' to option '%s'." % (value, option))
            self.conf.set(section, option, value)
            LOG.debug("Option '{opt}' is configured. "
                      "{opt} = {value}".format(opt=option, value=value))
        else:
            LOG.debug("Option '{opt}' is already configured "
                      "in Tempest config file. {opt} = {opt_val}"
                      .format(opt=option, opt_val=option_value))

    def _discover_image(self):
        LOG.debug("Trying to discover a public image with name matching "
                  "regular expression '%s'. Note that case insensitive "
                  "matching is performed."
                  % conf.CONF.openstack.img_name_regex)
        image_service = image.Image(self.clients)
        images = image_service.list_images(status="active",
                                           visibility="public")
        for image_obj in images:
            if image_obj.name and re.match(conf.CONF.openstack.img_name_regex,
                                           image_obj.name, re.IGNORECASE):
                LOG.debug("The following public image discovered: '%s'."
                          % image_obj.name)
                return image_obj

        LOG.debug("There is no public image with name matching regular "
                  "expression '%s'." % conf.CONF.openstack.img_name_regex)

    def _download_image_from_source(self, target_path, image=None):
        if image:
            LOG.debug("Downloading image '%s' from Glance to %s."
                      % (image.name, target_path))
            with open(target_path, "wb") as image_file:
                for chunk in self.clients.glance().images.data(image.id):
                    image_file.write(chunk)
        else:
            LOG.debug("Downloading image from %s to %s."
                      % (conf.CONF.openstack.img_url, target_path))
            try:
                response = requests.get(conf.CONF.openstack.img_url,
                                        stream=True)
            except requests.ConnectionError as err:
                msg = ("Failed to download image. Possibly there is no "
                       "connection to Internet. Error: %s."
                       % (str(err) or "unknown"))
                raise exceptions.RallyException(msg)

            if response.status_code == 200:
                with open(target_path, "wb") as image_file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:   # filter out keep-alive new chunks
                            image_file.write(chunk)
                            image_file.flush()
            else:
                if response.status_code == 404:
                    msg = "Failed to download image. Image was not found."
                else:
                    msg = ("Failed to download image. HTTP error code %d."
                           % response.status_code)
                raise exceptions.RallyException(msg)

        LOG.debug("The image has been successfully downloaded!")

    def _download_image(self):
        image_path = os.path.join(self.data_dir, self.image_name)
        if os.path.isfile(image_path):
            LOG.debug("Image is already downloaded to %s." % image_path)
            return

        if conf.CONF.openstack.img_name_regex:
            image = self._discover_image()
            if image:
                return self._download_image_from_source(image_path, image)

        self._download_image_from_source(image_path)

    def _discover_or_create_image(self):
        if conf.CONF.openstack.img_name_regex:
            image_obj = self._discover_image()
            if image_obj:
                LOG.debug("Using image '%s' (ID = %s) for the tests."
                          % (image_obj.name, image_obj.id))
                return image_obj

        params = {
            "image_name": self.generate_random_name(),
            "disk_format": conf.CONF.openstack.img_disk_format,
            "container_format": conf.CONF.openstack.img_container_format,
            "image_location": os.path.join(self.data_dir, self.image_name),
            "visibility": "public"
        }
        LOG.debug("Creating image '%s'." % params["image_name"])
        image_service = image.Image(self.clients)
        image_obj = image_service.create_image(**params)
        LOG.debug("Image '%s' (ID = %s) has been successfully created!"
                  % (image_obj.name, image_obj.id))
        self._created_images.append(image_obj)

        return image_obj

    def _discover_or_create_flavor(self, flv_ram):
        novaclient = self.clients.nova()

        LOG.debug("Trying to discover a flavor with the following "
                  "properties: RAM = %dMB, VCPUs = 1, disk = 0GB." % flv_ram)
        for flavor in novaclient.flavors.list():
            if (flavor.ram == flv_ram and
                    flavor.vcpus == 1 and flavor.disk == 0):
                LOG.debug("The following flavor discovered: '{0}'. "
                          "Using flavor '{0}' (ID = {1}) for the tests."
                          .format(flavor.name, flavor.id))
                return flavor

        LOG.debug("There is no flavor with the mentioned properties.")

        params = {
            "name": self.generate_random_name(),
            "ram": flv_ram,
            "vcpus": 1,
            "disk": 0
        }
        LOG.debug("Creating flavor '%s' with the following properties: RAM "
                  "= %dMB, VCPUs = 1, disk = 0GB." % (params["name"], flv_ram))
        flavor = novaclient.flavors.create(**params)
        LOG.debug("Flavor '%s' (ID = %s) has been successfully created!"
                  % (flavor.name, flavor.id))
        self._created_flavors.append(flavor)

        return flavor

    def _create_network_resources(self):
        neutron_wrapper = network.NeutronWrapper(self.clients, self)
        tenant_id = self.clients.keystone.auth_ref.project_id
        LOG.debug("Creating network resources: network, subnet, router.")
        net = neutron_wrapper.create_network(
            tenant_id, subnets_num=1, add_router=True,
            network_create_args={"shared": True})
        LOG.debug("Network resources have been successfully created!")
        self._created_networks.append(net)

        return net

    def _cleanup_tempest_roles(self):
        keystoneclient = self.clients.keystone()
        for role in self._created_roles:
            LOG.debug("Deleting role '%s'." % role.name)
            keystoneclient.roles.delete(role.id)
            LOG.debug("Role '%s' has been deleted." % role.name)

    def _cleanup_images(self):
        image_service = image.Image(self.clients)
        for image_obj in self._created_images:
            LOG.debug("Deleting image '%s'." % image_obj.name)
            self.clients.glance().images.delete(image_obj.id)
            task_utils.wait_for_status(
                image_obj, ["deleted", "pending_delete"],
                check_deletion=True,
                update_resource=image_service.get_image,
                timeout=conf.CONF.openstack.glance_image_delete_timeout,
                check_interval=conf.CONF.openstack.
                glance_image_delete_poll_interval)
            LOG.debug("Image '%s' has been deleted." % image_obj.name)
            self._remove_opt_value_from_config("compute", image_obj.id)

    def _cleanup_flavors(self):
        novaclient = self.clients.nova()
        for flavor in self._created_flavors:
            LOG.debug("Deleting flavor '%s'." % flavor.name)
            novaclient.flavors.delete(flavor.id)
            LOG.debug("Flavor '%s' has been deleted." % flavor.name)
            self._remove_opt_value_from_config("compute", flavor.id)
            self._remove_opt_value_from_config("orchestration", flavor.id)

    def _cleanup_network_resources(self):
        neutron_wrapper = network.NeutronWrapper(self.clients, self)
        for net in self._created_networks:
            LOG.debug("Deleting network resources: router, subnet, network.")
            neutron_wrapper.delete_network(net)
            self._remove_opt_value_from_config("compute", net["name"])
            LOG.debug("Network resources have been deleted.")

    def _remove_opt_value_from_config(self, section, opt_value):
        for option, value in self.conf.items(section):
            if opt_value == value:
                LOG.debug("Removing value '%s' of option '%s' "
                          "from Tempest config file." % (opt_value, option))
                self.conf.set(section, option, "")
                LOG.debug("Value '%s' has been removed." % opt_value)
