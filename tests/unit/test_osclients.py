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

import urlparse

from keystoneclient import exceptions as keystone_exceptions
import mock
from oslo.config import cfg

from rally import consts
from rally import exceptions
from rally.objects import endpoint
from rally import osclients
from tests.unit import fakes
from tests.unit import test


class OSClientsTestCase(test.TestCase):

    def setUp(self):
        super(OSClientsTestCase, self).setUp()
        self.endpoint = endpoint.Endpoint("http://auth_url", "use", "pass",
                                          "tenant")
        self.clients = osclients.Clients(self.endpoint)

        self.fake_keystone = fakes.FakeKeystoneClient()
        self.fake_keystone.auth_token = mock.MagicMock()
        self.service_catalog = self.fake_keystone.service_catalog
        self.service_catalog.url_for = mock.MagicMock()

        keystone_patcher = mock.patch("rally.osclients.create_keystone_client")
        self.mock_create_keystone_client = keystone_patcher.start()
        self.addCleanup(keystone_patcher.stop)
        self.mock_create_keystone_client.return_value = self.fake_keystone

    def tearDown(self):
        super(OSClientsTestCase, self).tearDown()

    def test_keystone(self):
        self.assertTrue("keystone" not in self.clients.cache)
        client = self.clients.keystone()
        self.assertEqual(client, self.fake_keystone)
        mgmt_url = urlparse.urlparse(self.endpoint.auth_url)
        auth_url = "{0}://{1}:{2}{3}".format(mgmt_url.scheme,
                                             mgmt_url.hostname,
                                             self.endpoint.admin_port,
                                             mgmt_url.path)
        endpoint = {"timeout": cfg.CONF.openstack_client_http_timeout,
                    "insecure": False, "cacert": None,
                    "endpoint": auth_url}
        kwargs = dict(self.endpoint.to_dict().items() + endpoint.items())
        self.mock_create_keystone_client.assert_called_once_with(kwargs)
        self.assertEqual(self.clients.cache["keystone"], self.fake_keystone)

    @mock.patch("rally.osclients.Clients.keystone")
    def test_verified_keystone_user_not_admin(self, mock_keystone):
        mock_keystone.return_value = fakes.FakeKeystoneClient()
        mock_keystone.return_value.auth_ref.role_names = ["notadmin"]
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
            self.service_catalog.url_for.assert_called_once_with(
                service_type='compute',
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_nova.Client.assert_called_once_with(
                "2",
                auth_token=self.fake_keystone.auth_token,
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None)
            client.set_management_url.assert_called_once_with(
                self.service_catalog.url_for.return_value)
            self.assertEqual(self.clients.cache["nova"], fake_nova)

    @mock.patch("rally.osclients.neutron")
    def test_neutron(self, mock_neutron):
        fake_neutron = fakes.FakeNeutronClient()
        mock_neutron.Client = mock.MagicMock(return_value=fake_neutron)
        self.assertTrue("neutron" not in self.clients.cache)
        client = self.clients.neutron()
        self.assertEqual(client, fake_neutron)
        kw = {
            "token": self.fake_keystone.auth_token,
            "endpoint_url": self.service_catalog.url_for.return_value,
            "timeout": cfg.CONF.openstack_client_http_timeout,
            "insecure": cfg.CONF.https_insecure,
            "ca_cert": cfg.CONF.https_cacert
        }
        self.service_catalog.url_for.assert_called_once_with(
            service_type='network', endpoint_type=consts.EndpointType.PUBLIC,
            region_name=self.endpoint.region_name)
        mock_neutron.Client.assert_called_once_with("2.0", **kw)
        self.assertEqual(self.clients.cache["neutron"], fake_neutron)

    def test_glance(self):
        with mock.patch("rally.osclients.glance") as mock_glance:
            fake_glance = fakes.FakeGlanceClient()
            mock_glance.Client = mock.MagicMock(return_value=fake_glance)
            self.assertTrue("glance" not in self.clients.cache)
            client = self.clients.glance()
            self.assertEqual(client, fake_glance)
            kw = {"endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None}
            self.service_catalog.url_for.assert_called_once_with(
                service_type='image',
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_glance.Client.assert_called_once_with("1", **kw)
            self.assertEqual(self.clients.cache["glance"], fake_glance)

    def test_cinder(self):
        with mock.patch("rally.osclients.cinder") as mock_cinder:
            fake_cinder = fakes.FakeCinderClient()
            fake_cinder.client = mock.MagicMock()
            mock_cinder.Client = mock.MagicMock(return_value=fake_cinder)
            self.assertTrue("cinder" not in self.clients.cache)
            client = self.clients.cinder()
            self.assertEqual(client, fake_cinder)
            self.service_catalog.url_for.assert_called_once_with(
                service_type='volume',
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_cinder.Client.assert_called_once_with(
                "1", None, None, http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None)
            self.assertEqual(fake_cinder.client.management_url,
                             self.service_catalog.url_for.return_value)
            self.assertEqual(fake_cinder.client.auth_token,
                             self.fake_keystone.auth_token)
            self.assertEqual(self.clients.cache["cinder"], fake_cinder)

    def test_ceilometer(self):
        with mock.patch("rally.osclients.ceilometer") as mock_ceilometer:
            fake_ceilometer = fakes.FakeCeilometerClient()
            mock_ceilometer.Client = mock.MagicMock(
                return_value=fake_ceilometer)
            self.assertTrue("ceilometer" not in self.clients.cache)
            client = self.clients.ceilometer()
            self.assertEqual(client, fake_ceilometer)
            self.service_catalog.url_for.assert_called_once_with(
                service_type='metering',
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            kw = {"endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None}
            mock_ceilometer.Client.assert_called_once_with("2", **kw)
            self.assertEqual(self.clients.cache["ceilometer"],
                             fake_ceilometer)

    @mock.patch("rally.osclients.ironic")
    def test_ironic(self, mock_ironic):
        fake_ironic = fakes.FakeIronicClient()
        mock_ironic.get_client = mock.MagicMock(return_value=fake_ironic)
        self.assertTrue("ironic" not in self.clients.cache)
        client = self.clients.ironic()
        self.assertEqual(client, fake_ironic)
        self.service_catalog.url_for.assert_called_once_with(
            service_type='baremetal',
            endpoint_type=consts.EndpointType.PUBLIC,
            region_name=self.endpoint.region_name)
        kw = {
            "os_auth_token": self.fake_keystone.auth_token,
            "ironic_url": self.service_catalog.url_for.return_value,
            "timeout": cfg.CONF.openstack_client_http_timeout,
            "insecure": cfg.CONF.https_insecure,
            "cacert": cfg.CONF.https_cacert
        }
        mock_ironic.get_client.assert_called_once_with("1.0", **kw)
        self.assertEqual(self.clients.cache["ironic"], fake_ironic)

    @mock.patch("rally.osclients.sahara")
    def test_sahara(self, mock_sahara):
        fake_sahara = fakes.FakeSaharaClient()
        mock_sahara.Client = mock.MagicMock(return_value=fake_sahara)
        self.assertTrue("sahara" not in self.clients.cache)
        client = self.clients.sahara()
        self.assertEqual(client, fake_sahara)
        kw = {
            "username": self.endpoint.username,
            "api_key": self.endpoint.password,
            "project_name": self.endpoint.tenant_name,
            "auth_url": self.endpoint.auth_url
        }
        mock_sahara.Client.assert_called_once_with("1.1", **kw)
        self.assertEqual(self.clients.cache["sahara"], fake_sahara)

    @mock.patch("rally.osclients.zaqar")
    def test_zaqar(self, mock_zaqar):
        fake_zaqar = fakes.FakeZaqarClient()
        mock_zaqar.Client = mock.MagicMock(return_value=fake_zaqar)
        self.assertTrue("zaqar" not in self.clients.cache)
        client = self.clients.zaqar()
        self.assertEqual(client, fake_zaqar)
        self.service_catalog.url_for.assert_called_once_with(
            service_type='messaging',
            endpoint_type=consts.EndpointType.PUBLIC,
            region_name=self.endpoint.region_name)
        fake_zaqar_url = self.service_catalog.url_for.return_value
        conf = {'auth_opts': {'backend': 'keystone', 'options': {
            'os_username': self.endpoint.username,
            'os_password': self.endpoint.password,
            'os_project_name': self.endpoint.tenant_name,
            'os_auth_url': self.endpoint.auth_url,
            'insecure': cfg.CONF.https_insecure,
        }}}
        mock_zaqar.Client.assert_called_once_with(url=fake_zaqar_url,
                                                  version=1.1,
                                                  conf=conf)
        self.assertEqual(self.clients.cache["zaqar"], fake_zaqar)

    @mock.patch("rally.osclients.Clients.keystone")
    def test_services(self, mock_keystone):
        available_services = {consts.ServiceType.IDENTITY: {},
                              consts.ServiceType.COMPUTE: {},
                              'unknown_service': {}
                              }
        mock_keystone.return_value = mock.Mock(service_catalog=mock.Mock(
                get_endpoints=lambda: available_services))
        clients = osclients.Clients({})

        self.assertEqual(
            clients.services(), {
                consts.ServiceType.IDENTITY: consts.Service.KEYSTONE,
                consts.ServiceType.COMPUTE: consts.Service.NOVA})
