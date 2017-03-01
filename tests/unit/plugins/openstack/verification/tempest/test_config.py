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

import ddt
import mock
from oslo_config import cfg

from rally.plugins.openstack.verification.tempest import config
from tests.unit import fakes
from tests.unit import test


CONF = cfg.CONF


CREDS = {
    "admin": {
        "username": "admin",
        "tenant_name": "admin",
        "password": "admin-12345",
        "auth_url": "http://test:5000/v2.0/",
        "permission": "admin",
        "region_name": "test",
        "https_insecure": False,
        "https_cacert": "/path/to/cacert/file",
        "user_domain_name": "admin",
        "project_domain_name": "admin"
    },
    "uuid": "fake_deployment"
}

PATH = "rally.plugins.openstack.verification.tempest.config"


@ddt.ddt
class TempestConfigfileManagerTestCase(test.TestCase):

    def setUp(self):
        super(TempestConfigfileManagerTestCase, self).setUp()

        mock.patch("rally.osclients.Clients").start()

        deployment = fakes.FakeDeployment(**CREDS)
        self.tempest = config.TempestConfigfileManager(deployment)

    def test__configure_auth(self):
        self.tempest.conf.add_section("auth")
        self.tempest._configure_auth()

        expected = (
            ("admin_username", CREDS["admin"]["username"]),
            ("admin_password", CREDS["admin"]["password"]),
            ("admin_project_name", CREDS["admin"]["tenant_name"]),
            ("admin_domain_name", CREDS["admin"]["user_domain_name"]))
        result = self.tempest.conf.items("auth")
        for item in expected:
            self.assertIn(item, result)

    @ddt.data("data_processing", "data-processing")
    def test__configure_data_processing(self, service_type):
        self.tempest.available_services = ["sahara"]

        self.tempest.clients.services.return_value = {
            service_type: "sahara"}
        self.tempest.conf.add_section("data-processing")
        self.tempest._configure_data_processing()
        self.assertEqual(
            self.tempest.conf.get(
                "data-processing", "catalog_type"), service_type)

    def test__configure_identity(self):
        self.tempest.conf.add_section("identity")
        self.tempest._configure_identity()

        expected = (
            ("region", CREDS["admin"]["region_name"]),
            ("auth_version", "v2"),
            ("uri", CREDS["admin"]["auth_url"][:-1]),
            ("uri_v3", CREDS["admin"]["auth_url"].replace("/v2.0/", "/v3")),
            ("disable_ssl_certificate_validation",
             str(CREDS["admin"]["https_insecure"])),
            ("ca_certificates_file", CREDS["admin"]["https_cacert"]))
        result = self.tempest.conf.items("identity")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_network_if_neutron(self):
        self.tempest.available_services = ["neutron"]
        client = self.tempest.clients.neutron()
        client.list_networks.return_value = {
            "networks": [
                {
                    "status": "ACTIVE",
                    "id": "test_id",
                    "name": "test_name",
                    "router:external": True
                }
            ]
        }

        self.tempest.conf.add_section("network")
        self.tempest._configure_network()
        self.assertEqual(self.tempest.conf.get("network", "public_network_id"),
                         "test_id")
        self.assertEqual(self.tempest.conf.get("network",
                                               "floating_network_name"),
                         "test_name")

    def test__configure_network_if_nova(self):
        self.tempest.available_services = ["nova"]
        client = self.tempest.clients.nova()
        client.networks.list.return_value = [
            mock.MagicMock(human_id="fake-network")]

        self.tempest.conf.add_section("compute")
        self.tempest.conf.add_section("validation")
        self.tempest._configure_network()

        expected = {"compute": ("fixed_network_name", "fake-network"),
                    "validation": ("network_for_ssh", "fake-network")}
        for section, option in expected.items():
            result = self.tempest.conf.items(section)
            self.assertIn(option, result)

    def test__configure_network_feature_enabled(self):
        self.tempest.available_services = ["neutron"]
        client = self.tempest.clients.neutron()
        client.list_ext.return_value = {
            "extensions": [
                {"alias": "dvr"},
                {"alias": "extra_dhcp_opt"},
                {"alias": "extraroute"}
            ]
        }

        self.tempest.conf.add_section("network-feature-enabled")
        self.tempest._configure_network_feature_enabled()
        client.list_ext.assert_called_once_with("extensions", "/extensions",
                                                retrieve_all=True)
        self.assertEqual(self.tempest.conf.get(
            "network-feature-enabled", "api_extensions"),
            "dvr,extra_dhcp_opt,extraroute")

    def test__configure_object_storage(self):
        self.tempest.conf.add_section("object-storage")
        self.tempest._configure_object_storage()

        expected = (
            ("operator_role", CONF.tempest.swift_operator_role),
            ("reseller_admin_role", CONF.tempest.swift_reseller_admin_role))
        result = self.tempest.conf.items("object-storage")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_orchestration(self):
        self.tempest.conf.add_section("orchestration")
        self.tempest._configure_orchestration()

        expected = (
            ("stack_owner_role", CONF.tempest.heat_stack_owner_role),
            ("stack_user_role", CONF.tempest.heat_stack_user_role))
        result = self.tempest.conf.items("orchestration")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_service_available(self):
        available_services = ("nova", "cinder", "glance", "sahara")
        self.tempest.available_services = available_services
        self.tempest.conf.add_section("service_available")
        self.tempest._configure_service_available()

        expected = (
            ("neutron", "False"), ("heat", "False"), ("nova", "True"),
            ("swift", "False"), ("cinder", "True"), ("sahara", "True"),
            ("glance", "True"))
        result = self.tempest.conf.items("service_available")
        for item in expected:
            self.assertIn(item, result)

    @ddt.data({}, {"service": "neutron", "connect_method": "floating"})
    @ddt.unpack
    def test__configure_validation(self, service="nova",
                                   connect_method="fixed"):
        self.tempest.available_services = [service]
        self.tempest.conf.add_section("validation")
        self.tempest._configure_validation()

        expected = (("connect_method", connect_method), )
        result = self.tempest.conf.items("validation")
        for item in expected:
            self.assertIn(item, result)

    @mock.patch("%s.six.StringIO" % PATH)
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    @mock.patch("inspect.getmembers")
    def test_create(self, mock_inspect_getmembers, mock_open, mock_string_io):
        configure_something_method = mock.MagicMock()
        mock_inspect_getmembers.return_value = [("_configure_something",
                                                 configure_something_method)]
        self.tempest.conf.read = mock.Mock()
        self.tempest.conf.write = mock.Mock()
        self.tempest.conf.read.return_value = "[section]\noption = value"

        fake_extra_conf = {"section2": {"option2": "value2"}}
        self.tempest.create("/path/to/fake/conf", fake_extra_conf)

        self.assertEqual(configure_something_method.call_count, 1)
        self.assertIn(("option2", "value2"),
                      self.tempest.conf.items("section2"))
        mock_open.assert_called_once_with("/path/to/fake/conf", "w")
        self.tempest.conf.write.assert_has_calls(
            [mock.call(mock_open.side_effect()),
             mock.call(mock_string_io.return_value)])
        mock_string_io.return_value.getvalue.assert_called_once_with()
