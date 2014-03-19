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

from rally.deploy.serverprovider.providers import openstack as provider
from rally import exceptions
from rally.openstack.common.fixture import mockpatch
from tests import fakes
from tests import test

MOD_NAME = 'rally.deploy.serverprovider.providers.openstack'
OSProvider = provider.OpenStackProvider


class FakeOSClients(object):

    def nova(self):
        return "nova"

    def glance(self):
        return "glance"


class OpenStackProviderTestCase(test.TestCase):

    def setUp(self):
        super(OpenStackProviderTestCase, self).setUp()
        self.useFixture(mockpatch.Patch('rally.deploy.serverprovider.provider.'
                                        'ResourceManager'))

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
        self.clients.glance = mock.Mock(return_value=self.glance_client)

        self.instance = mock.MagicMock()
        self.instance.status = "ACTIVE"

        self.nova_client = mock.MagicMock()
        self.nova_client.servers.create = mock.MagicMock(
                                return_value=self.instance)

        self.clients.nova = mock.MagicMock(
                                return_value=self.nova_client)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init(self, os_cli):
        cfg = self._get_valid_config()
        os_cli.Clients = mock.MagicMock(return_value=FakeOSClients())
        os_provider = OSProvider(mock.MagicMock(), cfg)
        self.assertEqual('nova', os_provider.nova)
        self.assertEqual('glance', os_provider.glance)

    @mock.patch('rally.osclients.Clients.glance')
    def test_openstack_provider_init_no_glance(self, mock_glance):
        mock_glance.side_effect = KeyError('image')
        cfg = self._get_valid_config()
        provider = OSProvider(mock.MagicMock(), cfg)
        self.assertEqual(provider.glance, None)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_no_user(self,
                                                               mock_osclient):
        cfg = self._get_valid_config()
        cfg.pop("user")
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_no_url(self,
                                                              mock_osclient):
        cfg = self._get_valid_config()
        del cfg['image']['url']
        del cfg['image']['checksum']
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_extra_key(self,
                                                                 mock_osclnt):
        cfg = self._get_valid_config()
        cfg["aaaaa"] = "bbbbb"
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_flavor_(self,
                                                               mock_osclient):
        cfg = self._get_valid_config()["user"] = 1111
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_with_valid_config(self,
                                                  mock_osclient):
        cfg = self._get_valid_config()
        OSProvider(mock.MagicMock(), cfg)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_with_valid_config_uuid(self, mock_osclient):
        cfg = self._get_valid_config()
        cfg['image'] = dict(uuid="289D7A51-1A0C-43C4-800D-706EA8A3CDF3")
        OSProvider(mock.MagicMock(), cfg)

    @mock.patch("rally.deploy.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_with_valid_config_checksum(self,
                                                           mock_osclient):
        cfg = self._get_valid_config()
        cfg['image'] = dict(checksum="checksum")
        OSProvider(mock.MagicMock(), cfg)

    @mock.patch(MOD_NAME + '.osclients')
    @mock.patch(MOD_NAME + '.open', create=True)
    @mock.patch(MOD_NAME + '.provider')
    @mock.patch('rally.benchmark.utils.get_from_manager')
    @mock.patch('time.sleep')
    def test_openstack_provider_create_servers(self, mock_sleep, get, g,
                                               provider, clients):
        get.return_value = lambda r: r
        self._init_mock_clients()
        clients.Clients = mock.MagicMock(return_value=self.clients)
        provider.Server = mock.MagicMock()
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        prov.get_image_uuid = mock.Mock()
        prov.nova.keypairs.create.return_value = mock.Mock(id='keypair_id',
                                                           name='keypair_name')
        self.instance.id = 'instance_id'
        prov.create_servers()
        self.assertEqual(['keypairs.create', 'servers.create'],
                         [call[0] for call in self.nova_client.mock_calls])
        prov.resources.create.assert_has_calls([
            mock.call({'id': 'keypair_id'}, type='keypair'),
            mock.call({'id': 'instance_id'}, type='server'),
        ])

    @mock.patch(MOD_NAME + '.osclients')
    @mock.patch(MOD_NAME + '.urllib2')
    def test_openstack_provider_get_image_found_by_checksum(self, u, oscl):
        self._init_mock_clients()
        oscl.Clients = mock.MagicMock(return_value=self.clients)
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        image_uuid = prov.get_image_uuid()
        self.assertEqual(image_uuid, 'fake-uuid')

    @mock.patch(MOD_NAME + '.osclients')
    @mock.patch(MOD_NAME + '.urllib2')
    def test_openstack_provider_get_image_download(self, u, oscl):
        self._init_mock_clients()
        self.glance_client.images.list = mock.Mock(return_value=[])
        oscl.Clients = mock.MagicMock(return_value=self.clients)
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        image_uuid = prov.get_image_uuid()
        self.assertEqual(image_uuid, 'fake-uuid')
        self.assertEqual(u.mock_calls,
                         [mock.call.urlopen('http://example.net/img.qcow2')])

    @mock.patch(MOD_NAME + '.osclients')
    def test_openstack_provider_get_image_no_glance_exception(
            self, mock_osclients):
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        prov.glance = None
        self.assertRaises(exceptions.InvalidConfigException,
                          prov.get_image_uuid)

    @mock.patch(MOD_NAME + '.osclients')
    def test_openstack_provider_get_image_from_uuid_no_glance(
            self, mock_osclients):
        conf = self._get_valid_config()
        conf['image']['uuid'] = "EC7A1DB7-C5BD-49A2-8066-613809CB22F5"
        prov = OSProvider(mock.MagicMock(), conf)
        prov.glance = True
        self.assertEqual(conf['image']['uuid'], prov.get_image_uuid())

    @mock.patch(MOD_NAME + '.osclients')
    def test_openstack_provider_destroy_servers(self, mock_osclients):
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        prov.resources.get_all.side_effect = [
            [fakes.FakeResource(
                id=1,
                items={'info': {'id': '35FC0503-FED6-419F-B6EE-B704198CE642'}}
            )],
            [fakes.FakeResource(
                id=2,
                items={'info': {'id': 'keypair_name'}}
            )],
        ]
        prov.destroy_servers()
        prov.resources.get_all.assert_has_calls([
            mock.call(type='server'),
            mock.call(type='keypair'),
        ])
        prov.nova.servers.delete.assert_called_once_with(
            '35FC0503-FED6-419F-B6EE-B704198CE642')
        prov.nova.keypairs.delete.assert_called_once_with('keypair_name')
        prov.resources.delete.assert_has_calls([
            mock.call(1),
            mock.call(2),
        ])
