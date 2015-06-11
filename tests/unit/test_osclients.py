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


from keystoneclient import exceptions as keystone_exceptions
import mock
from oslo_config import cfg

from rally import consts
from rally import exceptions
from rally import objects
from rally import osclients
from tests.unit import fakes
from tests.unit import test


class CachedTestCase(test.TestCase):

    def test_cached(self):
        foo_client = mock.Mock(
            __name__="foo_client",
            side_effect=lambda ins, *args, **kw: (args, kw))
        ins = mock.Mock(cache={})
        cached = osclients.cached(foo_client)
        self.assertEqual(((), {}), cached(ins))
        self.assertEqual({"foo_client": ((), {})}, ins.cache)
        self.assertEqual((("foo",), {"bar": "spam"}),
                         cached(ins, "foo", bar="spam"))
        self.assertEqual(
            {"foo_client": ((), {}),
             "foo_client('foo',){'bar': 'spam'}": (("foo",),
                                                   {"bar": "spam"})},
            ins.cache)
        ins.cache["foo_client('foo',){'bar': 'spam'}"] = "foo_cached"
        self.assertEqual(
            "foo_cached", cached(ins, "foo", bar="spam"))


class TestCreateKeystoneClient(test.TestCase):

    def setUp(self):
        super(TestCreateKeystoneClient, self).setUp()
        self.kwargs = {"auth_url": "http://auth_url", "username": "user",
                       "password": "password", "tenant_name": "tenant",
                       "https_insecure": False, "https_cacert": None}

    def test_create_keystone_client_v2(self):
        mock_keystone = mock.MagicMock()
        fake_keystoneclient = mock.MagicMock()
        mock_keystone.v2_0.client.Client.return_value = fake_keystoneclient
        mock_discover = mock.MagicMock(
            version_data=mock.MagicMock(return_value=[{"version": [2]}]))
        mock_keystone.discover.Discover.return_value = mock_discover
        with mock.patch.dict("sys.modules",
                             {"keystoneclient": mock_keystone,
                              "keystoneclient.v2_0": mock_keystone.v2_0}):
            client = osclients.create_keystone_client(self.kwargs)
            mock_discover.version_data.assert_called_once_with()
            self.assertEqual(fake_keystoneclient, client)
            mock_keystone.v2_0.client.Client.assert_called_once_with(
                **self.kwargs)

    def test_create_keystone_client_v3(self):
        mock_keystone = mock.MagicMock()
        fake_keystoneclient = mock.MagicMock()
        mock_keystone.v3.client.Client.return_value = fake_keystoneclient
        mock_discover = mock.MagicMock(
            version_data=mock.MagicMock(return_value=[{"version": [3]}]))
        mock_keystone.discover.Discover.return_value = mock_discover
        with mock.patch.dict("sys.modules",
                             {"keystoneclient": mock_keystone,
                              "keystoneclient.v3": mock_keystone.v3}):
            client = osclients.create_keystone_client(self.kwargs)
            mock_discover.version_data.assert_called_once_with()
            self.assertEqual(fake_keystoneclient, client)
            mock_keystone.v3.client.Client.assert_called_once_with(
                **self.kwargs)

    def test_create_keystone_client_version_not_found(self):
        mock_keystone = mock.MagicMock()
        mock_discover = mock.MagicMock(
            version_data=mock.MagicMock(return_value=[{"version": [100500]}]))
        mock_keystone.discover.Discover.return_value = mock_discover
        with mock.patch.dict("sys.modules", {"keystoneclient": mock_keystone}):
            self.assertRaises(exceptions.RallyException,
                              osclients.create_keystone_client, self.kwargs)
            mock_discover.version_data.assert_called_once_with()


