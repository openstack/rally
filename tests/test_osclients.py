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

import mock

from rally import osclients
from rally import test


class FakeServiceCatalog(object):
    def get_endpoints(self):
        return {'image': [{'publicURL': 'http://fake.to'}]}


class FakeNova(object):
    pass


class FakeGlance(object):
    pass


class FakeCinder(object):
    pass


class FakeKeystone(object):
    def __init__(self):
        self.auth_token = 'fake'
        self.service_catalog = FakeServiceCatalog()

    def authenticate(self):
        return True


class OSClientsTestCase(test.TestCase):

    def _get_auth_params(self):
        args = ['user', 'pass', 'tenant', 'http://auth_url']
        keys = ['username', 'password', 'tenant_name', 'auth_url']
        return (args, dict(zip(keys, args)))

    def setUp(self):
        super(OSClientsTestCase, self).setUp()
        self.args, self.kwargs = self._get_auth_params()
        self.clients = osclients.Clients(*self.args)

    def test_init(self):
        self.assertEqual(self.kwargs, self.clients.kw)

    def test_get_keystone_client(self):
        with mock.patch('rally.osclients.keystone') as mock_keystone:
            fake_keystone = FakeKeystone()
            mock_keystone.Client = mock.MagicMock(return_value=fake_keystone)
            self.assertTrue("keystone" not in self.clients.cache)
            client = self.clients.get_keystone_client()
            self.assertEqual(client, fake_keystone)
            endpoint = {"endpoint": "http://auth_url:35357"}
            kwargs = dict(self.kwargs.items() + endpoint.items())
            mock_keystone.Client.assert_called_once_with(**kwargs)
            self.assertEqual(self.clients.cache["keystone"], fake_keystone)

    def test_get_nova_client(self):
        with mock.patch('rally.osclients.nova') as mock_nova:
            fake_nova = FakeNova()
            mock_nova.Client = mock.MagicMock(return_value=fake_nova)
            self.assertTrue("nova" not in self.clients.cache)
            client = self.clients.get_nova_client()
            self.assertEqual(client, fake_nova)
            mock_nova.Client.assert_called_once_with('2', *self.args[:3],
                                                     auth_url=self.args[-1],
                                                     service_type='compute')
            self.assertEqual(self.clients.cache["nova"], fake_nova)

    def test_get_glance_client(self):
        with mock.patch('rally.osclients.glance') as mock_glance:
            fake_glance = FakeGlance()
            mock_glance.Client = mock.MagicMock(return_value=fake_glance)
            kc = FakeKeystone()
            self.clients.get_keystone_client = mock.MagicMock(return_value=kc)
            self.assertTrue("glance" not in self.clients.cache)
            client = self.clients.get_glance_client()
            self.assertEqual(client, fake_glance)
            endpoint = kc.service_catalog.get_endpoints()['image'][0]

            kw = {'endpoint': endpoint['publicURL'], 'token': kc.auth_token}
            mock_glance.Client.assert_called_once_with('1', **kw)
            self.assertEqual(self.clients.cache["glance"], fake_glance)

    def test_get_cinder_client(self):
        with mock.patch('rally.osclients.cinder') as mock_cinder:
            fake_cinder = FakeCinder()
            mock_cinder.Client = mock.MagicMock(return_value=fake_cinder)
            self.assertTrue("cinder" not in self.clients.cache)
            client = self.clients.get_cinder_client()
            self.assertEqual(client, fake_cinder)
            mock_cinder.Client.assert_called_once_with('1', *self.args[:3],
                                                       auth_url=self.args[-1],
                                                       service_type='volume')
            self.assertEqual(self.clients.cache["cinder"], fake_cinder)
