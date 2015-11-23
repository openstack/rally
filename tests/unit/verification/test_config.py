# Copyright 2014: Mirantis Inc.
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

import os

import mock
from oslo_config import cfg
import requests
from six.moves.urllib import parse

from rally import exceptions
from rally.verification.tempest import config
from tests.unit import fakes
from tests.unit import test

CONF = cfg.CONF


class TempestConfigTestCase(test.TestCase):

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    @mock.patch("rally.osclients.Clients.services",
                return_value={"test_service_type": "test_service"})
    @mock.patch("rally.osclients.Clients.verified_keystone")
    @mock.patch("rally.verification.tempest.config.os.path.isfile",
                return_value=True)
    def setUp(self, mock_isfile, mock_clients_verified_keystone,
              mock_clients_services, mock_deployment_get):
        super(TempestConfigTestCase, self).setUp()

        self.endpoint = {
            "username": "test",
            "tenant_name": "test",
            "password": "test",
            "auth_url": "http://test/v2.0/",
            "permission": "admin",
            "admin_domain_name": "Default",
            "https_insecure": False,
            "https_cacert": "/path/to/cacert/file"
        }
        mock_deployment_get.return_value = {"admin": self.endpoint}

        self.deployment = "fake_deployment"
        self.conf_generator = config.TempestConfig(self.deployment)
        self.conf_generator.clients.services = mock_clients_services

        keystone_patcher = mock.patch(
            "rally.osclients.Keystone._create_keystone_client")
        keystone_patcher.start()
        self.addCleanup(keystone_patcher.stop)

    @mock.patch("rally.verification.tempest.config.requests")
    @mock.patch("rally.verification.tempest.config.os.rename")
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open(),
                create=True)
    def test__download_cirros_image_success(self, mock_open, mock_rename,
                                            mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 200
        mock_requests.get.return_value = mock_result
        self.conf_generator._download_cirros_image()
        mock_requests.get.assert_called_once_with(CONF.image.cirros_img_url,
                                                  stream=True)

    @mock.patch("rally.verification.tempest.config.requests.get")
    def test__download_cirros_image_connection_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.ConnectionError()
        self.assertRaises(exceptions.TempestConfigCreationFailure,
                          self.conf_generator._download_cirros_image)

    @mock.patch("rally.verification.tempest.config.requests")
    def test__download_cirros_image_notfound(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 404
        mock_requests.get.return_value = mock_result
        self.assertRaises(exceptions.TempestConfigCreationFailure,
                          self.conf_generator._download_cirros_image)

    @mock.patch("rally.verification.tempest.config.requests")
    def test__download_cirros_image_code_not_200_and_404(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 500
        mock_requests.get.return_value = mock_result
        self.assertRaises(exceptions.TempestConfigCreationFailure,
                          self.conf_generator._download_cirros_image)

    def test__get_service_url(self):
        service = "test_service"
        service_type = "test_service_type"
        url = "test_url"
        # Mocked at setUp
        self.conf_generator.keystone.auth_ref = {
            "serviceCatalog": [
                {
                    "name": service,
                    "type": service_type,
                    "endpoints": [{"publicURL": url}]
                }
            ]
        }
        self.assertEqual(self.conf_generator._get_service_url(service), url)

    @mock.patch("rally.verification.tempest."
                "config.TempestConfig._get_service_url")
    def test__configure_boto(self, mock_tempest_config__get_service_url):
        url = "test_url"
        mock_tempest_config__get_service_url.return_value = url
        s3_materials_path = os.path.join(
            self.conf_generator.data_dir, "s3materials")
        self.conf_generator._configure_boto()
        expected = (("ec2_url", url),
                    ("s3_url", url),
                    ("http_socket_timeout", "30"),
                    ("s3_materials_path", s3_materials_path))
        result = self.conf_generator.conf.items("boto")
        self.assertIn(sorted(expected)[0], sorted(result))

    def test__configure_default(self):
        self.conf_generator._configure_default()
        expected = (("debug", "True"), ("log_file", "tempest.log"),
                    ("use_stderr", "False"))
        results = self.conf_generator.conf.items("DEFAULT")
        self.assertEqual(sorted(expected), sorted(results))

    def test__configure_dashboard(self):
        self.conf_generator._configure_dashboard()
        url = "http://%s/" % parse.urlparse(self.endpoint["auth_url"]).hostname
        expected = (("dashboard_url", url),)
        result = self.conf_generator.conf.items("dashboard")
        self.assertIn(sorted(expected)[0], sorted(result))

    def test__configure_identity(self):
        self.conf_generator._configure_identity()
        expected = (
            ("username", self.endpoint["username"]),
            ("password", self.endpoint["password"]),
            ("tenant_name", self.endpoint["tenant_name"]),
            ("admin_username", self.endpoint["username"]),
            ("admin_password", self.endpoint["password"]),
            ("admin_tenant_name", self.endpoint["username"]),
            ("admin_domain_name", self.endpoint["admin_domain_name"]),
            ("uri", self.endpoint["auth_url"]),
            ("uri_v3", self.endpoint["auth_url"].replace("/v2.0/", "/v3")),
            ("disable_ssl_certificate_validation",
             self.endpoint["https_insecure"]),
            ("ca_certificates_file", self.endpoint["https_cacert"]))
        result = self.conf_generator.conf.items("identity")
        self.assertIn(sorted(expected)[0], sorted(result))

    def test__configure_network_if_neutron(self):
        mock_neutronclient = mock.MagicMock()
        mock_neutronclient.list_networks.return_value = {
            "networks": [
                {
                    "status": "ACTIVE",
                    "id": "test_id",
                    "router:external": True
                }
            ]
        }
        mock_neutron = mock.MagicMock()
        mock_neutron.client.Client.return_value = mock_neutronclient
        with mock.patch.dict("sys.modules", {"neutronclient.neutron":
                                             mock_neutron}):
            self.conf_generator.available_services = ["neutron"]
            self.conf_generator._configure_network()
            expected = (("public_network_id", "test_id"),)
            result = self.conf_generator.conf.items("network")
            self.assertIn(sorted(expected)[0], sorted(result))

    def test__configure_network_if_nova(self):
        self.conf_generator.available_services = ["nova"]
        mock_novaclient = mock.MagicMock()
        mock_network = mock.MagicMock()
        mock_network.human_id = "fake-network"
        mock_novaclient.networks.list.return_value = [mock_network]
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = mock_novaclient
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            self.conf_generator._configure_network()
            self.assertEqual("fake-network",
                             self.conf_generator.conf.get(
                                 "compute", "fixed_network_name"))
            self.assertEqual("fake-network",
                             self.conf_generator.conf.get(
                                 "compute", "network_for_ssh"))

    def test__configure_network_feature_enabled(self):
        mock_neutronclient = mock.MagicMock()
        mock_neutronclient.list_ext.return_value = {
            "extensions": [
                {"alias": "dvr"},
                {"alias": "extra_dhcp_opt"},
                {"alias": "extraroute"}
            ]
        }
        mock_neutron = mock.MagicMock()
        mock_neutron.client.Client.return_value = mock_neutronclient
        with mock.patch.dict("sys.modules",
                             {"neutronclient.neutron": mock_neutron}):
            self.conf_generator.available_services = ["neutron"]
            self.conf_generator._configure_network_feature_enabled()
            expected = (("api_extensions", "dvr,extra_dhcp_opt,extraroute"),)
            result = self.conf_generator.conf.items("network-feature-enabled")
            self.assertIn(sorted(expected)[0], sorted(result))

    @mock.patch("rally.verification.tempest.config.os.path.exists",
                return_value=False)
    @mock.patch("rally.verification.tempest.config.os.makedirs")
    def test__configure_oslo_concurrency(self, mock_makedirs, mock_exists):
        self.conf_generator._configure_oslo_concurrency()
        lock_path = os.path.join(
            self.conf_generator.data_dir, "lock_files_%s" % self.deployment)
        mock_makedirs.assert_called_once_with(lock_path)
        expected = (("lock_path", lock_path),)
        result = self.conf_generator.conf.items("oslo_concurrency")
        self.assertIn(sorted(expected)[0], sorted(result))

    def test__configure_object_storage(self):
        self.conf_generator._configure_object_storage()
        expected = (
            ("operator_role", CONF.role.swift_operator_role),
            ("reseller_admin_role", CONF.role.swift_reseller_admin_role))
        result = self.conf_generator.conf.items("object-storage")
        self.assertIn(sorted(expected)[0], sorted(result))

    def test__configure_scenario(self):
        self.conf_generator._configure_scenario()
        expected = (
            ("img_dir", self.conf_generator.data_dir),
            ("img_file", config.IMAGE_NAME))
        result = self.conf_generator.conf.items("scenario")
        self.assertIn(sorted(expected)[0], sorted(result))

    @mock.patch("rally.verification.tempest.config.requests")
    def test__configure_service_available(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 404
        mock_requests.get.return_value = mock_result
        available_services = ("nova", "cinder", "glance", "sahara")
        self.conf_generator.available_services = available_services
        self.conf_generator._configure_service_available()
        expected_horizon_url = "http://test"
        expected_timeout = CONF.openstack_client_http_timeout
        mock_requests.get.assert_called_once_with(
            expected_horizon_url,
            timeout=expected_timeout)
        expected = (("neutron", "False"), ("heat", "False"),
                    ("ceilometer", "False"), ("swift", "False"),
                    ("cinder", "True"), ("nova", "True"),
                    ("glance", "True"), ("horizon", "False"),
                    ("sahara", "True"))
        result = self.conf_generator.conf.items("service_available")
        self.assertIn(sorted(expected)[0], sorted(result))

    @mock.patch("rally.verification.tempest.config.requests")
    def test__configure_service_available_horizon(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 200
        mock_requests.get.return_value = mock_result
        self.conf_generator._configure_service_available()
        self.assertEqual(
            self.conf_generator.conf.get(
                "service_available", "horizon"), "True")

    @mock.patch("rally.verification.tempest.config.requests.get")
    def test__configure_service_not_available_horizon(self, mock_get):
        mock_get.side_effect = requests.Timeout()
        self.conf_generator._configure_service_available()
        self.assertEqual(
            self.conf_generator.conf.get(
                "service_available", "horizon"), "False")

    def test__configure_validation_if_neutron(self):
        # if neutron is available
        self.conf_generator.available_services = ["neutron"]
        self.conf_generator._configure_validation()
        self.assertEqual("floating",
                         self.conf_generator.conf.get("validation",
                                                      "connect_method"))

    def test__configure_validation_if_novanetwork(self):
        self.conf_generator._configure_validation()
        self.assertEqual("fixed",
                         self.conf_generator.conf.get("validation",
                                                      "connect_method"))

    @mock.patch("rally.verification.tempest.config._write_config")
    @mock.patch("inspect.getmembers")
    def test_generate(self, mock_inspect_getmembers, mock__write_config):
        configure_something_method = mock.MagicMock()
        mock_inspect_getmembers.return_value = [("_configure_something",
                                                 configure_something_method)]

        self.conf_generator.generate("/path/to/fake/conf")
        self.assertEqual(configure_something_method.call_count, 1)
        self.assertEqual(mock__write_config.call_count, 1)

    @mock.patch("six.moves.builtins.open",
                side_effect=mock.mock_open(), create=True)
    def test__write_config(self, mock_open):
        conf_path = "/path/to/fake/conf"
        conf_data = mock.Mock()
        config._write_config(conf_path, conf_data)
        mock_open.assert_called_once_with(conf_path, "w+")
        conf_data.write.assert_called_once_with(mock_open.side_effect())


class TempestResourcesContextTestCase(test.TestCase):

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    @mock.patch("rally.osclients.Clients.services",
                return_value={"test_service_type": "test_service"})
    @mock.patch("rally.osclients.Clients.verified_keystone")
    def setUp(self, mock_clients_verified_keystone,
              mock_clients_services, mock_deployment_get):
        super(TempestResourcesContextTestCase, self).setUp()

        endpoint = {
            "username": "test",
            "tenant_name": "test",
            "password": "test",
            "auth_url": "http://test/v2.0/",
            "permission": "admin",
            "admin_domain_name": "Default"
        }
        mock_deployment_get.return_value = {"admin": endpoint}

        self.context = config.TempestResourcesContext("fake_deployment",
                                                      "/fake/path/to/config")
        self.context.clients = mock.MagicMock()
        self.context.conf.add_section("compute")

        keystone_patcher = mock.patch(
            "rally.osclients.Keystone._create_keystone_client")
        keystone_patcher.start()
        self.addCleanup(keystone_patcher.stop)

    @mock.patch("rally.plugins.openstack.wrappers."
                "network.NeutronWrapper.create_network")
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    def test_options_configured_manually(
            self, mock_open, mock_neutron_wrapper_create_network):
        self.context.available_services = ["glance", "nova", "neutron"]

        self.context.conf.set("compute", "image_ref", "id1")
        self.context.conf.set("compute", "image_ref_alt", "id2")
        self.context.conf.set("compute", "flavor_ref", "id3")
        self.context.conf.set("compute", "flavor_ref_alt", "id4")
        self.context.conf.set("compute", "fixed_network_name", "name1")

        self.context.__enter__()

        glanceclient = self.context.clients.glance()
        novaclient = self.context.clients.nova()

        self.assertEqual(glanceclient.images.create.call_count, 0)
        self.assertEqual(novaclient.flavors.create.call_count, 0)
        self.assertEqual(mock_neutron_wrapper_create_network.call_count, 0)

    def test__create_tempest_roles(self):
        role1 = CONF.role.swift_operator_role
        role2 = CONF.role.swift_reseller_admin_role
        role3 = CONF.role.heat_stack_owner_role
        role4 = CONF.role.heat_stack_user_role

        client = self.context.clients.verified_keystone()
        client.roles.list.return_value = [fakes.FakeRole(name=role1),
                                          fakes.FakeRole(name=role2)]
        client.roles.create.side_effect = [fakes.FakeFlavor(name=role3),
                                           fakes.FakeFlavor(name=role4)]

        self.context._create_tempest_roles()
        self.assertEqual(client.roles.create.call_count, 2)

        created_roles = [role.name for role in self.context._created_roles]
        self.assertIn(role3, created_roles)
        self.assertIn(role4, created_roles)

    # We can choose any option to test the '_configure_option' method. So let's
    # configure the 'flavor_ref' option.
    def test__configure_option(self):
        create_method = mock.MagicMock()
        create_method.side_effect = [fakes.FakeFlavor(id="id1")]

        self.context.conf.set("compute", "flavor_ref", "")
        self.context._configure_option("flavor_ref", create_method, 64)
        self.assertEqual(create_method.call_count, 1)

        result = self.context.conf.get("compute", "flavor_ref")
        self.assertEqual("id1", result)

    @mock.patch("six.moves.builtins.open")
    def test__create_image(self, mock_open):
        client = self.context.clients.glance()
        client.images.create.side_effect = [fakes.FakeImage(id="id1")]

        image = self.context._create_image()
        self.assertEqual("id1", image.id)
        self.assertEqual("id1", self.context._created_images[0].id)

    def test__create_flavor(self):
        client = self.context.clients.nova()
        client.flavors.create.side_effect = [fakes.FakeFlavor(id="id1")]

        flavor = self.context._create_flavor(64)
        self.assertEqual("id1", flavor.id)
        self.assertEqual("id1", self.context._created_flavors[0].id)

    @mock.patch("rally.plugins.openstack.wrappers."
                "network.NeutronWrapper.create_network")
    def test__create_network_resources(
            self, mock_neutron_wrapper_create_network):
        mock_neutron_wrapper_create_network.side_effect = [
            fakes.FakeNetwork(id="id1")]

        network = self.context._create_network_resources()
        self.assertEqual("id1", network.id)
        self.assertEqual("id1", self.context._created_networks[0].id)

    def test__cleanup_tempest_roles(self):
        self.context._created_roles = [fakes.FakeRole(), fakes.FakeRole()]

        self.context._cleanup_tempest_roles()
        client = self.context.clients.keystone()
        self.assertEqual(client.roles.delete.call_count, 2)

    def test__cleanup_images(self):
        self.context._created_images = [fakes.FakeImage(id="id1"),
                                        fakes.FakeImage(id="id2")]

        self.context.conf.set("compute", "image_ref", "id1")
        self.context.conf.set("compute", "image_ref_alt", "id2")

        self.context._cleanup_images()
        client = self.context.clients.glance()
        self.assertEqual(client.images.delete.call_count, 2)

        self.assertEqual("", self.context.conf.get("compute", "image_ref"))
        self.assertEqual("", self.context.conf.get("compute", "image_ref_alt"))

    def test__cleanup_flavors(self):
        self.context._created_flavors = [fakes.FakeFlavor(id="id1"),
                                         fakes.FakeFlavor(id="id2")]

        self.context.conf.set("compute", "flavor_ref", "id1")
        self.context.conf.set("compute", "flavor_ref_alt", "id2")

        self.context._cleanup_flavors()
        client = self.context.clients.nova()
        self.assertEqual(client.flavors.delete.call_count, 2)

        self.assertEqual("", self.context.conf.get("compute", "flavor_ref"))
        self.assertEqual("", self.context.conf.get("compute",
                                                   "flavor_ref_alt"))

    @mock.patch("rally.plugins.openstack.wrappers."
                "network.NeutronWrapper.delete_network")
    def test__cleanup_network_resources(
            self, mock_neutron_wrapper_delete_network):
        self.context._created_networks = [{"name": "net-12345"}]
        self.context.conf.set("compute", "fixed_network_name", "net-12345")

        self.context._cleanup_network_resources()
        self.assertEqual(mock_neutron_wrapper_delete_network.call_count, 1)
        self.assertEqual("", self.context.conf.get("compute",
                                                   "fixed_network_name"))
