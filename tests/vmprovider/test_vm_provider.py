
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
from rally import test
from rally import vmprovider


class VMProviderTestCase(test.NoDBTestCase):

    def test_get_provider_not_found(self):
        self.assertRaises(exceptions.NoSuchVMProvider,
                          vmprovider.VMProviderFactory.get_provider,
                          "non_existing", None)

    def _create_fake_providers(self):
        class ProviderMixIn(object):
            def create_vms(self, image_uuid=None, amount=1):
                pass

            def destroy_vms(self, vm_uuids):
                pass

        class ProviderA(ProviderMixIn, vmprovider.VMProviderFactory):
            def __init__(self, config):
                pass

        class ProviderB(ProviderMixIn, vmprovider.VMProviderFactory):
            def __init__(self, config):
                pass

        class ProviderC(ProviderB):
            def __init__(self, config):
                pass

        return [ProviderA, ProviderB, ProviderC]

    def test_get_provider(self):
        for p in self._create_fake_providers():
                p_inst = vmprovider.VMProviderFactory.get_provider(p.__name__,
                                                                   None)
                # TODO(boris-42): make it work through assertIsInstance
                self.assertEqual(str(type(p_inst)), str(p))

    def test_get_available_providers(self):
        providers = set([p.__name__ for p in self._create_fake_providers()])
        real_providers = \
            set(vmprovider.VMProviderFactory.get_available_providers())
        self.assertEqual(providers & real_providers, providers)

    def test_vm_prvoider_factory_is_abstract(self):
        self.assertRaises(TypeError, vmprovider.VMProviderFactory)

    def test_image_methods_raise_not_implemented(self):
        provider = self._create_fake_providers()[0](None)
        self.assertRaises(NotImplementedError, provider.upload_image, None)
        self.assertRaises(NotImplementedError, provider.destroy_image, None)
