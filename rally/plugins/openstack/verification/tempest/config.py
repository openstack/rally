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

from oslo_config import cfg
import six
from six.moves import configparser
from six.moves.urllib import parse

from rally.common import objects
from rally import osclients
from rally.verification import utils


TEMPEST_OPTS = [
    cfg.StrOpt("img_url",
               default="http://download.cirros-cloud.net/"
                       "0.3.5/cirros-0.3.5-x86_64-disk.img",
               help="image URL"),
    cfg.StrOpt("img_disk_format",
               default="qcow2",
               help="Image disk format to use when creating the image"),
    cfg.StrOpt("img_container_format",
               default="bare",
               help="Image container format to use when creating the image"),
    cfg.StrOpt("img_name_regex",
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


class TempestConfigfileManager(object):
    """Class to create a Tempest config file."""

    def __init__(self, deployment):
        self.credential = deployment.get_credentials_for("openstack")["admin"]
        self.clients = osclients.Clients(objects.Credential(**self.credential))
        self.available_services = self.clients.services().values()

        self.conf = configparser.ConfigParser()

    def _get_service_type_by_service_name(self, service_name):
        for s_type, s_name in self.clients.services().items():
            if s_name == service_name:
                return s_type

    def _configure_auth(self, section_name="auth"):
        self.conf.set(section_name, "admin_username",
                      self.credential["username"])
        self.conf.set(section_name, "admin_password",
                      self.credential["password"])
        self.conf.set(section_name, "admin_project_name",
                      self.credential["tenant_name"])
        # Keystone v3 related parameter
        self.conf.set(section_name, "admin_domain_name",
                      self.credential["user_domain_name"] or "Default")

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
                net_name = public_nets[0]["name"]
                self.conf.set(section_name, "public_network_id", net_id)
                self.conf.set(section_name, "floating_network_name", net_name)
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
            extensions = neutronclient.list_ext("extensions", "/extensions",
                                                retrieve_all=True)
            aliases = [ext["alias"] for ext in extensions["extensions"]]
            aliases_str = ",".join(aliases)
            self.conf.set(section_name, "api_extensions", aliases_str)

    def _configure_object_storage(self, section_name="object-storage"):
        self.conf.set(section_name, "operator_role",
                      CONF.tempest.swift_operator_role)
        self.conf.set(section_name, "reseller_admin_role",
                      CONF.tempest.swift_reseller_admin_role)

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

    def create(self, conf_path, extra_options=None):
        self.conf.read(os.path.join(os.path.dirname(__file__), "config.ini"))

        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith("_configure_"):
                method()

        if extra_options:
            utils.add_extra_options(extra_options, self.conf)

        with open(conf_path, "w") as configfile:
            self.conf.write(configfile)

        raw_conf = six.StringIO()
        raw_conf.write("# Some empty values of options will be replaced while "
                       "creating required resources (images, flavors, etc).\n")
        self.conf.write(raw_conf)

        return raw_conf.getvalue()
