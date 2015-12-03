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

import inspect
import os
import uuid

from oslo_config import cfg
import requests
from six.moves import configparser
from six.moves.urllib import parse

from rally.common import db
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import objects
from rally.common import utils
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.wrappers import network

LOG = logging.getLogger(__name__)

IMAGE_OPTS = [
    cfg.StrOpt("cirros_img_url",
               default="http://download.cirros-cloud.net/"
                       "0.3.4/cirros-0.3.4-x86_64-disk.img",
               help="CirrOS image URL")
]

ROLE_OPTS = [
    cfg.StrOpt("swift_operator_role",
               default="Member",
               help="Role required for users "
                    "to be able to create Swift containers"),
    cfg.StrOpt("swift_reseller_admin_role",
               default="ResellerAdmin",
               help="User role that has reseller admin"),
    cfg.StrOpt("heat_stack_owner_role",
               default="heat_stack_owner",
               help="Role required for users "
                    "to be able to manage Heat stacks"),
    cfg.StrOpt("heat_stack_user_role",
               default="heat_stack_user",
               help="Role for Heat template-defined users")
]

CONF = cfg.CONF
CONF.register_opts(IMAGE_OPTS, "image")
CONF.register_opts(ROLE_OPTS, "role")

IMAGE_NAME = parse.urlparse(CONF.image.cirros_img_url).path.split("/")[-1]


