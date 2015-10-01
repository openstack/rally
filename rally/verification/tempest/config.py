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
from rally import exceptions
from rally import osclients

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


class TempestConfig(object):
    """Class to generate Tempest configuration file."""

    def __init__(self, deployment):
        self.deployment = deployment

        self.endpoint = db.deployment_get(deployment)["admin"]
        self.clients = osclients.Clients(objects.Endpoint(**self.endpoint))
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
        url = "http://%s/" % parse.urlparse(self.endpoint["auth_url"]).hostname
        self.conf.set(section_name, "dashboard_url", url)

    def _configure_identity(self, section_name="identity"):
        self.conf.set(section_name, "username", self.endpoint["username"])
        self.conf.set(section_name, "password", self.endpoint["password"])
        self.conf.set(section_name, "tenant_name",
                      self.endpoint["tenant_name"])

        self.conf.set(section_name, "admin_username",
                      self.endpoint["username"])
        self.conf.set(section_name, "admin_password",
                      self.endpoint["password"])
        self.conf.set(section_name, "admin_tenant_name",
                      self.endpoint["tenant_name"])

        self.conf.set(section_name, "uri", self.endpoint["auth_url"])
        v2_url_trailer = parse.urlparse(self.endpoint["auth_url"]).path
        self.conf.set(section_name, "uri_v3",
                      self.endpoint["auth_url"].replace(v2_url_trailer, "/v3"))

        self.conf.set(section_name, "admin_domain_name",
                      self.endpoint["admin_domain_name"])

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
                       parse.urlparse(self.endpoint["auth_url"]).hostname)
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

    def generate(self, conf_path=None):
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith("_configure_"):
                method()

        if conf_path:
            _write_config(conf_path, self.conf)


class TempestResourcesContext(object):
    """Context class to create/delete resources needed for Tempest."""

    def __init__(self, deployment, conf_path):
        endpoint = db.deployment_get(deployment)["admin"]
        self.clients = osclients.Clients(objects.Endpoint(**endpoint))
        self.keystone = self.clients.verified_keystone()

        self.conf_path = conf_path
        self.conf = configparser.ConfigParser()
        self.conf.read(conf_path)

    def __enter__(self):
        self._created_roles = []
        self._created_images = []
        self._created_flavors = []

        self._create_tempest_roles()
        self._configure_option("image_ref", self._create_image)
        self._configure_option("image_ref_alt", self._create_image)
        self._configure_option("flavor_ref", self._create_flavor, 64)
        self._configure_option("flavor_ref_alt", self._create_flavor, 128)

        _write_config(self.conf_path, self.conf)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._cleanup_roles()
        self._cleanup_resource("image", self._created_images)
        self._cleanup_resource("flavor", self._created_flavors)

    def _create_tempest_roles(self):
        roles = [CONF.role.swift_operator_role,
                 CONF.role.swift_reseller_admin_role,
                 CONF.role.heat_stack_owner_role,
                 CONF.role.heat_stack_user_role]
        existing_roles = set(role.name for role in self.keystone.roles.list())

        for role in roles:
            if role not in existing_roles:
                LOG.debug("Creating role '%s'" % role)
                self._created_roles.append(self.keystone.roles.create(role))

    def _configure_option(self, option, create_method, *args, **kwargs):
        option_value = self.conf.get("compute", option)
        if not option_value:
            LOG.debug("Option '%s' is not configured" % option)
            resource = create_method(*args, **kwargs)
            self.conf.set("compute", option, resource.id)
            LOG.debug("Option '{opt}' is configured. {opt} = {resource_id}"
                      .format(opt=option, resource_id=resource.id))
        else:
            LOG.debug("Option '{opt}' was configured manually "
                      "in Tempest config file. {opt} = {opt_val}"
                      .format(opt=option, opt_val=option_value))

    def _create_image(self):
        glanceclient = self.clients.glance()
        image_name = "rally-verify-cirros-img-%s" % uuid.uuid4()
        LOG.debug("Creating image '%s'" % image_name)
        try:
            image = glanceclient.images.create(
                name=image_name,
                disk_format="qcow2",
                container_format="bare",
                is_public=True)
            self._created_images.append(image)
            image.update(data=open(
                os.path.join(_create_or_get_data_dir(), IMAGE_NAME), "rb"))
        except Exception as exc:
            msg = _("Image could not be created. "
                    "Reason: %s") % (str(exc) or "unknown")
            raise exceptions.TempestResourceCreationFailure(msg)

        return image

    def _create_flavor(self, flv_ram):
        novaclient = self.clients.nova()
        flavor_name = "m1.rally-verify-flv-%s" % uuid.uuid4()
        LOG.debug("Creating flavor '%s'" % flavor_name)
        try:
            flavor = novaclient.flavors.create(
                flavor_name, ram=flv_ram, vcpus=1, disk=0)
        except Exception as exc:
            msg = _("Flavor could not be created. "
                    "Reason: %s") % (str(exc) or "unknown")
            raise exceptions.TempestResourceCreationFailure(msg)

        self._created_flavors.append(flavor)

        return flavor

    def _cleanup_roles(self):
        for role in self._created_roles:
            LOG.debug("Deleting role '%s'" % role.name)
            role.delete()

    def _cleanup_resource(self, resource_type, created_resources):
        for res in created_resources:
            LOG.debug("Deleting %s '%s'" % (resource_type, res.name))
            if res.id == self.conf.get("compute", "%s_ref" % resource_type):
                self.conf.set("compute", "%s_ref" % resource_type, "")
            else:
                self.conf.set("compute", "%s_ref_alt" % resource_type, "")
            res.delete()

        _write_config(self.conf_path, self.conf)
