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

import os
import time
import urllib2

from rally.benchmark import utils as benchmark_utils
from rally import exceptions
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import osclients
from rally.serverprovider import provider
from rally import utils


LOG = logging.getLogger(__name__)


SERVER_TYPE = 'server'
KEYPAIR_TYPE = 'keypair'


class OpenStackProvider(provider.ProviderFactory):
    """Provides VMs using existing OpenStack cloud.

    Sample configuration:

    {
        "name": "OpenStackProvider",
        "amount": 42
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
            "userdata": "#cloud-config\r\n disable_root: false"
        }
    }

    """

    CONFIG_SCHEMA = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'deployment_name': {'type': 'string'},
            'amount': {'type': 'integer'},
            'user': {'type': 'string'},
            'password': {'type': 'string'},
            'tenant': {'type': 'string'},
            'auth_url': {'type': 'string'},
            'flavor_id': {'type': 'string'},
            'image': {
                'type': 'object',
                'properties': {
                    'checksum': {'type': 'string'},
                    'name': {'type': 'string'},
                    'format': {'type': 'string'},
                    'userdata': {'type': 'string'},
                    'url': {'type': 'string'},
                    'uuid': {'type': 'string'},
                },
                'additionalProperties': False,
                'required': ['name', 'format', 'url', 'checksum'],
            },
        },
        'additionalProperties': False,
        'required': ['user', 'password', 'tenant', 'deployment_name',
                     'auth_url', 'flavor_id', 'image']
    }

    def __init__(self, deployment, config):
        super(OpenStackProvider, self).__init__(deployment, config)
        clients = osclients.Clients(config['user'], config['password'],
                                    config['tenant'], config['auth_url'])
        self.nova = clients.get_nova_client()
        self.glance = clients.get_glance_client()

    def get_image_uuid(self):
        """Get image uuid. Download image if necessary."""

        image_uuid = self.config['image'].get('uuid', None)
        if image_uuid:
            return image_uuid

        for image in self.glance.images.list():
            if image.checksum == self.config['image']['checksum']:
                LOG.info(_('Found image with appropriate checksum. Using it.'))
                return image.id

        LOG.info(_('Downloading new image %s') % self.config['image']['url'])
        image = self.glance.images.create(name=self.config['image']['name'])
        try:
            image.update(data=urllib2.urlopen(self.config['image']['url']),
                         disk_format=self.config['image']['format'],
                         container_format='bare')
        except urllib2.URLError:
            LOG.error(_('Unable to retrieve %s') % self.config['image']['url'])
            raise
        image.get()

        if image.checksum != self.config['image']['checksum']:
            raise exceptions.ChecksumMismatch(url=self.config['image']['url'])

        return image.id

    def get_userdata(self):
        userdata = self.config['image'].get('userdata', None)
        if userdata is not None:
            return userdata
        userdata = self.config['image'].get('userdata_file', None)
        if userdata is not None:
            userdata = open(userdata, 'r')
        return userdata

    def create_vms(self):
        """Create VMs with chosen image."""

        image_uuid = self.get_image_uuid()
        userdata = self.get_userdata()
        flavor = self.config['flavor_id']

        public_key_path = self.config.get(
            'ssh_public_key_file', os.path.expanduser('~/.ssh/id_rsa.pub'))
        public_key = open(public_key_path, 'r').read().strip()
        key_name = self.config['deployment_name'] + '-key'
        keypair = self.nova.keypairs.create(key_name, public_key)
        self.resources.create({'id': keypair.id}, type=KEYPAIR_TYPE)

        os_servers = []
        for i in range(self.config.get('amount', 1)):
            name = "%s-%d" % (self.config['deployment_name'], i)
            server = self.nova.servers.create(name, image_uuid, flavor,
                                              key_name=keypair.name,
                                              userdata=userdata)

            os_servers.append(server)
            self.resources.create({'id': server.id}, type=SERVER_TYPE)

        kwargs = {
            'is_ready': benchmark_utils.resource_is("ACTIVE"),
            'update_resource': benchmark_utils.get_from_manager(),
            'timeout': 120,
            'check_interval': 5
        }

        for os_server in os_servers:
            utils.wait_for(os_server, **kwargs)

        servers = [provider.Server(s.id,
                                   s.addresses.values()[0][0]['addr'],
                                   'root',
                                   public_key_path)
                   for s in os_servers]
        for s in servers:
            s.ssh.wait(timeout=120, interval=5)

        # NOTE(eyerediskin): usually ssh is ready much earlier then cloud-init
        time.sleep(8)
        return servers

    def destroy_vms(self):
        for resource in self.resources.get_all(type=SERVER_TYPE):
            self.nova.servers.delete(resource['info']['id'])
            self.resources.delete(resource)
        for resource in self.resources.get_all(type=KEYPAIR_TYPE):
            self.nova.keypairs.delete(resource['info']['id'])
            self.resources.delete(resource)