def _create_or_get_data_dir():
    data_dir = os.path.join(
        os.path.expanduser("~"), ".rally", "tempest", "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    return data_dir


def _write_config(conf_path, conf_data):
    with open(conf_path, "w+") as conf_file:
        conf_data.write(conf_file)


class TempestConfig(utils.RandomNameGeneratorMixin):
    """Class to generate Tempest configuration file."""

    def __init__(self, deployment):
        self.deployment = deployment

        self.credential = db.deployment_get(deployment)["admin"]
        self.clients = osclients.Clients(objects.Credential(**self.credential))
        self.keystone = self.clients.verified_keystone()
        self.available_services = self.clients.services().values()

        self.data_dir = _create_or_get_data_dir()

        self.conf = configparser.ConfigParser()
        self.conf.read(os.path.join(os.path.dirname(__file__), "config.ini"))

        self._download_cirros_image()

    def _download_cirros_image(self):
        img_path = os.path.join(self.data_dir, IMAGE_NAME)
        if os.path.isfile(img_path):
            return

        try:
            response = requests.get(CONF.image.cirros_img_url, stream=True)
        except requests.ConnectionError as err:
            msg = _("Failed to download CirrOS image. "
                    "Possibly there is no connection to Internet. "
                    "Error: %s.") % (str(err) or "unknown")
            raise exceptions.TempestConfigCreationFailure(msg)

        if response.status_code == 200:
            with open(img_path + ".tmp", "wb") as img_file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:   # filter out keep-alive new chunks
                        img_file.write(chunk)
                        img_file.flush()
            os.rename(img_path + ".tmp", img_path)
        else:
            if response.status_code == 404:
                msg = _("Failed to download CirrOS image. "
                        "Image was not found.")
            else:
                msg = _("Failed to download CirrOS image. "
                        "HTTP error code %d.") % response.status_code
            raise exceptions.TempestConfigCreationFailure(msg)

    def _get_service_url(self, service_type):
        for service in self.keystone.auth_ref["serviceCatalog"]:
            if self.clients.services().get(service["type"]) == service_type:
                return service["endpoints"][0]["publicURL"]

    def _configure_boto(self, section_name="boto"):
        self.conf.set(section_name, "ec2_url", self._get_service_url("ec2"))
        self.conf.set(section_name, "s3_url", self._get_service_url("s3"))
        self.conf.set(section_name, "s3_materials_path",
                      os.path.join(self.data_dir, "s3materials"))
        # TODO(olkonami): find out how can we get ami, ari, aki manifest files

    def _configure_default(self, section_name="DEFAULT"):
        # Nothing to configure in this section for now
        pass

    def _configure_dashboard(self, section_name="dashboard"):
        url = "http://%s/" % parse.urlparse(
            self.credential["auth_url"]).hostname
        self.conf.set(section_name, "dashboard_url", url)

    def _configure_identity(self, section_name="identity"):
        self.conf.set(section_name, "username", self.credential["username"])
        self.conf.set(section_name, "password", self.credential["password"])
        self.conf.set(section_name, "tenant_name",
                      self.credential["tenant_name"])

        self.conf.set(section_name, "admin_username",
                      self.credential["username"])
        self.conf.set(section_name, "admin_password",
                      self.credential["password"])
        self.conf.set(section_name, "admin_tenant_name",
                      self.credential["tenant_name"])

        self.conf.set(section_name, "region",
                      self.credential["region_name"])

        self.conf.set(section_name, "uri", self.credential["auth_url"])
        v2_url_trailer = parse.urlparse(self.credential["auth_url"]).path
        self.conf.set(section_name, "uri_v3",
                      self.credential["auth_url"].replace(
                          v2_url_trailer, "/v3"))

        self.conf.set(section_name, "admin_domain_name",
                      self.credential["admin_domain_name"])

        self.conf.set(section_name, "disable_ssl_certificate_validation",
                      str(self.credential["https_insecure"]))
        self.conf.set(section_name, "ca_certificates_file",
                      self.credential["https_cacert"])

    # The compute section is configured in context class for Tempest resources.
    # Options which are configured there: 'image_ref', 'image_ref_alt',
    # 'flavor_ref', 'flavor_ref_alt'.

    def _configure_network(self, section_name="network"):
        if "neutron" in self.available_services:
            neutronclient = self.clients.neutron()
            public_nets = [net for net
                           in neutronclient.list_networks()["networks"]
                           if net["status"] == "ACTIVE" and
                           net["router:external"] is True]
            if public_nets:
                net_id = public_nets[0]["id"]
                self.conf.set(section_name, "public_network_id", net_id)
        else:
            novaclient = self.clients.nova()
            net_name = next(net.human_id for net in novaclient.networks.list()
                            if net.human_id is not None)
            self.conf.set("compute", "fixed_network_name", net_name)
            self.conf.set("compute", "network_for_ssh", net_name)

    def _configure_network_feature_enabled(
            self, section_name="network-feature-enabled"):
        if "neutron" in self.available_services:
            neutronclient = self.clients.neutron()
            ext_list = [ext["alias"] for ext in
                        neutronclient.list_ext("/extensions")["extensions"]]
            ext_list_str = ",".join(ext_list)
            self.conf.set(section_name, "api_extensions", ext_list_str)

    def _configure_oslo_concurrency(self, section_name="oslo_concurrency"):
        lock_path = os.path.join(self.data_dir,
                                 "lock_files_%s" % self.deployment)
        if not os.path.exists(lock_path):
            os.makedirs(lock_path)
        self.conf.set(section_name, "lock_path", lock_path)

    def _configure_object_storage(self, section_name="object-storage"):
        self.conf.set(section_name, "operator_role",
                      CONF.role.swift_operator_role)
        self.conf.set(section_name, "reseller_admin_role",
                      CONF.role.swift_reseller_admin_role)

    def _configure_scenario(self, section_name="scenario"):
        self.conf.set(section_name, "img_dir", self.data_dir)
        self.conf.set(section_name, "img_file", IMAGE_NAME)

    def _configure_service_available(self, section_name="service_available"):
        services = ["ceilometer", "cinder", "glance",
                    "heat", "neutron", "nova", "sahara", "swift"]
        for service in services:
            # Convert boolean to string because ConfigParser fails
            # on attempt to get option with boolean value
            self.conf.set(section_name, service,
                          str(service in self.available_services))
        horizon_url = ("http://" +
                       parse.urlparse(self.credential["auth_url"]).hostname)
        try:
            horizon_req = requests.get(
                horizon_url,
                timeout=CONF.openstack_client_http_timeout)
        except requests.RequestException as e:
            LOG.debug("Failed to connect to Horizon: %s" % e)
            horizon_availability = False
        else:
            horizon_availability = (horizon_req.status_code == 200)
        # Convert boolean to string because ConfigParser fails
        # on attempt to get option with boolean value
        self.conf.set(section_name, "horizon", str(horizon_availability))

    def _configure_validation(self, section_name="validation"):
        if "neutron" in self.available_services:
            self.conf.set(section_name, "connect_method", "floating")
        else:
            self.conf.set(section_name, "connect_method", "fixed")

    def _configure_orchestration(self, section_name="orchestration"):
        self.conf.set(section_name, "stack_owner_role",
                      CONF.role.heat_stack_owner_role)
        self.conf.set(section_name, "stack_user_role",
                      CONF.role.heat_stack_user_role)

    def generate(self, conf_path=None):
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith("_configure_"):
                method()

        if conf_path:
            _write_config(conf_path, self.conf)


class TempestResourcesContext(object):
    """Context class to create/delete resources needed for Tempest."""

    def __init__(self, deployment, conf_path):
        credential = db.deployment_get(deployment)["admin"]
        self.clients = osclients.Clients(objects.Credential(**credential))
        self.available_services = self.clients.services().values()

        self.conf_path = conf_path
        self.conf = configparser.ConfigParser()
        self.conf.read(conf_path)

        self._created_roles = []
        self._created_images = []
        self._created_flavors = []
        self._created_networks = []

    def __enter__(self):
        self._create_tempest_roles()
        self._configure_option("compute", "image_ref", self._create_image)
        self._configure_option("compute", "image_ref_alt", self._create_image)
        self._configure_option("compute",
                               "flavor_ref", self._create_flavor, 64)
        self._configure_option("compute",
                               "flavor_ref_alt", self._create_flavor, 128)
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
                          "'fixed_network_name' option should be configured")
                self._configure_option("compute", "fixed_network_name",
                                       self._create_network_resources)
        if "heat" in self.available_services:
            self._configure_option("orchestration", "instance_type",
                                   self._create_flavor, 64)

        _write_config(self.conf_path, self.conf)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # Tempest tests may take more than 1 hour and we should remove all
        # cached clients sessions to avoid tokens expiration when deleting
        # Tempest resources.
        self.clients.clear()

        self._cleanup_tempest_roles()
        self._cleanup_images()
        self._cleanup_flavors()
        if "neutron" in self.available_services:
            self._cleanup_network_resources()

        _write_config(self.conf_path, self.conf)

    def _create_tempest_roles(self):
        keystoneclient = self.clients.verified_keystone()
        roles = [CONF.role.swift_operator_role,
                 CONF.role.swift_reseller_admin_role,
                 CONF.role.heat_stack_owner_role,
                 CONF.role.heat_stack_user_role]
        existing_roles = set(role.name for role in keystoneclient.roles.list())

        for role in roles:
            if role not in existing_roles:
                LOG.debug("Creating role '%s'" % role)
                self._created_roles.append(keystoneclient.roles.create(role))

    def _configure_option(self, section, option,
                          create_method, *args, **kwargs):
        option_value = self.conf.get(section, option)
        if not option_value:
            LOG.debug("Option '%s' from '%s' section "
                      "is not configured" % (option, section))
            resource = create_method(*args, **kwargs)
            value = resource["name"] if "network" in option else resource.id
            LOG.debug("Setting value '%s' for option '%s'" % (value, option))
            self.conf.set(section, option, value)
            LOG.debug("Option '{opt}' is configured. "
                      "{opt} = {value}".format(opt=option, value=value))
        else:
            LOG.debug("Option '{opt}' was configured manually "
                      "in Tempest config file. {opt} = {opt_val}"
                      .format(opt=option, opt_val=option_value))

    def _create_image(self):
        glanceclient = self.clients.glance()
        params = {
            "name": "rally-verify-cirros-img-%s" % uuid.uuid4(),
            "disk_format": "qcow2",
            "container_format": "bare",
            "is_public": True
        }
        LOG.debug("Creating image '%s'" % params["name"])
        image = glanceclient.images.create(**params)
        self._created_images.append(image)
        image.update(data=open(
            os.path.join(_create_or_get_data_dir(), IMAGE_NAME), "rb"))

        return image

    def _create_flavor(self, flv_ram):
        novaclient = self.clients.nova()
        params = {
            "name": "m1.rally-verify-flv-%s" % uuid.uuid4(),
            "ram": flv_ram,
            "vcpus": 1,
            "disk": 0
        }
        LOG.debug("Creating flavor '%s'" % params["name"])
        flavor = novaclient.flavors.create(**params)
        self._created_flavors.append(flavor)

        return flavor

    def _create_network_resources(self):
        neutron_wrapper = network.NeutronWrapper(self.clients, self)
        LOG.debug("Creating network resources: network, subnet, router")
        net = neutron_wrapper.create_network(
            self.clients.keystone().tenant_id, subnets_num=1,
            add_router=True, network_create_args={"shared": True})
        self._created_networks.append(net)

        return net

    def _cleanup_tempest_roles(self):
        keystoneclient = self.clients.keystone()
        for role in self._created_roles:
            LOG.debug("Deleting role '%s'" % role.name)
            keystoneclient.roles.delete(role.id)

    def _cleanup_images(self):
        glanceclient = self.clients.glance()
        for image in self._created_images:
            LOG.debug("Deleting image '%s'" % image.name)
            glanceclient.images.delete(image.id)
            self._remove_opt_value_from_config("compute", image.id)

    def _cleanup_flavors(self):
        novaclient = self.clients.nova()
        for flavor in self._created_flavors:
            LOG.debug("Deleting flavor '%s'" % flavor.name)
            novaclient.flavors.delete(flavor.id)
            self._remove_opt_value_from_config("compute", flavor.id)
            self._remove_opt_value_from_config("orchestration", flavor.id)

    def _cleanup_network_resources(self):
        neutron_wrapper = network.NeutronWrapper(self.clients, self)
        for net in self._created_networks:
            LOG.debug("Deleting network resources: router, subnet, network")
            neutron_wrapper.delete_network(net)
            self._remove_opt_value_from_config("compute", net["name"])

    def _remove_opt_value_from_config(self, section, opt_value):
        for option, value in self.conf.items(section):
            if opt_value == value:
                LOG.debug("Removing value '%s' for option '%s' "
                          "from Tempest config file" % (opt_value, option))
                self.conf.set(section, option, "")
