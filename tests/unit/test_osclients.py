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
from keystoneclient import exceptions as keystone_exceptions
import mock
from oslo_config import cfg

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


class OSClientTestCaseUtils(object):

    def set_up_keystone_mocks(self):
        self.ksc_module = mock.MagicMock(__version__="2.0.0")
        self.ksc_client = mock.MagicMock()
        self.ksa_identity_plugin = mock.MagicMock()
        self.ksa_password = mock.MagicMock(
            return_value=self.ksa_identity_plugin)
        self.ksa_identity = mock.MagicMock(Password=self.ksa_password)

        self.ksa_auth = mock.MagicMock()
        self.ksa_session = mock.MagicMock()
        self.patcher = mock.patch.dict("sys.modules",
                                       {"keystoneclient": self.ksc_module,
                                        "keystoneauth1": self.ksa_auth})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.ksc_module.client = self.ksc_client
        self.ksa_auth.identity = self.ksa_identity
        self.ksa_auth.session = self.ksa_session

    def make_auth_args(self):
        auth_kwargs = {
            "auth_url": "http://auth_url/", "username": "user",
            "password": "password", "tenant_name": "tenant",
            "domain_name": "domain", "project_name": "project_name",
            "project_domain_name": "project_domain_name",
            "user_domain_name": "user_domain_name",
        }
        kwargs = {"https_insecure": False, "https_cacert": None}
        kwargs.update(auth_kwargs)
        return auth_kwargs, kwargs


@ddt.ddt
class OSClientTestCase(test.TestCase, OSClientTestCaseUtils):

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

    @mock.patch("rally.osclients.Keystone.service_catalog")
    @ddt.data(
        {"endpoint_type": None, "service_type": None, "region_name": None},
        {"endpoint_type": "et", "service_type": "st", "region_name": "rn"}
    )
    @ddt.unpack
    def test__get_endpoint(self, mock_keystone_service_catalog, endpoint_type,
                           service_type, region_name):
        credential = objects.Credential("http://auth_url/v2.0", "user", "pass",
                                        endpoint_type=endpoint_type,
                                        region_name=region_name)
        mock_choose_service_type = mock.MagicMock()
        osclient = osclients.OSClient(credential, {}, mock.MagicMock())
        osclient.choose_service_type = mock_choose_service_type
        mock_url_for = mock_keystone_service_catalog.url_for
        self.assertEqual(mock_url_for.return_value,
                         osclient._get_endpoint(service_type))
        call_args = {
            "service_type": mock_choose_service_type.return_value,
            "region_name": region_name}
        if endpoint_type:
            call_args["interface"] = endpoint_type
        mock_url_for.assert_called_once_with(**call_args)
        mock_choose_service_type.assert_called_once_with(service_type)

    @mock.patch("rally.osclients.Keystone.get_session")
    def test__get_session(self, mock_keystone_get_session):
        osclient = osclients.OSClient(None, None, None)
        auth_url = "auth_url"
        version = "version"
        import warnings
        with mock.patch.object(warnings, "warn") as mock_warn:
            self.assertEqual(mock_keystone_get_session.return_value,
                             osclient._get_session(auth_url, version))
            self.assertFalse(mock_warn.called)
        mock_keystone_get_session.assert_called_once_with(version)


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