class OSClientsTestCase(test.TestCase):

    def setUp(self):
        super(OSClientsTestCase, self).setUp()
        self.endpoint = objects.Endpoint("http://auth_url", "use", "pass",
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

    def test_create_from_env(self):
        with mock.patch.dict("os.environ",
                             {"OS_AUTH_URL": "foo_auth_url",
                              "OS_USERNAME": "foo_username",
                              "OS_PASSWORD": "foo_password",
                              "OS_TENANT_NAME": "foo_tenant_name",
                              "OS_REGION_NAME": "foo_region_name"}):
            clients = osclients.Clients.create_from_env()

        self.assertEqual("foo_auth_url", clients.endpoint.auth_url)
        self.assertEqual("foo_username", clients.endpoint.username)
        self.assertEqual("foo_password", clients.endpoint.password)
        self.assertEqual("foo_tenant_name", clients.endpoint.tenant_name)
        self.assertEqual("foo_region_name", clients.endpoint.region_name)

    def test_keystone(self):
        self.assertNotIn("keystone", self.clients.cache)
        client = self.clients.keystone()
        self.assertEqual(client, self.fake_keystone)
        endpoint = {"timeout": cfg.CONF.openstack_client_http_timeout,
                    "insecure": False, "cacert": None}
        kwargs = self.endpoint.to_dict()
        kwargs.update(endpoint.items())
        self.mock_create_keystone_client.assert_called_once_with(kwargs)
        self.assertEqual(self.fake_keystone, self.clients.cache["keystone"])

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
        fake_nova = fakes.FakeNovaClient()
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = fake_nova
        self.assertNotIn("nova", self.clients.cache)
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            client = self.clients.nova()
            self.assertEqual(fake_nova, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="compute",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_nova.client.Client.assert_called_once_with(
                "2",
                auth_token=self.fake_keystone.auth_token,
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None,
                username=self.endpoint.username,
                api_key=self.endpoint.password,
                project_id=self.endpoint.tenant_name,
                auth_url=self.endpoint.auth_url)
            client.set_management_url.assert_called_once_with(
                self.service_catalog.url_for.return_value)
            self.assertEqual(fake_nova, self.clients.cache["nova"])

    def test_neutron(self):
        fake_neutron = fakes.FakeNeutronClient()
        mock_neutron = mock.MagicMock()
        mock_neutron.client.Client.return_value = fake_neutron
        self.assertNotIn("neutron", self.clients.cache)
        with mock.patch.dict("sys.modules", {"neutronclient.neutron":
                                             mock_neutron}):
            client = self.clients.neutron()
            self.assertEqual(fake_neutron, client)
            kw = {
                "token": self.fake_keystone.auth_token,
                "endpoint_url": self.service_catalog.url_for.return_value,
                "timeout": cfg.CONF.openstack_client_http_timeout,
                "insecure": self.endpoint.insecure,
                "ca_cert": self.endpoint.cacert,
                "username": self.endpoint.username,
                "password": self.endpoint.password,
                "tenant_name": self.endpoint.tenant_name,
                "auth_url": self.endpoint.auth_url
            }
            self.service_catalog.url_for.assert_called_once_with(
                service_type="network",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_neutron.client.Client.assert_called_once_with("2.0", **kw)
            self.assertEqual(fake_neutron, self.clients.cache["neutron"])

    def test_glance(self):
        fake_glance = fakes.FakeGlanceClient()
        mock_glance = mock.MagicMock()
        mock_glance.Client = mock.MagicMock(return_value=fake_glance)
        with mock.patch.dict("sys.modules", {"glanceclient": mock_glance}):
            self.assertNotIn("glance", self.clients.cache)
            client = self.clients.glance()
            self.assertEqual(fake_glance, client)
            kw = {"endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None}
            self.service_catalog.url_for.assert_called_once_with(
                service_type="image",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_glance.Client.assert_called_once_with("1", **kw)
            self.assertEqual(fake_glance, self.clients.cache["glance"])

    def test_cinder(self):
        fake_cinder = mock.MagicMock(client=fakes.FakeCinderClient())
        mock_cinder = mock.MagicMock()
        mock_cinder.client.Client.return_value = fake_cinder
        self.assertNotIn("cinder", self.clients.cache)
        with mock.patch.dict("sys.modules", {"cinderclient": mock_cinder}):
            client = self.clients.cinder()
            self.assertEqual(fake_cinder, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="volume",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_cinder.client.Client.assert_called_once_with(
                "1",
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None,
                username=self.endpoint.username,
                api_key=self.endpoint.password,
                project_id=self.endpoint.tenant_name,
                auth_url=self.endpoint.auth_url)
            self.assertEqual(fake_cinder.client.management_url,
                             self.service_catalog.url_for.return_value)
            self.assertEqual(fake_cinder.client.auth_token,
                             self.fake_keystone.auth_token)
            self.assertEqual(fake_cinder, self.clients.cache["cinder"])

    def test_manila(self):
        mock_manila = mock.MagicMock()
        self.assertNotIn("manila", self.clients.cache)
        with mock.patch.dict("sys.modules", {"manilaclient": mock_manila}):
            client = self.clients.manila()
            self.assertEqual(mock_manila.client.Client.return_value, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="share",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            mock_manila.client.Client.assert_called_once_with(
                "1",
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None,
                username=self.endpoint.username,
                api_key=self.endpoint.password,
                region_name=self.endpoint.region_name,
                project_name=self.endpoint.tenant_name,
                auth_url=self.endpoint.auth_url)
            self.assertEqual(
                mock_manila.client.Client.return_value.client.management_url,
                self.service_catalog.url_for.return_value)
            self.assertEqual(
                mock_manila.client.Client.return_value.client.auth_token,
                self.fake_keystone.auth_token)
            self.assertEqual(
                mock_manila.client.Client.return_value,
                self.clients.cache["manila"])

    def test_ceilometer(self):
        fake_ceilometer = fakes.FakeCeilometerClient()
        mock_ceilometer = mock.MagicMock()
        mock_ceilometer.client.get_client = mock.MagicMock(
            return_value=fake_ceilometer)
        self.assertNotIn("ceilometer", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"ceilometerclient": mock_ceilometer}):
            client = self.clients.ceilometer()
            self.assertEqual(fake_ceilometer, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="metering",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            kw = {"os_endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None,
                  "username": self.endpoint.username,
                  "password": self.endpoint.password,
                  "tenant_name": self.endpoint.tenant_name,
                  "auth_url": self.endpoint.auth_url
                  }
            mock_ceilometer.client.get_client.assert_called_once_with("2",
                                                                      **kw)
            self.assertEqual(fake_ceilometer,
                             self.clients.cache["ceilometer"])

    def test_ironic(self):
        fake_ironic = fakes.FakeIronicClient()
        mock_ironic = mock.MagicMock()
        mock_ironic.client.get_client = mock.MagicMock(
            return_value=fake_ironic)
        self.assertNotIn("ironic", self.clients.cache)
        with mock.patch.dict("sys.modules", {"ironicclient": mock_ironic}):
            client = self.clients.ironic()
            self.assertEqual(fake_ironic, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="baremetal",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            kw = {
                "os_auth_token": self.fake_keystone.auth_token,
                "ironic_url": self.service_catalog.url_for.return_value,
                "timeout": cfg.CONF.openstack_client_http_timeout,
                "insecure": self.endpoint.insecure,
                "cacert": self.endpoint.cacert
            }
            mock_ironic.client.get_client.assert_called_once_with("1.0", **kw)
            self.assertEqual(fake_ironic, self.clients.cache["ironic"])

    def test_sahara(self):
        fake_sahara = fakes.FakeSaharaClient()
        mock_sahara = mock.MagicMock()
        mock_sahara.client.Client = mock.MagicMock(return_value=fake_sahara)
        self.assertNotIn("sahara", self.clients.cache)
        with mock.patch.dict("sys.modules", {"saharaclient": mock_sahara}):
            client = self.clients.sahara()
            self.assertEqual(fake_sahara, client)
            kw = {
                "username": self.endpoint.username,
                "api_key": self.endpoint.password,
                "project_name": self.endpoint.tenant_name,
                "auth_url": self.endpoint.auth_url
            }
            mock_sahara.client.Client.assert_called_once_with("1.1", **kw)
            self.assertEqual(fake_sahara, self.clients.cache["sahara"])

    def test_zaqar(self):
        fake_zaqar = fakes.FakeZaqarClient()
        mock_zaqar = mock.MagicMock()
        mock_zaqar.client.Client = mock.MagicMock(return_value=fake_zaqar)
        self.assertNotIn("zaqar", self.clients.cache)
        with mock.patch.dict("sys.modules", {"zaqarclient.queues":
                                             mock_zaqar}):
            client = self.clients.zaqar()
            self.assertEqual(fake_zaqar, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="messaging",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            fake_zaqar_url = self.service_catalog.url_for.return_value
            conf = {"auth_opts": {"backend": "keystone", "options": {
                "os_username": self.endpoint.username,
                "os_password": self.endpoint.password,
                "os_project_name": self.endpoint.tenant_name,
                "os_project_id": self.fake_keystone.auth_tenant_id,
                "os_auth_url": self.endpoint.auth_url,
                "insecure": self.endpoint.insecure,
            }}}
            mock_zaqar.client.Client.assert_called_once_with(
                url=fake_zaqar_url, version=1.1, conf=conf)
            self.assertEqual(fake_zaqar, self.clients.cache["zaqar"])

    def test_trove(self):
        fake_trove = fakes.FakeTroveClient()
        mock_trove = mock.MagicMock()
        mock_trove.client.Client = mock.MagicMock(return_value=fake_trove)
        self.assertNotIn("trove", self.clients.cache)
        with mock.patch.dict("sys.modules", {"troveclient": mock_trove}):
            client = self.clients.trove()
            self.assertEqual(fake_trove, client)
            kw = {
                "username": self.endpoint.username,
                "api_key": self.endpoint.password,
                "project_id": self.endpoint.tenant_name,
                "auth_url": self.endpoint.auth_url,
                "region_name": self.endpoint.region_name,
                "timeout": cfg.CONF.openstack_client_http_timeout,
                "insecure": self.endpoint.insecure,
                "cacert": self.endpoint.cacert
            }
            mock_trove.client.Client.assert_called_once_with("1.0", **kw)
            self.assertEqual(fake_trove, self.clients.cache["trove"])

    def test_mistral(self):
        fake_mistral = fakes.FakeMistralClient()
        mock_mistral = mock.Mock()
        mock_mistral.client.client.return_value = fake_mistral

        self.assertNotIn("mistral", self.clients.cache)
        with mock.patch.dict(
                "sys.modules", {"mistralclient": mock_mistral,
                                "mistralclient.api": mock_mistral}):
            client = self.clients.mistral()
            self.assertEqual(fake_mistral, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="workflowv2",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name
            )
            fake_mistral_url = self.service_catalog.url_for.return_value
            mock_mistral.client.client.assert_called_once_with(
                mistral_url=fake_mistral_url,
                service_type="workflowv2",
                auth_token=self.fake_keystone.auth_token
            )
            self.assertEqual(fake_mistral, self.clients.cache["mistral"])

    def test_swift(self):
        fake_swift = fakes.FakeSwiftClient()
        mock_swift = mock.MagicMock()
        mock_swift.client.Connection = mock.MagicMock(return_value=fake_swift)
        self.assertNotIn("swift", self.clients.cache)
        with mock.patch.dict("sys.modules", {"swiftclient": mock_swift}):
            client = self.clients.swift()
            self.assertEqual(client, fake_swift)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="object-store",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            kw = {"retries": 1,
                  "preauthurl": self.service_catalog.url_for.return_value,
                  "preauthtoken": self.fake_keystone.auth_token,
                  "insecure": False,
                  "cacert": None,
                  "user": self.endpoint.username,
                  "key": self.endpoint.password,
                  "tenant_name": self.endpoint.tenant_name,
                  "authurl": self.endpoint.auth_url
                  }
            mock_swift.client.Connection.assert_called_once_with(**kw)
            self.assertEqual(self.clients.cache["swift"], fake_swift)

    def test_ec2(self):
        mock_boto = mock.Mock()
        self.service_catalog.url_for.return_value = "http://fake.to:1/fake"
        self.fake_keystone.ec2 = mock.Mock()
        self.fake_keystone.ec2.create.return_value = mock.Mock(
            access="fake_access", secret="fake_secret")
        fake_ec2 = fakes.FakeEC2Client()
        mock_boto.connect_ec2_endpoint.return_value = fake_ec2

        self.assertNotIn("ec2", self.clients.cache)
        with mock.patch.dict("sys.modules", {"boto": mock_boto}):
            client = self.clients.ec2()
            self.assertEqual(fake_ec2, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="ec2",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name)
            kw = {
                "url": "http://fake.to:1/fake",
                "aws_access_key_id": "fake_access",
                "aws_secret_access_key": "fake_secret",
                "is_secure": self.endpoint.insecure,
            }
            mock_boto.connect_ec2_endpoint.assert_called_once_with(**kw)
            self.assertEqual(fake_ec2, self.clients.cache["ec2"])

    @mock.patch("rally.osclients.Clients.keystone")
    def test_services(self, mock_keystone):
        available_services = {consts.ServiceType.IDENTITY: {},
                              consts.ServiceType.COMPUTE: {},
                              "unknown_service": {}}
        mock_keystone.return_value = mock.Mock(service_catalog=mock.Mock(
            get_endpoints=lambda: available_services))
        clients = osclients.Clients(self.endpoint)

        self.assertEqual(
            {consts.ServiceType.IDENTITY: consts.Service.KEYSTONE,
             consts.ServiceType.COMPUTE: consts.Service.NOVA},
            clients.services())

    def test_murano(self):
        fake_murano = fakes.FakeMuranoClient()
        mock_murano = mock.Mock()
        mock_murano.client.Client.return_value = fake_murano
        self.assertNotIn("murano", self.clients.cache)
        with mock.patch.dict("sys.modules", {"muranoclient": mock_murano}):
            client = self.clients.murano()
            self.assertEqual(fake_murano, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="application_catalog",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.endpoint.region_name
            )
            kw = {"endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token}
            mock_murano.client.Client.assert_called_once_with("1", **kw)
            self.assertEqual(fake_murano, self.clients.cache["murano"])

    @mock.patch("rally.osclients.cached")
    def test_register(self, mock_cached):
        client_func = mock.Mock(return_value="foo_client")
        cached_client_func = mock.Mock(return_value="cached_foo_client")
        mock_cached.return_value = cached_client_func
        clients = osclients.Clients(mock.Mock())

        self.assertFalse(hasattr(clients, "foo"))

        func = osclients.Clients.register("foo")(client_func)

        mock_cached.assert_called_once_with(client_func)
        self.assertEqual("cached_foo_client", clients.foo())
        self.assertEqual(client_func, func)
        self.assertEqual(cached_client_func, clients.foo)

        # Call second time with same name
        self.assertRaises(ValueError,
                          osclients.Clients.register("foo"), client_func)
