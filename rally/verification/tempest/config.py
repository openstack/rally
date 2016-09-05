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

from distutils import version
import inspect
import os
import re

from neutronclient import version as nc_version
from oslo_config import cfg
import requests
import six
from six.moves import configparser
from six.moves.urllib import parse

from rally.common import db
from rally.common.i18n import _
from rally.common import logging
from rally.common import objects
from rally.common import utils
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.wrappers import glance
from rally.plugins.openstack.wrappers import network
from rally.task import utils as task_utils

LOG = logging.getLogger(__name__)

TEMPEST_OPTS = [
    cfg.StrOpt("img_url",
               deprecated_opts=[cfg.DeprecatedOpt("cirros_img_url",
                                                  group="image")],
               default="http://download.cirros-cloud.net/"
                       "0.3.4/cirros-0.3.4-x86_64-disk.img",
               help="image URL"),
    cfg.StrOpt("img_disk_format",
               deprecated_opts=[cfg.DeprecatedOpt("disk_format",
                                                  group="image")],
               default="qcow2",
               help="Image disk format to use when creating the image"),
    cfg.StrOpt("img_container_format",
               deprecated_opts=[cfg.DeprecatedOpt("container_format",
                                                  group="image")],
               default="bare",
               help="Image container format to use when creating the image"),
    cfg.StrOpt("img_name_regex",
               deprecated_opts=[cfg.DeprecatedOpt("name_regex",
                                                  group="image")],
               default="^.*(cirros|testvm).*$",
               help="Regular expression for name of a public image to "
                    "discover it in the cloud and use it for the tests. "
                    "Note that when Rally is searching for the image, case "
                    "insensitive matching is performed. Specify nothing "
                    "('img_name_regex =') if you want to disable discovering. "
                    "In this case Rally will create needed resources by "
                    "itself if the values for the corresponding config "
                    "options are not specified in the Tempest config file"),
    cfg.StrOpt("swift_operator_role",
               deprecated_group="role",
               default="Member",
               help="Role required for users "
                    "to be able to create Swift containers"),
    cfg.StrOpt("swift_reseller_admin_role",
               deprecated_group="role",
               default="ResellerAdmin",
               help="User role that has reseller admin"),
    cfg.StrOpt("heat_stack_owner_role",
               deprecated_group="role",
               default="heat_stack_owner",
               help="Role required for users "
                    "to be able to manage Heat stacks"),
    cfg.StrOpt("heat_stack_user_role",
               deprecated_group="role",
               default="heat_stack_user",
               help="Role for Heat template-defined users"),
    cfg.IntOpt("flavor_ref_ram",
               default="64",
               help="Primary flavor RAM size used by most of the test cases"),
    cfg.IntOpt("flavor_ref_alt_ram",
               default="128",
               help="Alternate reference flavor RAM size used by test that"
               "need two flavors, like those that resize an instance"),
    cfg.IntOpt("heat_instance_type_ram",
               default="64",
               help="RAM size flavor used for orchestration test cases")
]

CONF = cfg.CONF
CONF.register_opts(TEMPEST_OPTS, "tempest")
CONF.import_opt("glance_image_delete_timeout",
                "rally.plugins.openstack.scenarios.glance.utils",
                "benchmark")