@ddt.ddt
class TestCreateKeystoneClient(test.TestCase, OSClientTestCaseUtils):

    def setUp(self):
        super(TestCreateKeystoneClient, self).setUp()
        self.credential = objects.Credential("http://auth_url/v2.0", "user",
                                             "pass", "tenant")

    def test_create_client(self):
        # NOTE(bigjools): This is a very poor testing strategy as it
        # tightly couples the test implementation to the tested
        # function's implementation. Ideally, we'd use a fake keystone
        # but all that's happening here is that it's checking the right
        # parameters were passed to the various parts that create a
        # client. Hopefully one day we'll get a real fake from the
        # keystone guys.
        self.set_up_keystone_mocks()
        keystone = osclients.Keystone(self.credential, {}, mock.MagicMock())
        keystone.get_session = mock.Mock(
            return_value=(self.ksa_session, self.ksa_identity_plugin,))
        client = keystone.create_client(version=3)

        kwargs_session = self.credential.to_dict()
        kwargs_session.update({
            "auth_url": "http://auth_url/",
            "session": self.ksa_session,
            "timeout": 180.0})
        keystone.get_session.assert_called_once_with(version="3")
        self.ksc_client.Client.assert_called_once_with(
            session=self.ksa_session, timeout=180.0, version="3")
        self.assertIs(client, self.ksc_client.Client())

    def test_create_client_removes_url_path_if_version_specified(self):
        # If specifying a version on the client creation call, ensure
        # the auth_url is versionless and the version required is passed
        # into the Client() call.
        self.set_up_keystone_mocks()
        auth_kwargs, all_kwargs = self.make_auth_args()
        keystone = osclients.Keystone(
            self.credential, {}, mock.MagicMock())
        keystone.get_session = mock.Mock(
            return_value=(self.ksa_session, self.ksa_identity_plugin,))
        client = keystone.create_client(version="3")

        self.assertIs(client, self.ksc_client.Client())
        called_with = self.ksc_client.Client.call_args_list[0][1]
        self.assertEqual(
            {"session": self.ksa_session, "timeout": 180.0, "version": "3"},
            called_with)

    @ddt.data("http://auth_url/v2.0", "http://auth_url/v3",
              "http://auth_url/", "auth_url")
    def test_keystone_get_session(self, auth_url):
        credential = objects.Credential(auth_url, "user",
                                        "pass", "tenant")
        self.set_up_keystone_mocks()
        keystone = osclients.Keystone(credential, {}, {})

        version_data = mock.Mock(return_value=[{"version": (1, 0)}])
        self.ksa_auth.discover.Discover.return_value = (
            mock.Mock(version_data=version_data))

        self.assertEqual((self.ksa_session.Session.return_value,
                          self.ksa_identity_plugin),
                         keystone.get_session())
        if auth_url.endswith("v2.0"):
            self.ksa_password.assert_called_once_with(
                auth_url=auth_url, password="pass",
                tenant_name="tenant", username="user")
        else:
            self.ksa_password.assert_called_once_with(
                auth_url=auth_url, password="pass",
                tenant_name="tenant", username="user",
                domain_name=None, project_domain_name=None,
                user_domain_name=None)
        self.ksa_session.Session.assert_has_calls(
            [mock.call(timeout=180.0, verify=True),
             mock.call(auth=self.ksa_identity_plugin, timeout=180.0,
                       verify=True)])

    def test_keystone_property(self):
        keystone = osclients.Keystone(None, None, None)
        self.assertRaises(exceptions.RallyException, lambda: keystone.keystone)

    @mock.patch("rally.osclients.Keystone.get_session")
    def test_auth_ref(self, mock_keystone_get_session):
        session = mock.MagicMock()
        auth_plugin = mock.MagicMock()
        mock_keystone_get_session.return_value = (session, auth_plugin)
        cache = {}
        keystone = osclients.Keystone(None, None, cache)

        self.assertEqual(auth_plugin.get_access.return_value,
                         keystone.auth_ref)
        self.assertEqual(auth_plugin.get_access.return_value,
                         cache["keystone_auth_ref"])

        # check that auth_ref was cached.
        keystone.auth_ref
        mock_keystone_get_session.assert_called_once_with()


