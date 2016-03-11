# Copyright 2013: Mirantis Inc.
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

import itertools
import json
import os

import novaclient.exceptions

from rally.common.i18n import _
from rally.common import logging
from rally.common import objects
from rally.deployment.serverprovider import provider
from rally import exceptions
from rally import osclients
from rally.task import utils


LOG = logging.getLogger(__name__)


SERVER_TYPE = "server"
KEYPAIR_TYPE = "keypair"


def _get_address(s):
    if s.accessIPv4:
        return s.accessIPv4
    if s.accessIPv6:
        return s.accessIPv6
    for a in itertools.chain(s.addresses.get("public", []),
                             *s.addresses.values()):
        return a["addr"]
    raise RuntimeError("No address found for %s" % s)


def _cloud_init_success(s):
    status, stdout, stderr = s.ssh.execute(
        "cat /run/cloud-init/result.json")
    if status:
        LOG.debug("Failed to read result.json on %s: %s" %
                  (s, stderr))
        return False  # Not finished (or no cloud-init)

    res = json.loads(stdout)
    if res["v1"]["errors"]:
        raise RuntimeError("cloud-init exited with errors on %s: %s" %
                           (s, res["v1"]["errors"]))

    LOG.debug("cloud-init finished with no errors")
    return True  # Success!


