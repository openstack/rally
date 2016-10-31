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

from rally.common import sshutils
from rally.deployment.serverprovider import provider
from rally import exceptions
from tests.unit import test


class ProviderMixIn(object):
    def create_servers(self, image_uuid=None, amount=1):
        pass

    def destroy_servers(self):
        pass


class ProviderA(ProviderMixIn, provider.ProviderFactory):
    """Fake server provider.

    Used for tests.
    """
    pass


class ProviderB(ProviderMixIn, provider.ProviderFactory):
    """Fake server provider.

    Used for tests.
    """
    pass


class ProviderC(ProviderB):
    """Fake server provider.

    Used for tests.
    """
    pass


FAKE_PROVIDERS = [ProviderA, ProviderB, ProviderC]


class ProviderFactoryTestCase(test.TestCase):

    @mock.patch.object(provider.ProviderFactory, "validate")
    def test_init(self, mock_validate):
        ProviderA(None, None)
        mock_validate.assert_called_once_with()

    def test_get_provider_not_found(self):
        self.assertRaises(exceptions.PluginNotFound,
                          provider.ProviderFactory.get_provider,
                          {"type": "fail"}, None)

    def test_vm_prvoider_factory_is_abstract(self):
        self.assertRaises(TypeError, provider.ProviderFactory)


class ServerTestCase(test.TestCase):
    def setUp(self):
        super(ServerTestCase, self).setUp()
        self.vals = ["192.168.1.1", "admin", "some_key", "pwd"]
        self.keys = ["host", "user", "key", "password"]

    def test_init_server_dto(self):
        server = provider.Server(*self.vals)
        for k, v in dict(zip(self.keys, self.vals)).items():
            self.assertEqual(getattr(server, k), v)
        self.assertIsInstance(server.ssh, sshutils.SSH)

    def test_credentials(self):
        server_one = provider.Server(*self.vals)
        creds = server_one.get_credentials()
        server_two = provider.Server.from_credentials(creds)
        for k in self.keys:
            self.assertEqual(getattr(server_one, k), getattr(server_two, k))


class ResourceManagerTestCase(test.TestCase):
    def setUp(self):
        super(ResourceManagerTestCase, self).setUp()
        self.deployment = mock.Mock()
        self.resources = provider.ResourceManager(self.deployment,
                                                  "provider")

    def test_create(self):
        self.resources.create("info", type="type")
        self.deployment.add_resource.assert_called_once_with("provider",
                                                             type="type",
                                                             info="info")

    def test_get_all(self):
        self.resources.get_all(type="type")
        self.deployment.get_resources.assert_called_once_with(
            provider_name="provider", type="type")

    def test_delete(self):
        self.resources.delete("resource_id")
        self.deployment.delete_resource.assert_called_once_with("resource_id")
