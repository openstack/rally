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

from rally.verification.tempest import config
from tests.unit import fakes
from tests.unit import test

CONF = cfg.CONF


class ConfigTestCase(test.TestCase):

    @mock.patch("rally.objects.deploy.db.deployment_get")
    @mock.patch("rally.osclients.Clients.services",
                return_value={"test_service_type": "test_service"})
    @mock.patch("rally.osclients.Clients.verified_keystone")
    @mock.patch("rally.verification.tempest.config.os.path.isfile",
                return_value=True)
    def setUp(self, mock_isfile, mock_verified_keystone, mock_services,
              mock_get):
        super(ConfigTestCase, self).setUp()
        self.endpoint = {"username": "test",
                         "tenant_name": "test",
                         "password": "test",
                         "auth_url": "http://test/v2.0",
                         "permission": "admin",
                         "admin_domain_name": "Default"}
        mock_get.return_value = {"admin": self.endpoint}
        self.deployment = "fake_deployment"
        self.conf_generator = config.TempestConf(self.deployment)
        self.conf_generator.clients.services = mock_services

        keystone_patcher = mock.patch("rally.osclients.create_keystone_client")
        keystone_patcher.start()
        self.addCleanup(keystone_patcher.stop)

    def _remove_default_section(self, items):
        # getting items from configparser by specified section name
        # retruns also values from DEFAULT section
        defaults = (("log_file", "tempest.log"), ("debug", "True"),
                    ("use_stderr", "False"))
        return [item for item in items if item not in defaults]

    @mock.patch("rally.verification.tempest.config.requests")
    @mock.patch("rally.verification.tempest.config.os.rename")
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open(),
                create=True)
    def test__load_img_success(self, mock_open, mock_rename, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 200
        mock_requests.get.return_value = mock_result
        self.conf_generator._load_img()
        cirros_url = ("http://download.cirros-cloud.net/%s/%s" %
                      (CONF.image.cirros_version,
                       CONF.image.cirros_image))
        mock_requests.get.assert_called_once_with(cirros_url, stream=True)

    @mock.patch("rally.verification.tempest.config.requests")
    def test__load_img_notfound(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 404
        mock_requests.get.return_value = mock_result
        self.assertRaises(config.TempestConfigCreationFailure,
                          self.conf_generator._load_img)

    def test__get_url(self):
        service = "test_service"
        service_type = "test_service_type"
        url = "test_url"
        # mocked at setUp
        self.conf_generator.keystoneclient.auth_ref = {
            "serviceCatalog": [{
                "name": service,
                "type": service_type,
                "endpoints": [{"publicURL": url}]
            }]}
        self.assertEqual(self.conf_generator._get_url(service), url)

    @mock.patch("rally.verification.tempest.config.TempestConf"
                "._get_url")
    def test__set_boto(self, mock_get_url):
        url = "test_url"
        mock_get_url.return_value = url
        self.conf_generator._set_boto()
        expected = (("ec2_url", url),
                    ("s3_url", url),
                    ("build_interval", "1"),
                    ("build_timeout", "196"),
                    ("http_socket_timeout", "30"),
                    ("instance_type", "m1.nano"),
                    ("ssh_user", "cirros"),
                    ("s3_materials_path",
                     os.path.join(self.conf_generator.data_path,
                                  "s3materials")))
        results = self._remove_default_section(
            self.conf_generator.conf.items("boto"))
        self.assertEqual(sorted(expected), sorted(results))

    def test__set_compute_admin(self):
        self.conf_generator._set_compute_admin()
        expected = [("username", self.endpoint["username"]),
                    ("password", self.endpoint["password"]),
                    ("tenant_name", self.endpoint["tenant_name"])]
        results = self._remove_default_section(
            self.conf_generator.conf.items("compute-admin"))
        self.assertEqual(sorted(expected), sorted(results))

    def test__set_compute_flavors(self):
        mock_novaclient = mock.MagicMock()
        mock_novaclient.flavors.list.return_value = [
            fakes.FakeFlavor(id="id1"), fakes.FakeFlavor(id="id2")]
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = mock_novaclient
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            self.conf_generator._set_compute_flavors()
            expected = ("id1", "id2")
            results = (self.conf_generator.conf.get("compute", "flavor_ref"),
                       self.conf_generator.conf.get("compute",
                                                    "flavor_ref_alt"))
            self.assertEqual(sorted(expected), sorted(results))

    def test__set_compute_flavors_create(self):
        mock_novaclient = mock.MagicMock()
        mock_novaclient.flavors.list.return_value = []
        mock_novaclient.flavors.create.side_effect = [
            fakes.FakeFlavor(id="id1"), fakes.FakeFlavor(id="id2")]
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = mock_novaclient
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            self.conf_generator._set_compute_flavors()
            self.assertEqual(mock_novaclient.flavors.create.call_count, 2)
            expected = ("id1", "id2")
            results = (self.conf_generator.conf.get("compute", "flavor_ref"),
                       self.conf_generator.conf.get("compute",
                                                    "flavor_ref_alt"))
            self.assertEqual(sorted(expected), sorted(results))

    def test__set_compute_flavors_create_fails(self):
        mock_novaclient = mock.MagicMock()
        mock_novaclient.flavors.list.return_value = []
        mock_novaclient.flavors.create.side_effect = Exception()
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = mock_novaclient
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            self.assertRaises(config.TempestConfigCreationFailure,
                              self.conf_generator._set_compute_flavors)

    def test__set_compute_images(self):
        mock_glanceclient = mock.MagicMock()
        mock_glanceclient.images.list.return_value = [
            fakes.FakeImage(id="id1", name="cirros1"),
            fakes.FakeImage(id="id2", name="cirros2")]
        mock_glance = mock.MagicMock()
        mock_glance.Client.return_value = mock_glanceclient
        with mock.patch.dict("sys.modules", {"glanceclient": mock_glance}):
            self.conf_generator._set_compute_images()
            expected = ("id1", "id2")
            results = (self.conf_generator.conf.get("compute", "image_ref"),
                       self.conf_generator.conf.get("compute",
                                                    "image_ref_alt"))
            self.assertEqual(sorted(expected), sorted(results))

    @mock.patch("six.moves.builtins.open")
    def test__set_compute_images_create(self, mock_open):
        mock_glanceclient = mock.MagicMock()
        mock_glanceclient.images.list.return_value = []
        mock_glanceclient.images.create.side_effect = [
            fakes.FakeImage(id="id1"), fakes.FakeImage(id="id2")]
        mock_glance = mock.MagicMock()
        mock_glance.Client.return_value = mock_glanceclient
        with mock.patch.dict("sys.modules", {"glanceclient": mock_glance}):
            self.conf_generator._set_compute_images()
            self.assertEqual(mock_glanceclient.images.create.call_count, 2)
            expected = ("id1", "id2")
            results = (self.conf_generator.conf.get("compute", "image_ref"),
                       self.conf_generator.conf.get("compute",
                                                    "image_ref_alt"))
            self.assertEqual(sorted(expected), sorted(results))

    def test__set_compute_images_create_fails(self):
        mock_glanceclient = mock.MagicMock()
        mock_glanceclient.images.list.return_value = []
        mock_glanceclient.images.create.side_effect = Exception()
        mock_glance = mock.MagicMock()
        mock_glance.Client.return_value = mock_glanceclient
        with mock.patch.dict("sys.modules", {"glanceclient": mock_glance}):
            self.assertRaises(config.TempestConfigCreationFailure,
                              self.conf_generator._set_compute_images)

    def test__set_compute_ssh_connect_method_if_neutron(self):
        self.conf_generator._set_compute_ssh_connect_method()
        self.assertEqual("fixed",
                         self.conf_generator.conf.get("compute",
                                                      "ssh_connect_method"))
        # if neutron is available
        self.conf_generator.available_services = ["neutron"]
        self.conf_generator._set_compute_ssh_connect_method()
        self.assertEqual("floating",
                         self.conf_generator.conf.get("compute",
                                                      "ssh_connect_method"))

    @mock.patch("rally.verification.tempest.config.os.path.exists",
                return_value=False)
    @mock.patch("rally.verification.tempest.config.os.makedirs")
    def test__set_default(self, mock_makedirs, mock_exists):
        self.conf_generator._set_default()
        lock_path = os.path.join(self.conf_generator.data_path, "lock_files_%s"
                                 % self.deployment)
        mock_makedirs.assert_called_once_with(lock_path)
        expected = (("debug", "True"), ("log_file", "tempest.log"),
                    ("use_stderr", "False"),
                    ("lock_path", lock_path))
        results = self.conf_generator.conf.items("DEFAULT")
        self.assertEqual(sorted(expected), sorted(results))

    def test__set_identity(self):
        self.conf_generator._set_identity()
        expected = (("username", self.endpoint["username"]),
                    ("password", self.endpoint["password"]),
                    ("tenant_name", self.endpoint["tenant_name"]),
                    ("alt_username", self.endpoint["username"]),
                    ("alt_password", self.endpoint["password"]),
                    ("alt_tenant_name", self.endpoint["tenant_name"]),
                    ("admin_username", self.endpoint["username"]),
                    ("admin_password", self.endpoint["password"]),
                    ("admin_tenant_name", self.endpoint["username"]),
                    ("admin_domain_name", self.endpoint["admin_domain_name"]),
                    ("uri", self.endpoint["auth_url"]),
                    ("uri_v3", self.endpoint["auth_url"].replace("/v2.0",
                                                                 "/v3")))
        results = self._remove_default_section(
            self.conf_generator.conf.items("identity"))
        self.assertEqual(sorted(expected), sorted(results))

    def test__set_network_if_neutron(self):
        fake_neutronclient = mock.MagicMock()
        fake_neutronclient.list_networks.return_value = {"networks": [
                                                         {"status": "ACTIVE",
                                                          "id": "test_id",
                                                          "router:external":
                                                          True}]}
        fake_neutronclient.list_routers.return_value = {"routers": [
                                                        {"id": "test_router"}]}
        fake_neutronclient.list_subnets.return_value = {"subnets": [
                                                        {"cidr":
                                                         "10.0.0.0/24"}]}
        mock_neutron = mock.MagicMock()
        mock_neutron.client.Client.return_value = fake_neutronclient
        with mock.patch.dict("sys.modules", {"neutronclient.neutron":
                                             mock_neutron}):
            self.conf_generator.available_services = ["neutron"]
            self.conf_generator._set_network()
            expected = (("default_network", "10.0.0.0/24"),
                        ("tenant_networks_reachable", "false"),
                        ("api_version", "2.0"),
                        ("public_network_id", "test_id"),
                        ("public_router_id", "test_router"))
            results = self._remove_default_section(
                self.conf_generator.conf.items("network"))
            self.assertEqual(sorted(expected), sorted(results))

    def test__set_network_if_nova(self):
        network = "10.0.0.0/24"
        mock_novaclient = mock.MagicMock()
        mock_network = mock.MagicMock()
        mock_network.cidr = network
        mock_novaclient.networks.list.return_value = [mock_network]
        mock_nova = mock.MagicMock()
        mock_nova.client.Client.return_value = mock_novaclient
        with mock.patch.dict("sys.modules", {"novaclient": mock_nova}):
            self.conf_generator._set_network()
            self.assertEqual(network,
                             self.conf_generator.conf.get("network",
                                                          "default_network"))

    @mock.patch("rally.verification.tempest.config.requests")
    def test__set_service_available(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 404
        mock_requests.get.return_value = mock_result
        available_services = ("nova", "cinder", "glance")
        self.conf_generator.available_services = available_services
        self.conf_generator._set_service_available()
        expected = (("neutron", "False"), ("heat", "False"),
                    ("ceilometer", "False"), ("swift", "False"),
                    ("cinder", "True"), ("nova", "True"),
                    ("glance", "True"), ("horizon", "False"))
        options = self._remove_default_section(
            self.conf_generator.conf.items("service_available"))
        self.assertEqual(sorted(expected), sorted(options))

    @mock.patch("rally.verification.tempest.config.requests")
    def test__set_service_available_horizon(self, mock_requests):
        mock_result = mock.MagicMock()
        mock_result.status_code = 200
        mock_requests.get.return_value = mock_result
        self.conf_generator._set_service_available()
        self.assertEqual(self.conf_generator.conf.get(
            "service_available", "horizon"), "True")

    @mock.patch("rally.verification.tempest.config.requests.get")
    def test__set_service_not_available_horizon(self, mock_requests_get):
        mock_requests_get.side_effect = requests.Timeout()
        self.conf_generator._set_service_available()
        self.assertEqual(self.conf_generator.conf.get(
            "service_available", "horizon"), "False")

    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open(),
                create=True)
    def test_write_config(self, mock_open):
        self.conf_generator.conf = mock.Mock()
        file_name = "/path/to/fake/conf"

        self.conf_generator.write_config(file_name)

        mock_open.assert_called_once_with(file_name, "w+")
        self.conf_generator.conf.write.assert_called_once_with(
            mock_open.side_effect())
