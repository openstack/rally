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

from keystoneclient import exceptions as keystone_exceptions
from oslo.config import cfg

from rally import exceptions
from rally.objects import endpoint
from rally import osclients
from tests import fakes
from tests import test


class OSClientsTestCase(test.TestCase):

    def setUp(self):
        super(OSClientsTestCase, self).setUp()
        self.endpoint = endpoint.Endpoint("http://auth_url", "use", "pass",
                                          "tenant")
        self.clients = osclients.Clients(self.endpoint)

    def test_keystone(self):
        with mock.patch("rally.osclients.keystone") as mock_keystone:
            fake_keystone = fakes.FakeKeystoneClient()
            mock_keystone.Client = mock.MagicMock(return_value=fake_keystone)
            self.assertTrue("keystone" not in self.clients.cache)
            client = self.clients.keystone()
            self.assertEqual(client, fake_keystone)
            endpoint = {"endpoint": "http://auth_url:35357",
                        "timeout": cfg.CONF.openstack_client_http_timeout,
                        "insecure": False, "cacert": None}
            kwargs = dict(self.endpoint.to_dict().items() + endpoint.items())
            mock_keystone.Client.assert_called_once_with(**kwargs)
            self.assertEqual(self.clients.cache["keystone"], fake_keystone)

    @mock.patch("rally.osclients.Clients.keystone")
    def test_verified_keystone_user_not_admin(self, mock_keystone):
        mock_keystone.return_value = fakes.FakeKeystoneClient()
        mock_keystone.return_value.auth_ref["user"]["roles"] = \
            [{"name": "notadmin"}]
        self.assertRaises(exceptions.InvalidAdminException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Clients.keystone")
    def test_verified_keystone_unauthorized(self, mock_keystone):
        mock_keystone.return_value = fakes.FakeKeystoneClient()
        mock_keystone.side_effect = keystone_exceptions.Unauthorized
        self.assertRaises(exceptions.InvalidEndpointsException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Clients.keystone")
    def test_verified_keystone_unreachable(self, mock_keystone):
        mock_keystone.return_value = fakes.FakeKeystoneClient()
        mock_keystone.side_effect = keystone_exceptions.AuthorizationFailure
        self.assertRaises(exceptions.HostUnreachableException,
                          self.clients.verified_keystone)

    def test_nova(self):
        with mock.patch("rally.osclients.nova") as mock_nova:
            fake_nova = fakes.FakeNovaClient()
            mock_nova.Client = mock.MagicMock(return_value=fake_nova)
            self.assertTrue("nova" not in self.clients.cache)
            client = self.clients.nova()
            self.assertEqual(client, fake_nova)
            mock_nova.Client.assert_called_once_with(
                "2", self.endpoint.username, self.endpoint.password,
                self.endpoint.tenant_name, auth_url=self.endpoint.auth_url,
                service_type="compute",
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None)
            self.assertEqual(self.clients.cache["nova"], fake_nova)

    @mock.patch("rally.osclients.neutron")
    def test_neutron(self, mock_neutron):
        fake_neutron = fakes.FakeNeutronClient()
        mock_neutron.Client = mock.MagicMock(return_value=fake_neutron)
        self.assertTrue("neutron" not in self.clients.cache)
        client = self.clients.neutron()
        self.assertEqual(client, fake_neutron)
        kw = {
            "username": self.endpoint.username,
            "password": self.endpoint.password,
            "tenant_name": self.endpoint.tenant_name,
            "auth_url": self.endpoint.auth_url,
            "timeout": cfg.CONF.openstack_client_http_timeout,
            "insecure": cfg.CONF.https_insecure,
            "cacert": cfg.CONF.https_cacert
        }
        mock_neutron.Client.assert_called_once_with("2.0", **kw)
        self.assertEqual(self.clients.cache["neutron"], fake_neutron)

    def test_glance(self):
        with mock.patch("rally.osclients.glance") as mock_glance:
            fake_glance = fakes.FakeGlanceClient()
            mock_glance.Client = mock.MagicMock(return_value=fake_glance)
            kc = fakes.FakeKeystoneClient()
            self.clients.keystone = mock.MagicMock(return_value=kc)
            self.assertTrue("glance" not in self.clients.cache)
            client = self.clients.glance()
            self.assertEqual(client, fake_glance)
            endpoint = kc.service_catalog.get_endpoints()["image"][0]

            kw = {"endpoint": endpoint["publicURL"],
                  "token": kc.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None}
            mock_glance.Client.assert_called_once_with("1", **kw)
            self.assertEqual(self.clients.cache["glance"], fake_glance)

    def test_cinder(self):
        with mock.patch("rally.osclients.cinder") as mock_cinder:
            fake_cinder = fakes.FakeCinderClient()
            mock_cinder.Client = mock.MagicMock(return_value=fake_cinder)
            self.assertTrue("cinder" not in self.clients.cache)
            client = self.clients.cinder()
            self.assertEqual(client, fake_cinder)
            mock_cinder.Client.assert_called_once_with(
                "1", self.endpoint.username, self.endpoint.password,
                self.endpoint.tenant_name, auth_url=self.endpoint.auth_url,
                service_type="volume",
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None)
            self.assertEqual(self.clients.cache["cinder"], fake_cinder)

    def test_ceilometer(self):
        with mock.patch("rally.osclients.ceilometer") as mock_ceilometer:
            fake_ceilometer = fakes.FakeCeilometerClient()
            mock_ceilometer.Client = mock.MagicMock(
                return_value=fake_ceilometer)
            self.assertTrue("ceilometer" not in self.clients.cache)
            client = self.clients.ceilometer()
            self.assertEqual(client, fake_ceilometer)
            kw = {"username": self.endpoint.username,
                  "password": self.endpoint.password,
                  "tenant_name": self.endpoint.tenant_name,
                  "endpoint": self.endpoint.auth_url,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None}
            mock_ceilometer.Client.assert_called_once_with("1", **kw)
            self.assertEqual(self.clients.cache["ceilometer"],
                             fake_ceilometer)
