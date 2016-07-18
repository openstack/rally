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

import ddt
from keystoneclient.auth import token_endpoint
from keystoneclient import exceptions as keystone_exceptions
import mock
from oslo_config import cfg
from testtools import matchers

from rally.common import objects
from rally import consts
from rally import exceptions
from rally import osclients
from tests.unit import fakes
from tests.unit import test


@osclients.configure("dummy")
class DummyClient(osclients.OSClient):
    def create_client(self, *args, **kwargs):
        pass


class OSClientTestCase(test.TestCase):
    def test_choose_service_type(self):
        default_service_type = "default_service_type"

        @osclients.configure("test_choose_service_type",
                             default_service_type=default_service_type)
        class FakeClient(osclients.OSClient):
            create_client = mock.MagicMock()

        fake_client = FakeClient(mock.MagicMock(), {}, {})
        self.assertEqual(default_service_type,
                         fake_client.choose_service_type())
        self.assertEqual("foo",
                         fake_client.choose_service_type("foo"))


class CachedTestCase(test.TestCase):

    def test_cached(self):
        clients = osclients.Clients(mock.MagicMock())
        client_name = "CachedTestCase.test_cached"
        fake_client = osclients.configure(client_name)(
            osclients.OSClient(clients.credential, clients.api_info,
                               clients.cache))
        fake_client.create_client = mock.MagicMock()

        self.assertEqual({}, clients.cache)
        fake_client()
        self.assertEqual(
            {client_name: fake_client.create_client.return_value},
            clients.cache)
        fake_client.create_client.assert_called_once_with()
        fake_client()
        fake_client.create_client.assert_called_once_with()
        fake_client("2")
        self.assertEqual(
            {client_name: fake_client.create_client.return_value,
             "%s('2',)" % client_name: fake_client.create_client.return_value},
            clients.cache)
        clients.clear()
        self.assertEqual({}, clients.cache)


