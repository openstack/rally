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

import datetime
import inspect
import os
import time

from oslo_config import cfg
import requests
from six.moves import configparser
from six.moves.urllib import parse

from rally.common.i18n import _
from rally.common import log as logging
from rally import db
from rally import exceptions
from rally import objects
from rally import osclients


LOG = logging.getLogger(__name__)


IMAGE_OPTS = [
    cfg.StrOpt("cirros_version",
               default="0.3.2",
               help="Version of cirros image"),
    cfg.StrOpt("cirros_image",
               default="cirros-0.3.2-x86_64-disk.img",
               help="Cirros image name"),
    cfg.StrOpt("cirros_base_url",
               default="http://download.cirros-cloud.net",
               help="Cirros image base URL"),
]
CONF = cfg.CONF
CONF.register_opts(IMAGE_OPTS, "image")


class TempestConfigCreationFailure(exceptions.RallyException):
    msg_fmt = _("Unable create tempest.conf: '%(message)s'")


class TempestConf(object):

    def __init__(self, deployment):
        self.endpoint = db.deployment_get(deployment)["admin"]
        self.clients = osclients.Clients(objects.Endpoint(**self.endpoint))
        try:
            self.keystoneclient = self.clients.verified_keystone()
        except exceptions.InvalidAdminException:
            msg = (_("Admin permission is required to generate tempest "
                     "configuration file. User %s doesn't have admin role.") %
                   self.endpoint["username"])
            raise TempestConfigCreationFailure(msg)

        self.available_services = self.clients.services().values()

        self.conf = configparser.ConfigParser()
        self.conf.read(os.path.join(os.path.dirname(__file__), "config.ini"))
        self.deployment = deployment
        self.data_path = os.path.join(os.path.expanduser("~"), ".rally",
                                      "tempest", "data")
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
        self.img_path = os.path.join(self.data_path,
                                     CONF.image.cirros_image)
        if not os.path.isfile(self.img_path):
            self._load_img()

    def _load_img(self):
        cirros_url = ("%s/%s/%s" %
                      (CONF.image.cirros_base_url,
                       CONF.image.cirros_version,
                       CONF.image.cirros_image))
        try:
            response = requests.get(cirros_url, stream=True)
        except requests.ConnectionError as err:
            msg = _("Error on downloading cirros image, possibly"
                    " no connection to Internet with message %s") % str(err)
            raise TempestConfigCreationFailure(msg)
        if response.status_code == 200:
            with open(self.img_path + ".tmp", "wb") as img_file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:   # filter out keep-alive new chunks
                        img_file.write(chunk)
                        img_file.flush()
            os.rename(self.img_path + ".tmp", self.img_path)
        else:
            if response.status_code == 404:
                msg = _("Error on downloading cirros image, possibly"
                        "invalid cirros_version or cirros_image in rally.conf")
            else:
                msg = _("Error on downloading cirros image, "
                        "HTTP error code %s") % response.getcode()
            raise TempestConfigCreationFailure(msg)

    def _get_url(self, servicename):
        services_type2name_map = self.clients.services()
        for service in self.keystoneclient.auth_ref["serviceCatalog"]:
            if services_type2name_map.get(service["type"]) == servicename:
                return service["endpoints"][0]["publicURL"]

    def _set_default(self):
        lock_path = os.path.join(self.data_path,
                                 "lock_files_%s" % self.deployment)
        if not os.path.exists(lock_path):
            os.makedirs(lock_path)
        self.conf.set("DEFAULT", "lock_path", lock_path)

    def _set_boto(self, section_name="boto"):
        self.conf.set(section_name, "ec2_url", self._get_url("ec2"))
        self.conf.set(section_name, "s3_url", self._get_url("s3"))
        materials_path = os.path.join(self.data_path, "s3materials")
        self.conf.set(section_name, "s3_materials_path", materials_path)
        # TODO(olkonami): find out how can we get ami, ari, aki manifest files

    def _set_compute_images(self, section_name="compute"):
        glanceclient = self.clients.glance()
        image_list = [img for img in glanceclient.images.list()
                      if img.status.lower() == "active" and
                      img.name is not None and "cirros" in img.name]
        # Upload new images if there are no
        # necessary images in the cloud (cirros)
        while len(image_list) < 2:
            now = (datetime.datetime.fromtimestamp(time.time()).
                   strftime("%Y_%m_%d_%H_%M_%S"))
            try:
                image = glanceclient.images.create(name=("cirros_%s" % now),
                                                   disk_format="qcow2",
                                                   container_format="bare")
                image.update(data=open(self.img_path, "rb"))
                image_list.append(image)
            except Exception as e:
                msg = _("There are no desired images (cirros) or only one and "
                        "new image could not be created.\n"
                        "Reason: %s") % getattr(e, "message", "unknown")
                raise TempestConfigCreationFailure(msg)
        self.conf.set(section_name, "image_ref", image_list[0].id)
        self.conf.set(section_name, "image_ref_alt", image_list[1].id)

    def _set_compute_flavors(self, section_name="compute"):
        novaclient = self.clients.nova()
        flavor_list = sorted(novaclient.flavors.list(),
                             key=lambda flv: flv.ram)
        # Create new flavors if they are missing
        while len(flavor_list) < 2:
            now = (datetime.datetime.fromtimestamp(time.time()).
                   strftime("%Y_%m_%d_%H_%M_%S"))
            try:
                flv = novaclient.flavors.create("m1.tiny_%s" % now, 512, 1, 1)
                flavor_list.append(flv)
            except Exception as e:
                msg = _("There are no desired flavors or only one and "
                        "new flavor could not be created.\n"
                        "Reason: %s") % getattr(e, "message", "unknown")
                raise TempestConfigCreationFailure(msg)
        self.conf.set(section_name, "flavor_ref", flavor_list[0].id)
        self.conf.set(section_name, "flavor_ref_alt", flavor_list[1].id)

    def _set_compute_ssh_connect_method(self, section_name="compute"):
        if "neutron" in self.available_services:
            self.conf.set(section_name, "ssh_connect_method", "floating")
        else:
            self.conf.set(section_name, "ssh_connect_method", "fixed")

    def _set_compute_admin(self, section_name="compute-admin"):
        self.conf.set(section_name, "username", self.endpoint["username"])
        self.conf.set(section_name, "password", self.endpoint["password"])
        self.conf.set(section_name, "tenant_name",
                      self.endpoint["tenant_name"])

    def _set_identity(self, section_name="identity"):
        self.conf.set(section_name, "username", self.endpoint["username"])
        self.conf.set(section_name, "password", self.endpoint["password"])
        self.conf.set(section_name, "tenant_name",
                      self.endpoint["tenant_name"])
        self.conf.set(section_name, "alt_username", self.endpoint["username"])
        self.conf.set(section_name, "alt_password", self.endpoint["password"])
        self.conf.set(section_name, "alt_tenant_name",
                      self.endpoint["tenant_name"])
        self.conf.set(section_name, "admin_username",
                      self.endpoint["username"])
        self.conf.set(section_name, "admin_password",
                      self.endpoint["password"])
        self.conf.set(section_name, "admin_tenant_name",
                      self.endpoint["tenant_name"])
        self.conf.set(section_name, "uri", self.endpoint["auth_url"])
        self.conf.set(section_name, "uri_v3",
                      self.endpoint["auth_url"].replace("/v2.0", "/v3"))
        self.conf.set(section_name, "admin_domain_name",
                      self.endpoint["admin_domain_name"])

    def _set_network(self, section_name="network"):
        if "neutron" in self.available_services:
            neutron = self.clients.neutron()
            public_net = [net for net in neutron.list_networks()["networks"] if
                          net["status"] == "ACTIVE" and
                          net["router:external"] is True]
            if public_net:
                net_id = public_net[0]["id"]
                self.conf.set(section_name, "public_network_id", net_id)
                public_router = neutron.list_routers(
                    network_id=net_id)["routers"][0]
                self.conf.set(section_name, "public_router_id",
                              public_router["id"])
                subnets = neutron.list_subnets(network_id=net_id)["subnets"]
                if subnets:
                    subnet = subnets[0]
                else:
                    # TODO(akurilin): create public subnet
                    LOG.warn("No public subnet is found.")
            else:
                subnets = neutron.list_subnets()["subnets"]
                if subnets:
                    subnet = subnets[0]
                else:
                    # TODO(akurilin): create subnet
                    LOG.warn("No subnet is found.")
            self.conf.set(section_name, "default_network", subnet["cidr"])
        else:
            network = self.clients.nova().networks.list()[0]
            self.conf.set(section_name, "default_network", network.cidr)

    def _set_service_available(self, section_name="service_available"):
        services = ["neutron", "heat", "ceilometer", "swift",
                    "cinder", "nova", "glance"]
        for service in services:
            self.conf.set(section_name, service,
                          str(service in self.available_services))
        horizon_url = ("http://" +
                       parse.urlparse(self.endpoint["auth_url"]).hostname)
        try:
            horizon_req = requests.get(horizon_url)
        except requests.RequestException as e:
            LOG.debug("Failed to connect to Horizon: %s" % e)
            horizon_availability = False
        else:
            horizon_availability = (horizon_req.status_code == 200)
        # convert boolean to string because ConfigParser fails
        # on attempt to get option with boolean value
        self.conf.set(section_name, "horizon", str(horizon_availability))

    def write_config(self, file_name):
        with open(file_name, "w+") as f:
            self.conf.write(f)

    def generate(self, file_name=None):
        for name, func in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("_set_"):
                func()
        if file_name:
            self.write_config(file_name)

        return self.conf
