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

"""Tests for OpenStack VM provider."""

import jsonschema
import mock

from rally.serverprovider.providers import openstack as provider
from rally import test


MOD_NAME = 'rally.serverprovider.providers.openstack'
OSProvider = provider.OpenStackProvider


class FakeOSClients(object):

    def get_nova_client(self):
        return "nova"

    def get_glance_client(self):
        return "glance"


class OpenStackProviderTestCase(test.TestCase):

    def _get_valid_config(self):
        return {
            'image': {
                'url': 'http://example.net/img.qcow2',
                'format': 'qcow2',
                'name': 'Image',
                'checksum': '0123456789abcdef',
            },
            'deployment_name': 'rally-dep-1',
            'auth_url': 'urlto',
            'user': 'name',
            'password': 'mypass',
            'tenant': 'tenant',
            'flavor_id': '22'}

    def _init_mock_clients(self):

        def g():
            raise Exception('ooke')

        self.clients = mock.MagicMock()

        self.image = mock.MagicMock()
        self.image.checksum = '0123456789abcdef'
        self.image.get = mock.MagicMock(return_value=self.image)
        self.image.id = 'fake-uuid'
        self.glance_client = mock.Mock(return_value=self.image)
        self.glance_client.images.create = mock.Mock(return_value=self.image)
        self.glance_client.images.list = mock.Mock(return_value=[self.image])
        self.clients.get_glance_client = mock.Mock(
                                return_value=self.glance_client)

        self.instance = mock.MagicMock()
        self.instance.status = "ACTIVE"

        self.nova_client = mock.MagicMock()
        self.nova_client.servers.create = mock.MagicMock(
                                return_value=self.instance)

        self.clients.get_nova_client = mock.MagicMock(
                                return_value=self.nova_client)

    def test_openstack_provider_init(self):
        cfg = self._get_valid_config()

        mod = "rally.serverprovider.providers.openstack."
        with mock.patch(mod + "osclients") as os_cli:
            os_cli.Clients = mock.MagicMock(return_value=FakeOSClients())
            os_provider = OSProvider(cfg)
        expected_calls = [
            mock.call.Clients(cfg['user'], cfg['password'],
                              cfg['tenant'], cfg['auth_url'])]
        self.assertEqual(expected_calls, os_cli.mock_calls)
        self.assertEqual('nova', os_provider.nova)
        self.assertEqual('glance', os_provider.glance)

    def test_openstack_provider_init_with_invalid_conf_no_user(self):
        cfg = self._get_valid_config()
        cfg.pop("user")
        with mock.patch("rally.serverprovider.providers.openstack.osclients"):
            self.assertRaises(jsonschema.ValidationError, OSProvider, cfg)

    def test_openstack_provider_init_with_invalid_conf_extra_key(self):
        cfg = self._get_valid_config()
        cfg["aaaaa"] = "bbbbb"
        with mock.patch("rally.serverprovider.providers.openstack.osclients"):
            self.assertRaises(jsonschema.ValidationError, OSProvider, cfg)

    def test_openstack_provider_init_with_invalid_conf_flavor_(self):
        cfg = self._get_valid_config()
        cfg["user"] = 1111
        with mock.patch("rally.serverprovider.providers.openstack.osclients"):
            self.assertRaises(jsonschema.ValidationError, OSProvider, cfg)

    def test_openstack_provider_with_valid_config(self):
        cfg = self._get_valid_config()
        with mock.patch("rally.serverprovider.providers.openstack.osclients"):
            OSProvider(cfg)

    @mock.patch(MOD_NAME + '.osclients')
    @mock.patch(MOD_NAME + '.open', create=True)
    @mock.patch(MOD_NAME + '.provider')
    @mock.patch(MOD_NAME + '.nova_utils._get_from_manager', new=lambda r: r)
    def test_openstack_provider_create_vms(self, g, provider, clients):
        self._init_mock_clients()
        clients.Clients = mock.MagicMock(return_value=self.clients)
        provider.Server = mock.MagicMock()
        prov = OSProvider(self._get_valid_config())
        prov.get_image_uuid = mock.Mock()
        prov.create_vms()
        self.assertEqual(['keypairs.create', 'servers.create'],
                         [call[0] for call in self.nova_client.mock_calls])

    @mock.patch(MOD_NAME + '.osclients')
    @mock.patch(MOD_NAME + '.urllib2')
    def test_openstack_provider_get_image_found_by_checksum(self, u, oscl):
        self._init_mock_clients()
        oscl.Clients = mock.MagicMock(return_value=self.clients)
        prov = OSProvider(self._get_valid_config())
        image_uuid = prov.get_image_uuid()
        self.assertEqual(image_uuid, 'fake-uuid')

    @mock.patch(MOD_NAME + '.osclients')
    @mock.patch(MOD_NAME + '.urllib2')
    def test_openstack_provider_get_image_download(self, u, oscl):
        self._init_mock_clients()
        self.glance_client.images.list = mock.Mock(return_value=[])
        oscl.Clients = mock.MagicMock(return_value=self.clients)
        prov = OSProvider(self._get_valid_config())
        image_uuid = prov.get_image_uuid()
        self.assertEqual(image_uuid, 'fake-uuid')
        self.assertEqual(u.mock_calls,
                         [mock.call.urlopen('http://example.net/img.qcow2')])

    def test_openstack_provider_destroy_vms(self):
        with mock.patch(MOD_NAME + '.osclients'):
            prov = OSProvider(self._get_valid_config())
            server = mock.MagicMock()
            keypair = mock.MagicMock()
            prov.os_servers = [server]
            prov.keypair = keypair
            prov.destroy_vms()
        self.assertEqual(server.mock_calls, [mock.call.delete()])
        self.assertEqual(keypair.mock_calls, [mock.call.delete()])
