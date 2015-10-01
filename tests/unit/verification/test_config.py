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

from rally import exceptions
from rally.verification.tempest import config
from tests.unit import fakes
from tests.unit import test

CONF = cfg.CONF


class ConfigTestCase(test.TestCase):

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    @mock.patch("rally.osclients.Clients.services",
                return_value={"test_service_type": "test_service"})
    @mock.patch("rally.osclients.Clients.verified_keystone")
    @mock.patch("rally.verification.tempest.config.os.path.isfile",
                return_value=True)
    def setUp(self, mock_isfile, mock_clients_verified_keystone,
              mock_clients_services, mock_deployment_get):
        super(ConfigTestCase, self).setUp()

        self.endpoint = {
            "username": "test",
            "tenant_name": "test",
            "password": "test",
            "auth_url": "http://test/v2.0/",
            "permission": "admin",
            "admin_domain_name": "Default"
        }
        mock_deployment_get.return_value = {"admin": self.endpoint}

        self.deployment = "fake_deployment"
        self.conf_generator = config.TempestConfig(self.deployment)
        self.conf_generator.clients.services = mock_clients_services
        self.context = config.TempestResourcesContext(self.deployment,
                                                      "/path/to/fake/conf")
        self.context.conf.add_section("compute")

        keystone_patcher = mock.patch("rally.osclients.create_keystone_client")
        keystone_patcher.start()
        self.addCleanup(keystone_patcher.stop)

    @staticmethod
    def _remove_default_section(items):
        # Getting items from config parser by specified section name
        # returns also values from DEFAULT section
        defaults = (("log_file", "tempest.log"), ("debug", "True"),
                    ("use_stderr", "False"))
        return [item for item in items if item not in defaults]

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

    @mock.patch("rally.verification.tempest.config.requests")
    def test__download_cirros_image_notfound(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 404
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
        results = self._remove_default_section(
            self.conf_generator.conf.items("boto"))
        self.assertEqual(sorted(expected), sorted(results))

    def test__configure_default(self):
        self.conf_generator._configure_default()
        expected = (("debug", "True"), ("log_file", "tempest.log"),
                    ("use_stderr", "False"))
        results = self.conf_generator.conf.items("DEFAULT")
        self.assertEqual(sorted(expected), sorted(results))

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
            ("uri_v3", self.endpoint["auth_url"].replace("/v2.0/", "/v3")))
        results = self._remove_default_section(
            self.conf_generator.conf.items("identity"))
        self.assertEqual(sorted(expected), sorted(results))

    def test__configure_option_flavor(self):
        mock_novaclient = mock.MagicMock()
        mock_novaclient.flavors.create.side_effect = [
            fakes.FakeFlavor(id="id1"), fakes.FakeFlavor(id="id2")]
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = mock_novaclient
        self.context.conf.set("compute", "flavor_ref", "")
        self.context.conf.set("compute", "flavor_ref_alt", "")
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            self.context._configure_option("flavor_ref",
                                           mock_novaclient.flavors.create, 64)
            self.context._configure_option("flavor_ref_alt",
                                           mock_novaclient.flavors.create, 128)
            self.assertEqual(mock_novaclient.flavors.create.call_count, 2)
            expected = ("id1", "id2")
            results = (self.context.conf.get("compute", "flavor_ref"),
                       self.context.conf.get("compute", "flavor_ref_alt"))
            self.assertEqual(sorted(expected), sorted(results))

    @mock.patch("six.moves.builtins.open")
    def test__configure_option_image(self, mock_open):
        mock_glanceclient = mock.MagicMock()
        mock_glanceclient.images.create.side_effect = [
            fakes.FakeImage(id="id1"), fakes.FakeImage(id="id2")]
        mock_glance = mock.MagicMock()
        mock_glance.Client.return_value = mock_glanceclient
        self.context.conf.set("compute", "image_ref", "")
        self.context.conf.set("compute", "image_ref_alt", "")
        with mock.patch.dict("sys.modules", {"glanceclient": mock_glance}):
            self.context._configure_option("image_ref",
                                           mock_glanceclient.images.create)
            self.context._configure_option("image_ref_alt",
                                           mock_glanceclient.images.create)
            self.assertEqual(mock_glanceclient.images.create.call_count, 2)
            expected = ("id1", "id2")
            results = (self.context.conf.get("compute", "image_ref"),
                       self.context.conf.get("compute", "image_ref_alt"))
            self.assertEqual(sorted(expected), sorted(results))

    def test__configure_network_if_neutron(self):
        fake_neutronclient = mock.MagicMock()
        fake_neutronclient.list_networks.return_value = {
            "networks": [
                {
                    "status": "ACTIVE",
                    "id": "test_id",
                    "router:external": True
                }
            ]
        }
        mock_neutron = mock.MagicMock()
        mock_neutron.client.Client.return_value = fake_neutronclient
        with mock.patch.dict("sys.modules", {"neutronclient.neutron":
                                             mock_neutron}):
            self.conf_generator.available_services = ["neutron"]
            self.conf_generator._configure_network()
            expected = (("public_network_id", "test_id"),)
            results = self._remove_default_section(
                self.conf_generator.conf.items("network"))
            self.assertEqual(sorted(expected), sorted(results))

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

    @mock.patch("rally.verification.tempest.config.os.path.exists",
                return_value=False)
    @mock.patch("rally.verification.tempest.config.os.makedirs")
    def test__configure_oslo_concurrency(self, mock_makedirs, mock_exists):
        self.conf_generator._configure_oslo_concurrency()
        lock_path = os.path.join(
            self.conf_generator.data_dir, "lock_files_%s" % self.deployment)
        mock_makedirs.assert_called_once_with(lock_path)
        expected = (("lock_path", lock_path),)
        results = self._remove_default_section(
            self.conf_generator.conf.items("oslo_concurrency"))
        self.assertEqual(sorted(expected), sorted(results))

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
        options = self._remove_default_section(
            self.conf_generator.conf.items("service_available"))
        self.assertEqual(sorted(expected), sorted(options))

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

    @mock.patch("six.moves.builtins.open",
                side_effect=mock.mock_open(), create=True)
    def test__write_config(self, mock_open):
        conf_path = "/path/to/fake/conf"
        conf_data = mock.Mock()
        config._write_config(conf_path, conf_data)
        mock_open.assert_called_once_with(conf_path, "w+")
        conf_data.write.assert_called_once_with(mock_open.side_effect())