@provider.configure(name="OpenStackProvider")
class OpenStackProvider(provider.ProviderFactory):
    """Provide VMs using an existing OpenStack cloud.

    Sample configuration:

    .. code-block:: json

        {
            "type": "OpenStackProvider",
            "amount": 42,
            "user": "admin",
            "tenant": "admin",
            "password": "secret",
            "auth_url": "http://example.com/",
            "flavor_id": 2,
            "image": {
                "checksum": "75846dd06e9fcfd2b184aba7fa2b2a8d",
                "url": "http://example.com/disk1.img",
                "name": "Ubuntu Precise(added by rally)",
                "format": "qcow2",
                "userdata": "disable_root: false"
            },
            "secgroup_name": "Rally"
        }
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "deployment_name": {"type": "string"},
            "amount": {"type": "integer"},
            "user": {"type": "string"},
            "nics": {"type": "array"},
            "password": {"type": "string"},
            "tenant": {"type": "string"},
            "auth_url": {"type": "string"},
            "region": {"type": "string"},
            "config_drive": {"type": "boolean"},
            "flavor_id": {"type": "string"},
            "wait_for_cloud_init": {"type": "boolean", "default": False},
            "image": {
                "type": "object",
                "properties": {
                    "checksum": {"type": "string"},
                    "name": {"type": "string"},
                    "format": {"type": "string"},
                    "userdata": {"type": "string"},
                    "url": {"type": "string"},
                    "uuid": {"type": "string"},
                },
                "additionalProperties": False,
                "anyOf": [
                    {
                        "title": "Create Image",
                        "required": ["name", "format", "url", "checksum"],
                    },
                    {
                        "title": "Existing image from checksum",
                        "required": ["checksum"]
                    },
                    {
                        "title": "Existing image from uuid",
                        "required": ["uuid"]
                    }
                ]
            },
            "secgroup_name": {"type": "string"},
        },
        "additionalProperties": False,
        "required": ["user", "password", "tenant", "deployment_name",
                     "auth_url", "flavor_id", "image"]
    }

    def __init__(self, deployment, config):
        super(OpenStackProvider, self).__init__(deployment, config)
        user_credential = objects.Credential(
            config["auth_url"], config["user"],
            config["password"], config["tenant"],
            region_name=config.get("region"))
        clients = osclients.Clients(user_credential)
        self.nova = clients.nova()
        self.sg = None
        try:
            self.glance = clients.glance()
        except KeyError:
            self.glance = None
            LOG.warning(_("Glance endpoint not available in service catalog"
                          ", only existing images can be used"))

    def get_image_uuid(self):
        """Get image uuid. Download image if necessary."""

        image_uuid = self.config["image"].get("uuid")
        if image_uuid:
            return image_uuid
        else:
            if not self.glance:
                raise exceptions.InvalidConfigException(
                    "If glance is not available in the service catalog"
                    " obtained by the openstack server provider, then"
                    " images cannot be uploaded so the uuid of an"
                    " existing image must be specified in the"
                    " deployment config."
                )

        for image in self.glance.images.list():
            if image.checksum == self.config["image"]["checksum"]:
                LOG.info(_("Found image with appropriate checksum. Using it."))
                return image.id

        LOG.info(_("Downloading new image %s") % self.config["image"]["url"])
        image = self.glance.images.create(
            name=self.config["image"]["name"],
            copy_from=self.config["image"]["url"],
            disk_format=self.config["image"]["format"],
            container_format="bare")
        image.get()

        if image.checksum != self.config["image"]["checksum"]:
            raise exceptions.ChecksumMismatch(url=self.config["image"]["url"])

        return image.id

    def get_userdata(self):
        userdata = self.config["image"].get("userdata")
        return userdata

    def create_keypair(self):
        public_key_path = self.config.get(
            "ssh_public_key_file", os.path.expanduser("~/.ssh/id_rsa.pub"))
        public_key = open(public_key_path, "r").read().strip()
        key_name = self.config["deployment_name"] + "-key"
        try:
            key = self.nova.keypairs.find(name=key_name)
            self.nova.keypairs.delete(key.id)
        except novaclient.exceptions.NotFound:
            pass
        keypair = self.nova.keypairs.create(key_name, public_key)
        self.resources.create({"id": keypair.id}, type=KEYPAIR_TYPE)
        return keypair, public_key_path

    def get_nics(self):
        return self.config.get("nics")

    def create_security_group_and_rules(self):
        sec_group_name = self.config.get("secgroup_name",
                                         "rally_security_group")
        rule_params = {
            "cidr": "0.0.0.0",
            "from_port": 0,
            "to_port": 0,
            "ip_protocol": "tcp"
        }

        self.sg = self.nova.security_groups.create(sec_group_name,
                                                   sec_group_name)

        self.nova.security_group_rules.create(
            self.sg.id, **rule_params)

    def create_servers(self):
        """Create VMs with chosen image."""

        image_uuid = self.get_image_uuid()
        userdata = self.get_userdata()
        flavor = self.config["flavor_id"]
        nics = self.get_nics()

        keypair, public_key_path = self.create_keypair()
        self.create_security_group_and_rules()

        sg_args = {"security_groups": [self.sg.name]} if self.sg else {}

        os_servers = []
        for i in range(self.config.get("amount", 1)):
            name = "%s-%d" % (self.config["deployment_name"], i)
            server = self.nova.servers.create(
                name, image_uuid, flavor,
                nics=nics,
                key_name=keypair.name,
                userdata=userdata,
                config_drive=self.config.get("config_drive", False),
                **sg_args)
            os_servers.append(server)
            self.resources.create({"id": server.id}, type=SERVER_TYPE)

        kwargs = {
            "ready_statuses": ["ACTIVE"],
            "update_resource": utils.get_from_manager(),
            "timeout": 120,
            "check_interval": 5
        }

        servers = []
        for os_server in os_servers:
            os_server = utils.wait_for(os_server, **kwargs)
            server = provider.Server(host=_get_address(os_server),
                                     user="root",
                                     key=public_key_path)
            servers.append(server)
        for s in servers:
            s.ssh.wait(timeout=120, interval=5)

        if self.config.get("wait_for_cloud_init", False):
            for s in servers:
                utils.wait_for(s, is_ready=_cloud_init_success)

        return servers

    def delete_security_group(self):
        sg_name = self.config.get("secgroup_name", "rally_security_group")
        sgs = self.nova.security_groups.list(serch_opts={"name": sg_name})
        if sgs:
            for secgroup in sgs:
                self.nova.security_groups.delete(secgroup.id)

    def destroy_servers(self):
        for resource in self.resources.get_all(type=SERVER_TYPE):
            try:
                self.nova.servers.delete(resource["info"]["id"])
            except novaclient.exceptions.NotFound:
                LOG.warning("Nova instance %s not found, so not deleting." %
                            resource["info"]["id"])
            try:
                self.resources.delete(resource.id)
            except exceptions.ResourceNotFound:
                LOG.warning(
                    "Instance resource record not found in DB, not removing."
                    " Deployment: %(deployment)s Instance ID:%(id)s"
                    " Instance Nova UUID:%(uuid)s" %
                    dict(deployment=resource.deployment_uuid,
                         id=resource.id,
                         uuid=resource["info"]["id"]
                         )
                )
        for resource in self.resources.get_all(type=KEYPAIR_TYPE):
            try:
                self.nova.keypairs.delete(resource["info"]["id"])
            except novaclient.exceptions.NotFound:
                LOG.warning("Nova keypair %s not found, so not deleting." %
                            resource["info"]["id"])
            try:
                self.resources.delete(resource.id)
            except exceptions.ResourceNotFound:
                LOG.warning(
                    "Keypair resource record not found in DB, not removing."
                    " Deployment: %(deployment)s Keypair ID:%(id)s"
                    " Keypair Name:%(name)s" %
                    dict(deployment=resource.deployment_uuid,
                         id=resource.id,
                         name=resource["info"]["id"]
                         )
                )
            finally:
                self.delete_security_group()