@ddt.ddt
class OSClientsTestCase(test.TestCase):

    def setUp(self):
        super(OSClientsTestCase, self).setUp()
        self.credential = objects.Credential("http://auth_url/v2.0", "user",
                                             "pass", "tenant")
        self.clients = osclients.Clients(self.credential, {})

        self.fake_keystone = fakes.FakeKeystoneClient()

        keystone_patcher = mock.patch(
            "rally.osclients.Keystone.create_client",
            return_value=self.fake_keystone)
        self.mock_create_keystone_client = keystone_patcher.start()

        self.auth_ref_patcher = mock.patch("rally.osclients.Keystone.auth_ref")
        self.auth_ref = self.auth_ref_patcher.start()

        self.service_catalog = self.auth_ref.service_catalog
        self.service_catalog.url_for = mock.MagicMock()

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

    def test_keystone(self):
        self.assertNotIn("keystone", self.clients.cache)
        client = self.clients.keystone()
        self.assertEqual(client, self.fake_keystone)
        credential = {"timeout": cfg.CONF.openstack_client_http_timeout,
                      "insecure": False, "cacert": None}
        kwargs = self.credential.to_dict()
        kwargs.update(credential)
        self.mock_create_keystone_client.assert_called_once_with()
        self.assertEqual(self.fake_keystone, self.clients.cache["keystone"])

    def test_verified_keystone(self):
        self.auth_ref.role_names = ["admin"]
        self.assertEqual(self.mock_create_keystone_client.return_value,
                         self.clients.verified_keystone())

    def test_verified_keystone_user_not_admin(self):
        self.auth_ref.role_names = ["notadmin"]
        self.assertRaises(exceptions.InvalidAdminException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Keystone.get_session")
    def test_verified_keystone_unauthorized(self, mock_keystone_get_session):
        self.auth_ref_patcher.stop()
        mock_keystone_get_session.side_effect = (
            keystone_exceptions.Unauthorized
        )
        self.assertRaises(exceptions.InvalidEndpointsException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Keystone.get_session")
    def test_verified_keystone_unreachable(self, mock_keystone_get_session):
        self.auth_ref_patcher.stop()
        mock_keystone_get_session.side_effect = (
            keystone_exceptions.AuthorizationFailure
        )
        self.assertRaises(exceptions.HostUnreachableException,
                          self.clients.verified_keystone)

    @mock.patch("rally.osclients.Nova._get_endpoint")
    def test_nova(self, mock_nova__get_endpoint):
        fake_nova = fakes.FakeNovaClient()
        mock_nova__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = fake_nova
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("nova", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"novaclient": mock_nova,
                              "keystoneauth1": mock_keystoneauth1}):
            mock_keystoneauth1.discover.Discover.return_value = (
                mock.Mock(version_data=mock.Mock(return_value=[
                    {"version": (2, 0)}]))
            )
            client = self.clients.nova()
            self.assertEqual(fake_nova, client)
            kw = {
                "version": "2",
                "session": mock_keystoneauth1.session.Session(),
                "endpoint_override": mock_nova__get_endpoint.return_value}
            mock_nova.client.Client.assert_called_once_with(**kw)
            self.assertEqual(fake_nova, self.clients.cache["nova"])

    @mock.patch("rally.osclients.Neutron._get_endpoint")
    def test_neutron(self, mock_neutron__get_endpoint):
        fake_neutron = fakes.FakeNeutronClient()
        mock_neutron__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_neutron = mock.MagicMock()
        mock_keystoneauth1 = mock.MagicMock()
        mock_neutron.client.Client.return_value = fake_neutron
        self.assertNotIn("neutron", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"neutronclient.neutron": mock_neutron,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.neutron()
            self.assertEqual(fake_neutron, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "endpoint_url": mock_neutron__get_endpoint.return_value}
            mock_neutron.client.Client.assert_called_once_with("2.0", **kw)
            self.assertEqual(fake_neutron, self.clients.cache["neutron"])

    @mock.patch("rally.osclients.Glance._get_endpoint")
    def test_glance(self, mock_glance__get_endpoint):
        fake_glance = fakes.FakeGlanceClient()
        mock_glance = mock.MagicMock()
        mock_glance__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        mock_glance.Client = mock.MagicMock(return_value=fake_glance)
        with mock.patch.dict("sys.modules",
                             {"glanceclient": mock_glance,
                              "keystoneauth1": mock_keystoneauth1}):
            self.assertNotIn("glance", self.clients.cache)
            client = self.clients.glance()
            self.assertEqual(fake_glance, client)
            kw = {
                "version": "1",
                "session": mock_keystoneauth1.session.Session(),
                "endpoint_override": mock_glance__get_endpoint.return_value}
            mock_glance.Client.assert_called_once_with(**kw)
            self.assertEqual(fake_glance, self.clients.cache["glance"])

    @mock.patch("rally.osclients.Cinder._get_endpoint")
    def test_cinder(self, mock_cinder__get_endpoint):
        fake_cinder = mock.MagicMock(client=fakes.FakeCinderClient())
        mock_cinder = mock.MagicMock()
        mock_cinder.client.Client.return_value = fake_cinder
        mock_cinder__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("cinder", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"cinderclient": mock_cinder,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.cinder()
            self.assertEqual(fake_cinder, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "endpoint_override": mock_cinder__get_endpoint.return_value}
            mock_cinder.client.Client.assert_called_once_with(
                "2", **kw)
            self.assertEqual(fake_cinder, self.clients.cache["cinder"])

    @mock.patch("rally.osclients.Manila._get_endpoint")
    def test_manila(self, mock_manila__get_endpoint):
        mock_manila = mock.MagicMock()
        mock_manila__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("manila", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"manilaclient": mock_manila,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.manila()
            self.assertEqual(mock_manila.client.Client.return_value, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "service_catalog_url": mock_manila__get_endpoint.return_value
            }
            mock_manila.client.Client.assert_called_once_with("1", **kw)
            self.assertEqual(
                mock_manila.client.Client.return_value,
                self.clients.cache["manila"])

    @mock.patch("rally.osclients.Ceilometer._get_endpoint")
    def test_ceilometer(self, mock_ceilometer__get_endpoint):
        fake_ceilometer = fakes.FakeCeilometerClient()
        mock_ceilometer = mock.MagicMock()
        mock_ceilometer__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        mock_ceilometer.client.get_client = mock.MagicMock(
            return_value=fake_ceilometer)
        self.assertNotIn("ceilometer", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"ceilometerclient": mock_ceilometer,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.ceilometer()
            self.assertEqual(fake_ceilometer, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "endpoint_override": mock_ceilometer__get_endpoint.return_value
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
            mock_keystoneauth1.discover.Discover.return_value = (
                mock.Mock(version_data=mock.Mock(return_value=[
                    {"version": (1, 0)}]))
            )
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
                region_name=self.credential.region_name)
            os_endpoint = self.service_catalog.url_for.return_value
            kw = {"token": self.auth_ref.auth_token,
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

    @mock.patch("rally.osclients.Ironic._get_endpoint")
    def test_ironic(self, mock_ironic__get_endpoint):
        fake_ironic = fakes.FakeIronicClient()
        mock_ironic = mock.MagicMock()
        mock_ironic.client.get_client = mock.MagicMock(
            return_value=fake_ironic)
        mock_ironic__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("ironic", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"ironicclient": mock_ironic,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.ironic()
            self.assertEqual(fake_ironic, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "endpoint": mock_ironic__get_endpoint.return_value}
            mock_ironic.client.get_client.assert_called_once_with("1", **kw)
            self.assertEqual(fake_ironic, self.clients.cache["ironic"])

    @mock.patch("rally.osclients.Sahara._get_endpoint")
    def test_sahara(self, mock_sahara__get_endpoint):
        fake_sahara = fakes.FakeSaharaClient()
        mock_sahara = mock.MagicMock()
        mock_sahara.client.Client = mock.MagicMock(return_value=fake_sahara)
        mock_sahara__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("sahara", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"saharaclient": mock_sahara,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.sahara()
            self.assertEqual(fake_sahara, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "sahara_url": mock_sahara__get_endpoint.return_value}
            mock_sahara.client.Client.assert_called_once_with(1.1, **kw)
            self.assertEqual(fake_sahara, self.clients.cache["sahara"])

    def test_zaqar(self):
        fake_zaqar = fakes.FakeZaqarClient()
        mock_zaqar = mock.MagicMock()
        mock_zaqar.client.Client = mock.MagicMock(return_value=fake_zaqar)
        self.assertNotIn("zaqar", self.clients.cache)
        p_id = self.auth_ref.project_id
        with mock.patch.dict("sys.modules", {"zaqarclient.queues":
                                             mock_zaqar}):
            client = self.clients.zaqar()
            self.assertEqual(fake_zaqar, client)
            self.service_catalog.url_for.assert_called_once_with(
                service_type="messaging",
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

    @mock.patch("rally.osclients.Trove._get_endpoint")
    def test_trove(self, mock_trove__get_endpoint):
        fake_trove = fakes.FakeTroveClient()
        mock_trove = mock.MagicMock()
        mock_trove.client.Client = mock.MagicMock(return_value=fake_trove)
        mock_trove__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        self.assertNotIn("trove", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"troveclient": mock_trove,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.trove()
            self.assertEqual(fake_trove, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "endpoint": mock_trove__get_endpoint.return_value}
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
                region_name=self.credential.region_name
            )
            fake_mistral_url = self.service_catalog.url_for.return_value
            mock_mistral.client.client.assert_called_once_with(
                mistral_url=fake_mistral_url,
                service_type="workflowv2",
                auth_token=self.auth_ref.auth_token
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
                region_name=self.credential.region_name)
            kw = {"retries": 1,
                  "preauthurl": self.service_catalog.url_for.return_value,
                  "preauthtoken": self.auth_ref.auth_token,
                  "insecure": False,
                  "cacert": None,
                  "user": self.credential.username,
                  "tenant_name": self.credential.tenant_name,
                  }
            mock_swift.client.Connection.assert_called_once_with(**kw)
            self.assertEqual(self.clients.cache["swift"], fake_swift)

    @mock.patch("rally.osclients.EC2._get_endpoint")
    def test_ec2(self, mock_ec2__get_endpoint):
        mock_boto = mock.Mock()
        self.fake_keystone.ec2 = mock.Mock()
        self.fake_keystone.ec2.create.return_value = mock.Mock(
            access="fake_access", secret="fake_secret")
        mock_ec2__get_endpoint.return_value = "http://fake.to:1/fake"
        fake_ec2 = fakes.FakeEC2Client()
        mock_boto.connect_ec2_endpoint.return_value = fake_ec2

        self.assertNotIn("ec2", self.clients.cache)
        with mock.patch.dict("sys.modules", {"boto": mock_boto}):
            client = self.clients.ec2()

            self.assertEqual(fake_ec2, client)
            kw = {
                "url": "http://fake.to:1/fake",
                "aws_access_key_id": "fake_access",
                "aws_secret_access_key": "fake_secret",
                "is_secure": self.credential.insecure,
            }
            mock_boto.connect_ec2_endpoint.assert_called_once_with(**kw)
            self.assertEqual(fake_ec2, self.clients.cache["ec2"])

    @mock.patch("rally.osclients.Keystone.service_catalog")
    def test_services(self, mock_keystone_service_catalog):
        available_services = {consts.ServiceType.IDENTITY: {},
                              consts.ServiceType.COMPUTE: {},
                              "some_service": {}}
        mock_get_endpoints = mock_keystone_service_catalog.get_endpoints
        mock_get_endpoints.return_value = available_services
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
                region_name=self.credential.region_name
            )
            kw = {"endpoint": self.service_catalog.url_for.return_value,
                  "token": self.auth_ref.auth_token}
            mock_murano.client.Client.assert_called_once_with("1", **kw)
            self.assertEqual(fake_murano, self.clients.cache["murano"])

    @mock.patch("rally.osclients.Keystone.get_session")
    @ddt.data(
        {},
        {"version": "2"},
        {"version": "1"},
        {"version": None}
    )
    @ddt.unpack
    def test_designate(self, mock_keystone_get_session, version=None):
        fake_designate = fakes.FakeDesignateClient()
        mock_designate = mock.Mock()
        mock_designate.client.Client.return_value = fake_designate

        mock_keystone_get_session.return_value = ("fake_session",
                                                  "fake_auth_plugin")

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
                region_name=self.credential.region_name
            )

            default = version or "1"

            # Check that we append /v<version>
            url = self.service_catalog.url_for.return_value
            url.__iadd__.assert_called_once_with("/v%s" % default)

            mock_keystone_get_session.assert_called_once_with()

            if version == "2":
                mock_designate.client.Client.assert_called_once_with(
                    version,
                    endpoint_override=url.__iadd__.return_value,
                    session="fake_session")
            elif version == "1":
                mock_designate.client.Client.assert_called_once_with(
                    version,
                    endpoint=url.__iadd__.return_value,
                    session="fake_session")

            key = "designate"
            if version is not None:
                key += "%s" % {"version": version}
            self.assertEqual(fake_designate, self.clients.cache[key])

    @mock.patch("rally.osclients.Keystone.get_session")
    def test_cue(self, mock_keystone_get_session):
        fake_cue = fakes.FakeCueClient()
        mock_cue = mock.MagicMock()
        mock_cue.client.Client = mock.MagicMock(return_value=fake_cue)
        mock_keystone_get_session.return_value = ("fake_session",
                                                  "fake_auth_plugin")
        self.assertNotIn("cue", self.clients.cache)
        with mock.patch.dict("sys.modules", {"cueclient": mock_cue,
                                             "cueclient.v1": mock_cue}):
            client = self.clients.cue()
            self.assertEqual(fake_cue, client)
            mock_cue.client.Client.assert_called_once_with(
                interface=self.credential.endpoint_type,
                session="fake_session")
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

    @mock.patch("rally.osclients.Magnum._get_endpoint")
    def test_magnum(self, mock_magnum__get_endpoint):
        fake_magnum = fakes.FakeMagnumClient()
        mock_magnum = mock.MagicMock()
        mock_magnum.client.Client.return_value = fake_magnum

        mock_magnum__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()

        self.assertNotIn("magnum", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"magnumclient": mock_magnum,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.magnum()

            self.assertEqual(fake_magnum, client)
            kw = {
                "interface": self.credential.endpoint_type,
                "session": mock_keystoneauth1.session.Session(),
                "magnum_url": mock_magnum__get_endpoint.return_value}

            mock_magnum.client.Client.assert_called_once_with(**kw)
            self.assertEqual(fake_magnum, self.clients.cache["magnum"])

    @mock.patch("rally.osclients.Watcher._get_endpoint")
    def test_watcher(self, mock_watcher__get_endpoint):
        fake_watcher = fakes.FakeWatcherClient()
        mock_watcher = mock.MagicMock()
        mock_watcher__get_endpoint.return_value = "http://fake.to:2/fake"
        mock_keystoneauth1 = mock.MagicMock()
        mock_watcher.client.Client.return_value = fake_watcher
        self.assertNotIn("watcher", self.clients.cache)
        with mock.patch.dict("sys.modules",
                             {"watcherclient": mock_watcher,
                              "keystoneauth1": mock_keystoneauth1}):
            client = self.clients.watcher()

            self.assertEqual(fake_watcher, client)
            kw = {
                "session": mock_keystoneauth1.session.Session(),
                "endpoint": mock_watcher__get_endpoint.return_value}

            mock_watcher.client.Client.assert_called_once_with("1", **kw)
            self.assertEqual(fake_watcher, self.clients.cache["watcher"])