CONF.import_opt("glance_image_delete_poll_interval",
                "rally.plugins.openstack.scenarios.glance.utils",
                "benchmark")


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

        self.image_name = parse.urlparse(
            CONF.tempest.img_url).path.split("/")[-1]
        self._download_image()

    def _download_image(self):
        img_path = os.path.join(self.data_dir, self.image_name)
        if os.path.isfile(img_path):
            return

        try:
            response = requests.get(CONF.tempest.img_url, stream=True)
        except requests.ConnectionError as err:
            msg = _("Failed to download image. "
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
                msg = _("Failed to download image. "
                        "Image was not found.")
            else:
                msg = _("Failed to download image. "
                        "HTTP error code %d.") % response.status_code
            raise exceptions.TempestConfigCreationFailure(msg)

    def _get_service_url(self, service_name):
        s_type = self._get_service_type_by_service_name(service_name)
        available_endpoints = self.keystone.service_catalog.get_endpoints()
        service_endpoints = available_endpoints.get(s_type, [])
        for endpoint in service_endpoints:
            # If endpoints were returned by Keystone API V2
            if "publicURL" in endpoint:
                return endpoint["publicURL"]
            # If endpoints were returned by Keystone API V3
            if endpoint["interface"] == "public":
                return endpoint["url"]

    def _get_service_type_by_service_name(self, service_name):
        for s_type, s_name in six.iteritems(self.clients.services()):
            if s_name == service_name:
                return s_type

    def _configure_auth(self, section_name="auth"):
        self.conf.set(section_name, "admin_username",
                      self.credential["username"])
        self.conf.set(section_name, "admin_password",
                      self.credential["password"])
        self.conf.set(section_name, "admin_project_name",
                      self.credential["tenant_name"])
        self.conf.set(section_name, "admin_domain_name",
                      self.credential["admin_domain_name"])

    # Sahara has two service types: 'data_processing' and 'data-processing'.
    # 'data_processing' is deprecated, but it can be used in previous OpenStack
    # releases. So we need to configure the 'catalog_type' option to support
    # environments where 'data_processing' is used as service type for Sahara.
    def _configure_data_processing(self, section_name="data-processing"):
        if "sahara" in self.available_services:
            self.conf.set(section_name, "catalog_type",
                          self._get_service_type_by_service_name("sahara"))

    def _configure_identity(self, section_name="identity"):
        self.conf.set(section_name, "region",
                      self.credential["region_name"])

        auth_url = self.credential["auth_url"]
        if "/v2" not in auth_url and "/v3" not in auth_url:
            auth_version = "v2"
            auth_url_v2 = parse.urljoin(auth_url, "/v2.0")
        else:
            url_path = parse.urlparse(auth_url).path
            auth_version = url_path[1:3]
            auth_url_v2 = auth_url.replace(url_path, "/v2.0")
        self.conf.set(section_name, "auth_version", auth_version)
        self.conf.set(section_name, "uri", auth_url_v2)
        self.conf.set(section_name, "uri_v3",
                      auth_url_v2.replace("/v2.0", "/v3"))

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
            self.conf.set("validation", "network_for_ssh", net_name)

    def _configure_network_feature_enabled(
            self, section_name="network-feature-enabled"):
        if "neutron" in self.available_services:
            neutronclient = self.clients.neutron()
            # NOTE(ylobankov): We need the if/else block here because
            # the list_ext method has different number of arguments in
            # different Neutron client versions.
            cl_ver = nc_version.__version__
            if version.StrictVersion(cl_ver) >= version.StrictVersion("4.1.0"):
                # Neutron client version >= 4.1.0
                extensions = neutronclient.list_ext(
                    "extensions", "/extensions", retrieve_all=True)
            else:
                # Neutron client version < 4.1.0
                extensions = neutronclient.list_ext("/extensions")
            aliases = [ext["alias"] for ext in extensions["extensions"]]
            aliases_str = ",".join(aliases)
            self.conf.set(section_name, "api_extensions", aliases_str)

    def _configure_oslo_concurrency(self, section_name="oslo_concurrency"):
        lock_path = os.path.join(self.data_dir,
                                 "lock_files_%s" % self.deployment)
        if not os.path.exists(lock_path):
            os.makedirs(lock_path)
        self.conf.set(section_name, "lock_path", lock_path)

    def _configure_object_storage(self, section_name="object-storage"):
        self.conf.set(section_name, "operator_role",
                      CONF.tempest.swift_operator_role)
        self.conf.set(section_name, "reseller_admin_role",
                      CONF.tempest.swift_reseller_admin_role)

    def _configure_scenario(self, section_name="scenario"):
        self.conf.set(section_name, "img_dir", self.data_dir)
        self.conf.set(section_name, "img_file", self.image_name)

    def _configure_service_available(self, section_name="service_available"):
        services = ["cinder", "glance", "heat", "ironic", "neutron", "nova",
                    "sahara", "swift"]
        for service in services:
            # Convert boolean to string because ConfigParser fails
            # on attempt to get option with boolean value
            self.conf.set(section_name, service,
                          str(service in self.available_services))

    def _configure_validation(self, section_name="validation"):
        if "neutron" in self.available_services:
            self.conf.set(section_name, "connect_method", "floating")
        else:
            self.conf.set(section_name, "connect_method", "fixed")

    def _configure_orchestration(self, section_name="orchestration"):
        self.conf.set(section_name, "stack_owner_role",
                      CONF.tempest.heat_stack_owner_role)
        self.conf.set(section_name, "stack_user_role",
                      CONF.tempest.heat_stack_user_role)

    def generate(self, conf_path, extra_conf=None):
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith("_configure_"):
                method()

        if extra_conf:
            for section in extra_conf.sections():
                if section not in self.conf.sections():
                    self.conf.add_section(section)
                for option, value in extra_conf.items(section):
                    self.conf.set(section, option, value)

        _write_config(conf_path, self.conf)


class TempestResourcesContext(utils.RandomNameGeneratorMixin):
    """Context class to create/delete resources needed for Tempest."""

    RESOURCE_NAME_FORMAT = "rally_verify_XXXXXXXX_XXXXXXXX"

    def __init__(self, deployment, verification, conf_path):
        credential = db.deployment_get(deployment)["admin"]
        self.clients = osclients.Clients(objects.Credential(**credential))
        self.available_services = self.clients.services().values()

        self.verification = verification

        self.conf_path = conf_path
        self.conf = configparser.ConfigParser()
        self.conf.read(conf_path)

        self.image_name = parse.urlparse(
            CONF.tempest.img_url).path.split("/")[-1]

        self._created_roles = []
        self._created_images = []
        self._created_flavors = []
        self._created_networks = []

    def __enter__(self):
        self._create_tempest_roles()
        self._configure_option("compute", "image_ref",
                               self._discover_or_create_image)
        self._configure_option("compute", "image_ref_alt",
                               self._discover_or_create_image)
        self._configure_option("compute", "flavor_ref",
                               self._discover_or_create_flavor,
                               CONF.tempest.flavor_ref_ram)
        self._configure_option("compute", "flavor_ref_alt",
                               self._discover_or_create_flavor,
                               CONF.tempest.flavor_ref_alt_ram)
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
                                   self._discover_or_create_flavor,
                                   CONF.tempest.heat_instance_type_ram)

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
        roles = [CONF.tempest.swift_operator_role,
                 CONF.tempest.swift_reseller_admin_role,
                 CONF.tempest.heat_stack_owner_role,
                 CONF.tempest.heat_stack_user_role]
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
            LOG.debug("Option '{opt}' is already configured "
                      "in Tempest config file. {opt} = {opt_val}"
                      .format(opt=option, opt_val=option_value))

    def _discover_or_create_image(self):
        glance_wrapper = glance.wrap(self.clients.glance, self)

        if CONF.tempest.img_name_regex:
            LOG.debug("Trying to discover a public image with name matching "
                      "regular expression '%s'. Note that case insensitive "
                      "matching is performed" % CONF.tempest.img_name_regex)
            images = glance_wrapper.list_images(status="active",
                                                visibility="public")
            for img in images:
                if img.name and re.match(CONF.tempest.img_name_regex,
                                         img.name, re.IGNORECASE):
                    LOG.debug(
                        "The following public image discovered: '{0}'. "
                        "Using image '{0}' for the tests".format(img.name))
                    return img

            LOG.debug("There is no public image with name matching "
                      "regular expression '%s'" % CONF.tempest.img_name_regex)

        params = {
            "name": self.generate_random_name(),
            "disk_format": CONF.tempest.img_disk_format,
            "container_format": CONF.tempest.img_container_format,
            "image_location": os.path.join(_create_or_get_data_dir(),
                                           self.image_name),
            "visibility": "public"
        }
        LOG.debug("Creating image '%s'" % params["name"])
        image = glance_wrapper.create_image(**params)
        self._created_images.append(image)

        return image

    def _discover_or_create_flavor(self, flv_ram):
        novaclient = self.clients.nova()

        LOG.debug("Trying to discover a flavor with the following "
                  "properties: RAM = %dMB, VCPUs = 1, disk = 0GB" % flv_ram)
        for flavor in novaclient.flavors.list():
            if (flavor.ram == flv_ram
                    and flavor.vcpus == 1 and flavor.disk == 0):
                LOG.debug("The following flavor discovered: '{0}'. Using "
                          "flavor '{0}' for the tests".format(flavor.name))
                return flavor

        LOG.debug("There is no flavor with the mentioned properties")

        params = {
            "name": self.generate_random_name(),
            "ram": flv_ram,
            "vcpus": 1,
            "disk": 0
        }
        LOG.debug("Creating flavor '%s' with the following properties: RAM "
                  "= %dMB, VCPUs = 1, disk = 0GB" % (params["name"], flv_ram))
        flavor = novaclient.flavors.create(**params)
        self._created_flavors.append(flavor)

        return flavor

    def _create_network_resources(self):
        neutron_wrapper = network.NeutronWrapper(self.clients, self)
        tenant_id = self.clients.keystone.auth_ref.project_id
        LOG.debug("Creating network resources: network, subnet, router")
        net = neutron_wrapper.create_network(
            tenant_id, subnets_num=1, add_router=True,
            network_create_args={"shared": True})
        self._created_networks.append(net)

        return net

    def _cleanup_tempest_roles(self):
        keystoneclient = self.clients.keystone()
        for role in self._created_roles:
            LOG.debug("Deleting role '%s'" % role.name)
            keystoneclient.roles.delete(role.id)

    def _cleanup_images(self):
        glance_wrapper = glance.wrap(self.clients.glance, self)
        for image in self._created_images:
            LOG.debug("Deleting image '%s'" % image.name)
            self.clients.glance().images.delete(image.id)
            task_utils.wait_for_status(
                image, ["deleted", "pending_delete"],
                check_deletion=True,
                update_resource=glance_wrapper.get_image,
                timeout=CONF.benchmark.glance_image_delete_timeout,
                check_interval=CONF.benchmark.
                glance_image_delete_poll_interval)
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
