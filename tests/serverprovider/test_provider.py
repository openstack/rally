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
"""Test for vm providers."""

import mock

from rally import exceptions
from rally import serverprovider
from rally import sshutils
from rally import test


ProviderFactory = serverprovider.ProviderFactory


class ProviderMixIn(object):
    def create_vms(self, image_uuid=None, amount=1):
        pass

    def destroy_vms(self):
        pass


class ProviderA(ProviderMixIn, ProviderFactory):
    pass


class ProviderB(ProviderMixIn, ProviderFactory):
    pass


class ProviderC(ProviderB):
    pass


FAKE_PROVIDERS = [ProviderA, ProviderB, ProviderC]


class ProviderTestCase(test.TestCase):

    @mock.patch.object(ProviderFactory, 'validate')
    def test_init(self, fake_validate):
        ProviderA(None, None)
        fake_validate.assert_called_once_with()

    def test_get_provider_not_found(self):
        self.assertRaises(exceptions.NoSuchVMProvider,
                          ProviderFactory.get_provider,
                          {"name": "fail"}, None)

    def test_get_provider(self):
        for p in FAKE_PROVIDERS:
                p_inst = ProviderFactory.get_provider({"name": p.__name__},
                                                      None)
                # TODO(boris-42): make it work through assertIsInstance
                self.assertEqual(str(type(p_inst)), str(p))

    def test_get_available_providers(self):
        providers = set([p.__name__ for p in FAKE_PROVIDERS])
        real_providers = set(ProviderFactory.get_available_providers())
        self.assertEqual(providers & real_providers, providers)

    def test_vm_prvoider_factory_is_abstract(self):
        self.assertRaises(TypeError, ProviderFactory)

    def test_image_methods_raise_not_implemented(self):
        provider = FAKE_PROVIDERS[0](None, None)
        self.assertRaises(NotImplementedError,
                          provider.upload_image, None, None, None)
        self.assertRaises(NotImplementedError, provider.destroy_image, None)


class ServerTestCase(test.TestCase):
    def setUp(self):
        super(ServerTestCase, self).setUp()
        self.vals = ['uuid', '192.168.1.1', 'admin', 'some_key', 'pwd']
        self.keys = ['uuid', 'ip', 'user', 'key', 'password']

    def test_init_server_dto(self):
        server = serverprovider.Server(*self.vals)
        for k, v in dict(zip(self.keys, self.vals)).iteritems():
            self.assertEqual(getattr(server, k), v)
        self.assertIsInstance(server.ssh, sshutils.SSH)

    def test_credentials(self):
        server_one = serverprovider.Server(*self.vals)
        creds = server_one.get_credentials()
        server_two = serverprovider.Server.from_credentials(creds)
        for k in self.keys:
            self.assertEqual(getattr(server_one, k), getattr(server_two, k))


class ImageDTOTestCase(test.TestCase):
    def test_init_image_dto(self):
        vals = ['uuid', 'qcow2', 'bare']
        keys = ['uuid', 'image_format', 'container_format']
        server = serverprovider.ImageDTO(*vals)
        for k, v in dict(zip(keys, vals)).iteritems():
            self.assertEqual(getattr(server, k), v)


class ResourceManagerTestCase(test.TestCase):
    def setUp(self):
        super(ResourceManagerTestCase, self).setUp()
        self.deployment = mock.Mock()
        self.resources = serverprovider.ResourceManager(self.deployment,
                                                        'provider')

    def test_create(self):
        self.resources.create('info', type='type')
        self.deployment.add_resource.assert_called_once_with('provider',
                                                             type='type',
                                                             info='info')

    def test_get_all(self):
        self.resources.get_all(type='type')
        self.deployment.get_resources.assert_called_once_with(
            provider_name='provider', type='type')

    def test_delete(self):
        self.resources.delete('resource_id')
        self.deployment.delete_resource.assert_called_once_with('resource_id')