class TestCreateKeystoneClient(test.TestCase):

    def make_auth_args(self):
        auth_kwargs = {
            "auth_url": "http://auth_url", "username": "user",
            "password": "password", "tenant_name": "tenant",
            "domain_name": "domain", "project_name": "project_name",
            "project_domain_name": "project_domain_name",
            "user_domain_name": "user_domain_name",
        }
        kwargs = {"https_insecure": False, "https_cacert": None}
        kwargs.update(auth_kwargs)
        return auth_kwargs, kwargs

    def set_up_keystone_mocks(self):
        self.ksc_module = mock.MagicMock()
        self.ksc_client = mock.MagicMock()
        self.ksc_identity = mock.MagicMock()
        self.ksc_password = mock.MagicMock()
        self.ksc_session = mock.MagicMock()
        self.ksc_auth = mock.MagicMock()
        self.patcher = mock.patch.dict("sys.modules",
                                       {"keystoneclient": self.ksc_module,
                                        "keystoneclient.auth": self.ksc_auth})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.ksc_module.client = self.ksc_client
        self.ksc_auth.identity = self.ksc_identity
        self.ksc_auth.identity.Password = self.ksc_password
        self.ksc_module.session = self.ksc_session

    def test_create_keystone_client(self):
        # NOTE(bigjools): This is a very poor testing strategy as it
        # tightly couples the test implementation to the tested
        # function's implementation. Ideally, we'd use a fake keystone
        # but all that's happening here is that it's checking the right
        # parameters were passed to the various parts that create a
        # client. Hopefully one day we'll get a real fake from the
        # keystone guys.
        self.set_up_keystone_mocks()
        auth_kwargs, all_kwargs = self.make_auth_args()
        keystone = osclients.Keystone(
            mock.MagicMock(), mock.sentinel, mock.sentinel)
        client = keystone._create_keystone_client(all_kwargs)

        self.ksc_password.assert_called_once_with(**auth_kwargs)
        self.ksc_session.Session.assert_called_once_with(
            auth=self.ksc_identity.Password(), timeout=mock.ANY,
            verify=mock.ANY)
        self.ksc_client.Client.assert_called_once_with(
            version=None, **all_kwargs)
        self.assertIs(client, self.ksc_client.Client())

    def test_client_is_pre_authed(self):
        # The client needs to be pre-authed so that service_catalog
        # works. This is because when using sessions, lazy auth is done
        # in keystoneclient.
        self.set_up_keystone_mocks()
        _, all_kwargs = self.make_auth_args()
        keystone = osclients.Keystone(
            mock.MagicMock(), mock.sentinel, mock.sentinel)
        client = keystone._create_keystone_client(all_kwargs)
        auth_ref = getattr(client, "auth_ref", None)
        self.assertIsNot(auth_ref, None)
        self.ksc_client.Client.assert_called_once_with(
            version=None, **all_kwargs)
        self.assertIs(client, self.ksc_client.Client())

    def test_create_client_removes_url_path_if_version_specified(self):
        # If specifying a version on the client creation call, ensure
        # the auth_url is versionless and the version required is passed
        # into the Client() call.
        self.set_up_keystone_mocks()
        auth_kwargs, all_kwargs = self.make_auth_args()
        credential = objects.Credential(
            "http://auth_url/v2.0", "user", "pass", "tenant")
        keystone = osclients.Keystone(
            credential, {}, mock.MagicMock())
        client = keystone.create_client(version="3")

        self.assertIs(client, self.ksc_client.Client())
        called_with = self.ksc_client.Client.call_args_list[0][1]
        self.expectThat(
            called_with["auth_url"], matchers.Equals("http://auth_url/"))
        self.expectThat(called_with["version"], matchers.Equals("3"))

    def test_create_keystone_client_with_v2_url_omits_domain(self):
        # NOTE(bigjools): Test that domain-related info is not present
        # when forcing a v2 URL, because it breaks keystoneclient's
        # service discovery.
        self.set_up_keystone_mocks()
        auth_kwargs, all_kwargs = self.make_auth_args()

        all_kwargs["auth_url"] = "http://auth_url/v2.0"
        auth_kwargs["auth_url"] = all_kwargs["auth_url"]
        keystone = osclients.Keystone(
            mock.MagicMock(), mock.sentinel, mock.sentinel)
        client = keystone._create_keystone_client(all_kwargs)

        auth_kwargs.pop("user_domain_name")
        auth_kwargs.pop("project_domain_name")
        auth_kwargs.pop("domain_name")
        self.ksc_password.assert_called_once_with(**auth_kwargs)
        self.ksc_session.Session.assert_called_once_with(
            auth=self.ksc_identity.Password(), timeout=mock.ANY,
            verify=mock.ANY)
        self.ksc_client.Client.assert_called_once_with(
            version=None, **all_kwargs)
        self.assertIs(client, self.ksc_client.Client())

    def test_create_keystone_client_with_v2_version_omits_domain(self):
        self.set_up_keystone_mocks()
        auth_kwargs, all_kwargs = self.make_auth_args()

        all_kwargs["auth_url"] = "http://auth_url/"
        auth_kwargs["auth_url"] = all_kwargs["auth_url"]
        keystone = osclients.Keystone(
            mock.MagicMock(), mock.sentinel, mock.sentinel)
        client = keystone._create_keystone_client(all_kwargs, version="2")

        auth_kwargs.pop("user_domain_name")
        auth_kwargs.pop("project_domain_name")
        auth_kwargs.pop("domain_name")
        self.ksc_password.assert_called_once_with(**auth_kwargs)
        self.ksc_session.Session.assert_called_once_with(
            auth=self.ksc_identity.Password(), timeout=mock.ANY,
            verify=mock.ANY)
        self.ksc_client.Client.assert_called_once_with(
            version="2", **all_kwargs)
        self.assertIs(client, self.ksc_client.Client())


