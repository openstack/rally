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

from rally import exceptions
from rally import serverprovider
from rally import test


ProviderFactory = serverprovider.ProviderFactory


class ProviderTestCase(test.TestCase):

    def test_get_provider_not_found(self):
        self.assertRaises(exceptions.NoSuchVMProvider,
                          ProviderFactory.get_provider,
                          {"name": "fail"}, None)

    def _create_fake_providers(self):
        class ProviderMixIn(object):
            def create_vms(self, image_uuid=None, amount=1):
                pass

            def destroy_vms(self, vm_uuids):
                pass

        class ProviderA(ProviderMixIn, ProviderFactory):
            def __init__(self, config):
                pass

        class ProviderB(ProviderMixIn, ProviderFactory):
            def __init__(self, config):
                pass

        class ProviderC(ProviderB):
            def __init__(self, config):
                pass

        return [ProviderA, ProviderB, ProviderC]

    def test_get_provider(self):
        for p in self._create_fake_providers():
                p_inst = ProviderFactory.get_provider({"name": p.__name__},
                                                      None)
                # TODO(boris-42): make it work through assertIsInstance
                self.assertEqual(str(type(p_inst)), str(p))

    def test_get_available_providers(self):
        providers = set([p.__name__ for p in self._create_fake_providers()])
        real_providers = set(ProviderFactory.get_available_providers())
        self.assertEqual(providers & real_providers, providers)

    def test_vm_prvoider_factory_is_abstract(self):
        self.assertRaises(TypeError, ProviderFactory)

    def test_image_methods_raise_not_implemented(self):
        provider = self._create_fake_providers()[0](None)
        self.assertRaises(NotImplementedError,
                          provider.upload_image, None, None, None)
        self.assertRaises(NotImplementedError, provider.destroy_image, None)


class ServerDTOTestCase(test.TestCase):

    def test_init_server_dto(self):
        vals = ['uuid', '192.168.1.1', 'admin', 'some_key', 'pwd']
        keys = ['uuid', 'ip', 'user', 'key', 'password']
        server = serverprovider.ServerDTO(*vals)
        for k, v in dict(zip(keys, vals)).iteritems():
            self.assertEqual(getattr(server, k), v)


class ImageDTOTestCase(test.TestCase):
    def test_init_image_dto(self):
        vals = ['uuid', 'qcow2', 'bare']
        keys = ['uuid', 'image_format', 'container_format']
        server = serverprovider.ImageDTO(*vals)
        for k, v in dict(zip(keys, vals)).iteritems():
            self.assertEqual(getattr(server, k), v)