@ddt.ddt
class OSClientsTestCase(test.TestCase):

    def setUp(self):
        super(OSClientsTestCase, self).setUp()
        self.credential = objects.Credential("http://auth_url/v2.0", "use",
                                             "pass", "tenant")
        self.clients = osclients.Clients(self.credential, {})

        self.fake_keystone = fakes.FakeKeystoneClient()
        self.fake_keystone.auth_token = mock.MagicMock()
        self.service_catalog = self.fake_keystone.service_catalog
        self.service_catalog.url_for = mock.MagicMock()

        keystone_patcher = mock.patch(
            "rally.osclients.Keystone._create_keystone_client")
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

        self.assertEqual("foo_auth_url", clients.credential.auth_url)
        self.assertEqual("foo_username", clients.credential.username)
        self.assertEqual("foo_password", clients.credential.password)
        self.assertEqual("foo_tenant_name", clients.credential.tenant_name)
        self.assertEqual("foo_region_name", clients.credential.region_name)

    @mock.patch.object(DummyClient, "_get_endpoint")
    @mock.patch("keystoneclient.session.Session")
    def test_get_session(self, mock_session, mock_dummy_client__get_endpoint):
        # Use DummyClient since if not the abc meta kicks in
        osc = DummyClient(self.credential, {}, {})

        with mock.patch.object(token_endpoint, "Token") as token:
            osc._get_session()

            token.assert_called_once_with(
                mock_dummy_client__get_endpoint.return_value,
                self.fake_keystone.auth_token
            )
            mock_session.assert_called_once_with(
                auth=token.return_value, verify=not self.credential.insecure,
                timeout=cfg.CONF.openstack_client_http_timeout)

    @mock.patch.object(DummyClient, "_get_endpoint")
    @mock.patch("keystoneclient.session.Session")
    def test_get_session_with_endpoint(
            self, mock_session, mock_dummy_client__get_endpoint):
        # Use DummyClient since if not the abc meta kicks in
        osc = DummyClient(self.credential, {}, {})

        fake_endpoint = mock.Mock()
        with mock.patch.object(token_endpoint, "Token") as token:
            osc._get_session(endpoint=fake_endpoint)

            self.assertFalse(mock_dummy_client__get_endpoint.called)

            token.assert_called_once_with(
                fake_endpoint,
                self.fake_keystone.auth_token
            )
            mock_session.assert_called_once_with(
                auth=token.return_value, verify=not self.credential.insecure,
                timeout=cfg.CONF.openstack_client_http_timeout)

    @mock.patch("keystoneclient.session.Session")
    def test_get_session_with_auth(self, mock_session):
        # Use DummyClient since if not the abc meta kicks in
        osc = DummyClient(self.credential, {}, {})

        fake_auth = mock.Mock()
        osc._get_session(auth=fake_auth)

        mock_session.assert_called_once_with(
            auth=fake_auth, verify=not self.credential.insecure,
            timeout=cfg.CONF.openstack_client_http_timeout)

    @mock.patch("keystoneclient.session.Session")
    def test_get_session_with_ca(self, mock_session):
        # Use DummyClient since if not the abc meta kicks in
        osc = DummyClient(self.credential, {}, {})

        self.credential.cacert = "/fake/ca"
        fake_auth = mock.Mock()
        osc._get_session(auth=fake_auth)

        mock_session.assert_called_once_with(
            auth=fake_auth, verify="/fake/ca",
            timeout=cfg.CONF.openstack_client_http_timeout)

    def test_keystone(self):
        self.assertNotIn("keystone", self.clients.cache)
        client = self.clients.keystone()
        self.assertEqual(client, self.fake_keystone)
        credential = {"timeout": cfg.CONF.openstack_client_http_timeout,
                      "insecure": False, "cacert": None}
        kwargs = self.credential.to_dict()
        kwargs.update(credential.items())
        self.mock_create_keystone_client.assert_called_once_with(
            kwargs, version=None)
        self.assertEqual(self.fake_keystone, self.clients.cache["keystone"])

    @mock.patch("rally.osclients.Keystone.create_client")
    def test_verified_keystone_user_not_admin(self,
                                              mock_keystone_create_client):
        # naming rule for mocks sucks
        mock_keystone = mock_keystone_create_client
        mock_keystone.return_value = fakes.FakeKeystoneClient()
        mock_keystone.return_value.auth_ref.role_names = ["notadmin"]
        self.assertRaises(exceptions.InvalidAdminException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Keystone.create_client")
    def test_verified_keystone_unauthorized(self, mock_keystone_create_client):
        mock_keystone_create_client.return_value = fakes.FakeKeystoneClient()
        mock_keystone_create_client.side_effect = (
            keystone_exceptions.Unauthorized)
        self.assertRaises(exceptions.InvalidEndpointsException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Keystone.create_client")
    def test_verified_keystone_unreachable(self, mock_keystone_create_client):
        mock_keystone_create_client.return_value = fakes.FakeKeystoneClient()
        mock_keystone_create_client.side_effect = (
            keystone_exceptions.AuthorizationFailure
        )
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
                region_name=self.credential.region_name)
            mock_nova.client.Client.assert_called_once_with(
                "2",
                auth_token=self.fake_keystone.auth_token,
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None,
                username=self.credential.username,
                api_key=self.credential.password,
                project_id=self.credential.tenant_name,
                auth_url=self.credential.auth_url)
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
                "insecure": self.credential.insecure,
                "ca_cert": self.credential.cacert,
                "username": self.credential.username,
                "password": self.credential.password,
                "tenant_name": self.credential.tenant_name,
                "auth_url": self.credential.auth_url
            }
            self.service_catalog.url_for.assert_called_once_with(
                service_type="network",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name)
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
                region_name=self.credential.region_name)
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
                service_type="volumev2",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name)
            mock_cinder.client.Client.assert_called_once_with(
                "2",
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None,
                username=self.credential.username,
                api_key=self.credential.password,
                project_id=self.credential.tenant_name,
                auth_url=self.credential.auth_url)
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
                region_name=self.credential.region_name)
            mock_manila.client.Client.assert_called_once_with(
                "1",
                http_log_debug=False,
                timeout=cfg.CONF.openstack_client_http_timeout,
                insecure=False, cacert=None,
                username=self.credential.username,
                api_key=self.credential.password,
                region_name=self.credential.region_name,
                project_name=self.credential.tenant_name,
                auth_url=self.credential.auth_url)
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
                region_name=self.credential.region_name)
            kw = {"os_endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None,
                  "username": self.credential.username,
                  "password": self.credential.password,
                  "tenant_name": self.credential.tenant_name,
                  "auth_url": self.credential.auth_url
                  }
            mock_ceilometer.client.get_client.assert_called_once_with("2",
                                                                      **kw)
            self.assertEqual(fake_ceilometer,
                             self.clients.cache["ceilometer"])

    def test_gnocchi(self):
        fake_gnocchi = fakes.FakeGnocchiClient()
        mock_gnocchi = mock.MagicMock()
        mock_gnocchi.client.Client.return_value = fake_gnocchi
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("gnocchi", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"gnocchiclient": mock_gnocchi,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.gnocchi()

            self.assertEqual(fake_gnocchi, client)
            kw = {"version": "1",
                  "session": mock_keystoneauth1.session.Session(),
                  "service_type": "metric"}
            mock_gnocchi.client.Client.assert_called_once_with(**kw)
            self.assertEqual(fake_gnocchi, self.clients.cache["gnocchi"])

    def test_monasca(self):
        fake_monasca = fakes.FakeMonascaClient()
        mock_monasca = mock.MagicMock()
        mock_monasca.client.Client.return_value = fake_monasca
        self.assertNotIn("monasca", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"monascaclient": mock_monasca}):
            client = self.clients.monasca()
            self.assertEqual(fake_monasca, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="monitoring",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name)
            os_endpoint = self.service_catalog.url_for.return_value
            kw = {"token": self.fake_keystone.auth_token,
                  "timeout": cfg.CONF.openstack_client_http_timeout,
                  "insecure": False, "cacert": None,
                  "username": self.credential.username,
                  "password": self.credential.password,
                  "tenant_name": self.credential.tenant_name,
                  "auth_url": self.credential.auth_url
                  }
            mock_monasca.client.Client.assert_called_once_with("2_0",
                                                               os_endpoint,
                                                               **kw)
            self.assertEqual(mock_monasca.client.Client.return_value,
                             self.clients.cache["monasca"])

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
                region_name=self.credential.region_name)
            kw = {
                "os_auth_token": self.fake_keystone.auth_token,
                "ironic_url": self.service_catalog.url_for.return_value,
                "timeout": cfg.CONF.openstack_client_http_timeout,
                "insecure": self.credential.insecure,
                "cacert": self.credential.cacert
            }
            mock_ironic.client.get_client.assert_called_once_with("1", **kw)
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
                "service_type": "data-processing",
                "endpoint_type": self.credential.endpoint_type,
                "insecure": False,
                "username": self.credential.username,
                "api_key": self.credential.password,
                "project_name": self.credential.tenant_name,
                "cacert": self.credential.cacert,
                "auth_url": self.credential.auth_url
            }
            mock_sahara.client.Client.assert_called_once_with(1.1, **kw)
            self.assertEqual(fake_sahara, self.clients.cache["sahara"])

    def test_zaqar(self):
        fake_zaqar = fakes.FakeZaqarClient()
        mock_zaqar = mock.MagicMock()
        mock_zaqar.client.Client = mock.MagicMock(return_value=fake_zaqar)
        self.assertNotIn("zaqar", self.clients.cache)
        p_id = self.fake_keystone.auth_ref.get("token").get("tenant").get("id")
        with mock.patch.dict("sys.modules", {"zaqarclient.queues":
                                             mock_zaqar}):
            client = self.clients.zaqar()
            self.assertEqual(fake_zaqar, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="messaging",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name)
            fake_zaqar_url = self.service_catalog.url_for.return_value
            conf = {"auth_opts": {"backend": "keystone", "options": {
                "os_username": self.credential.username,
                "os_password": self.credential.password,
                "os_project_name": self.credential.tenant_name,
                "os_project_id": p_id,
                "os_auth_url": self.credential.auth_url,
                "insecure": self.credential.insecure,
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
                "username": self.credential.username,
                "api_key": self.credential.password,
                "project_id": self.credential.tenant_name,
                "auth_url": self.credential.auth_url,
                "region_name": self.credential.region_name,
                "timeout": cfg.CONF.openstack_client_http_timeout,
                "insecure": self.credential.insecure,
                "cacert": self.credential.cacert
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
                region_name=self.credential.region_name
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
                region_name=self.credential.region_name)
            kw = {"retries": 1,
                  "preauthurl": self.service_catalog.url_for.return_value,
                  "preauthtoken": self.fake_keystone.auth_token,
                  "insecure": False,
                  "cacert": None,
                  "user": self.credential.username,
                  "tenant_name": self.credential.tenant_name,
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
                region_name=self.credential.region_name)
            kw = {
                "url": "http://fake.to:1/fake",
                "aws_access_key_id": "fake_access",
                "aws_secret_access_key": "fake_secret",
                "is_secure": self.credential.insecure,
            }
            mock_boto.connect_ec2_endpoint.assert_called_once_with(**kw)
            self.assertEqual(fake_ec2, self.clients.cache["ec2"])

    @mock.patch("rally.osclients.Keystone.create_client")
    def test_services(self, mock_keystone_create_client):
        available_services = {consts.ServiceType.IDENTITY: {},
                              consts.ServiceType.COMPUTE: {},
                              "some_service": {}}
        mock_keystone_create_client.return_value = mock.Mock(
            service_catalog=mock.Mock(
                get_endpoints=lambda: available_services))
        clients = osclients.Clients(self.credential)

        self.assertEqual(
            {consts.ServiceType.IDENTITY: consts.Service.KEYSTONE,
             consts.ServiceType.COMPUTE: consts.Service.NOVA,
             "some_service": "__unknown__"},
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
                service_type="application-catalog",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name
            )
            kw = {"endpoint": self.service_catalog.url_for.return_value,
                  "token": self.fake_keystone.auth_token}
            mock_murano.client.Client.assert_called_once_with("1", **kw)
            self.assertEqual(fake_murano, self.clients.cache["murano"])

    @mock.patch("rally.osclients.Designate._get_session")
    @ddt.data(
        {},
        {"version": "2"},
        {"version": "1"},
        {"version": None}
    )
    @ddt.unpack
    def test_designate(self, mock_designate__get_session, version=None):
        fake_designate = fakes.FakeDesignateClient()
        mock_designate = mock.Mock()
        mock_designate.client.Client.return_value = fake_designate

        mock_designate__get_session.return_value = self.fake_keystone.session

        self.assertNotIn("designate", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"designateclient": mock_designate}):
            if version is not None:
                client = self.clients.designate(version=version)
            else:
                client = self.clients.designate()
            self.assertEqual(fake_designate, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="dns",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name
            )

            default = version or "1"

            # Check that we append /v<version>
            url = self.service_catalog.url_for.return_value
            url.__iadd__.assert_called_once_with("/v%s" % default)

            mock_designate__get_session.assert_called_once_with(
                endpoint=url.__iadd__.return_value)

            mock_designate.client.Client.assert_called_once_with(
                default, session=self.fake_keystone.session)

            key = "designate"
            if version is not None:
                key += "%s" % {"version": version}
            self.assertEqual(fake_designate, self.clients.cache[key])

    @mock.patch("rally.osclients.Cue._get_session")
    def test_cue(self, mock_cue__get_session):
        fake_cue = fakes.FakeCueClient()
        mock_cue = mock.MagicMock()
        mock_cue.client.Client = mock.MagicMock(return_value=fake_cue)

        mock_cue__get_session.return_value = self.fake_keystone.session

        self.assertNotIn("cue", self.clients.cache)
        with mock.patch.dict("sys.modules", {"cueclient": mock_cue,
                                             "cueclient.v1": mock_cue}):
            client = self.clients.cue()
            self.assertEqual(fake_cue, client)
            mock_cue.client.Client.assert_called_once_with(
                interface=consts.EndpointType.PUBLIC,
                session=self.fake_keystone.session)
            self.assertEqual(fake_cue, self.clients.cache["cue"])

    def test_senlin(self):
        mock_senlin = mock.MagicMock()
        self.assertNotIn("senlin", self.clients.cache)
        with mock.patch.dict("sys.modules", {"senlinclient": mock_senlin}):
            client = self.clients.senlin()
            self.assertEqual(mock_senlin.client.Client.return_value, client)
            mock_senlin.client.Client.assert_called_once_with(
                "1",
                username=self.credential.username,
                password=self.credential.password,
                project_name=self.credential.tenant_name,
                cert=self.credential.cacert,
                auth_url=self.credential.auth_url)
            self.assertEqual(
                mock_senlin.client.Client.return_value,
                self.clients.cache["senlin"])

    @mock.patch("rally.osclients.Magnum._get_session")
    def test_magnum(self, mock_magnum__get_session):
        fake_magnum = fakes.FakeMagnumClient()
        mock_magnum = mock.MagicMock()
        mock_magnum.client.Client.return_value = fake_magnum

        mock_magnum__get_session.return_value = self.fake_keystone.session

        self.assertNotIn("magnum", self.clients.cache)
        with mock.patch.dict("sys.modules", {"magnumclient": mock_magnum}):
            client = self.clients.magnum()

            self.assertEqual(fake_magnum, client)

            self.service_catalog.url_for.assert_called_once_with(
                service_type="container-infra",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name)

            mock_magnum.client.Client.assert_called_once_with(
                interface=consts.EndpointType.PUBLIC,
                session=self.fake_keystone.session)

            self.assertEqual(fake_magnum, self.clients.cache["magnum"])

    def test_watcher(self):
        fake_watcher = fakes.FakeWatcherClient()
        mock_watcher = mock.MagicMock()
        mock_watcher.client.Client.return_value = fake_watcher
        self.assertNotIn("watcher", self.clients.cache)
        with mock.patch.dict("sys.modules", {"watcherclient": mock_watcher}):
            client = self.clients.watcher()

            self.assertEqual(fake_watcher, client)

            self.service_catalog.url_for.assert_called_once_with(
                service_type="infra-optim",
                endpoint_type=consts.EndpointType.PUBLIC,
                region_name=self.credential.region_name)

            mock_watcher.client.Client.assert_called_once_with(
                "1",
                self.service_catalog.url_for.return_value,
                token=self.fake_keystone.auth_token,
                ca_file=None,
                insecure=False,
                timeout=180.0)

            self.assertEqual(fake_watcher, self.clients.cache["watcher"])
