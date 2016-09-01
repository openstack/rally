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

import ddt
import mock
from oslo_config import cfg
import requests
import six
from six.moves.urllib import parse

from rally import exceptions
from rally.verification.tempest import config
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
        "admin_domain_name": "Default",
        "https_insecure": False,
        "https_cacert": "/path/to/cacert/file"
    }
}


@ddt.ddt
class TempestConfigTestCase(test.TestCase):

    def setUp(self):
        super(TempestConfigTestCase, self).setUp()

        mock.patch("rally.common.objects.deploy.db.deployment_get",
                   return_value=CREDS).start()
        mock.patch("rally.osclients.Clients").start()
        self.mock_isfile = mock.patch("os.path.isfile",
                                      return_value=True).start()

        self.tempest_conf = config.TempestConfig("fake_deployment")

    @mock.patch("os.rename")
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    @mock.patch("requests.get", return_value=mock.MagicMock(status_code=200))
    def test__download_image_success(self, mock_get,
                                     mock_open, mock_rename):
        self.mock_isfile.return_value = False
        self.tempest_conf._download_image()
        mock_get.assert_called_once_with(
            CONF.tempest.img_url, stream=True)

    @mock.patch("requests.get")
    @ddt.data(404, 500)
    def test__download_image_failure(self, status_code, mock_get):
        self.mock_isfile.return_value = False
        mock_get.return_value = mock.MagicMock(status_code=status_code)
        self.assertRaises(exceptions.TempestConfigCreationFailure,
                          self.tempest_conf._download_image)

    @mock.patch("requests.get", side_effect=requests.ConnectionError())
    def test__download_image_connection_error(self, mock_requests_get):
        self.mock_isfile.return_value = False
        self.assertRaises(exceptions.TempestConfigCreationFailure,
                          self.tempest_conf._download_image)

    @ddt.data({"publicURL": "test_url"},
              {"interface": "public", "url": "test_url"})
    def test__get_service_url(self, endpoint):
        mock_catalog = mock.MagicMock()
        mock_catalog.get_endpoints.return_value = {
            "test_service_type": [endpoint]}

        self.tempest_conf.keystone.service_catalog = mock_catalog
        self.tempest_conf.clients.services.return_value = {
            "test_service_type": "test_service"}
        self.assertEqual(
            self.tempest_conf._get_service_url("test_service"), "test_url")

    def test__configure_auth(self):
        self.tempest_conf._configure_auth()

        expected = (
            ("admin_username", CREDS["admin"]["username"]),
            ("admin_password", CREDS["admin"]["password"]),
            ("admin_project_name", CREDS["admin"]["tenant_name"]),
            ("admin_domain_name", CREDS["admin"]["admin_domain_name"]))
        result = self.tempest_conf.conf.items("auth")
        for item in expected:
            self.assertIn(item, result)

    @ddt.data("data_processing", "data-processing")
    def test__configure_data_processing(self, service_type):
        self.tempest_conf.available_services = ["sahara"]

        self.tempest_conf.clients.services.return_value = {
            service_type: "sahara"}
        self.tempest_conf._configure_data_processing()
        self.assertEqual(
            self.tempest_conf.conf.get(
                "data-processing", "catalog_type"), service_type)

    def test__configure_identity(self):
        self.tempest_conf._configure_identity()

        expected = (
            ("region", CREDS["admin"]["region_name"]),
            ("auth_version", "v2"),
            ("uri", CREDS["admin"]["auth_url"][:-1]),
            ("uri_v3", CREDS["admin"]["auth_url"].replace("/v2.0/", "/v3")),
            ("disable_ssl_certificate_validation",
             str(CREDS["admin"]["https_insecure"])),
            ("ca_certificates_file", CREDS["admin"]["https_cacert"]))
        result = self.tempest_conf.conf.items("identity")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_network_if_neutron(self):
        self.tempest_conf.available_services = ["neutron"]
        client = self.tempest_conf.clients.neutron()
        client.list_networks.return_value = {
            "networks": [
                {
                    "status": "ACTIVE",
                    "id": "test_id",
                    "router:external": True
                }
            ]
        }

        self.tempest_conf._configure_network()
        self.assertEqual(
            self.tempest_conf.conf.get("network",
                                       "public_network_id"), "test_id")

    def test__configure_network_if_nova(self):
        self.tempest_conf.available_services = ["nova"]
        client = self.tempest_conf.clients.nova()
        client.networks.list.return_value = [
            mock.MagicMock(human_id="fake-network")]

        self.tempest_conf._configure_network()

        expected = {"compute": ("fixed_network_name", "fake-network"),
                    "validation": ("network_for_ssh", "fake-network")}
        for section, option in six.iteritems(expected):
            result = self.tempest_conf.conf.items(section)
            self.assertIn(option, result)

    @ddt.data({}, {"version": "4.1.0", "args": ("extensions", "/extensions"),
                   "kwargs": {"retrieve_all": True}})
    @ddt.unpack
    def test__configure_network_feature_enabled(
            self, version="4.0.0", args=("/extensions",), kwargs={}):
        self.tempest_conf.available_services = ["neutron"]
        client = self.tempest_conf.clients.neutron()
        client.list_ext.return_value = {
            "extensions": [
                {"alias": "dvr"},
                {"alias": "extra_dhcp_opt"},
                {"alias": "extraroute"}
            ]
        }

        mock.patch("neutronclient.version.__version__", version).start()
        self.tempest_conf._configure_network_feature_enabled()
        client.list_ext.assert_called_once_with(*args, **kwargs)
        self.assertEqual(self.tempest_conf.conf.get(
            "network-feature-enabled", "api_extensions"),
            "dvr,extra_dhcp_opt,extraroute")

    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists", return_value=False)
    def test__configure_oslo_concurrency(self, mock_exists, mock_makedirs):
        self.tempest_conf._configure_oslo_concurrency()

        lock_path = os.path.join(
            self.tempest_conf.data_dir, "lock_files_fake_deployment")
        mock_makedirs.assert_called_with(lock_path)
        self.assertEqual(
            self.tempest_conf.conf.get(
                "oslo_concurrency", "lock_path"), lock_path)

    def test__configure_object_storage(self):
        self.tempest_conf._configure_object_storage()

        expected = (
            ("operator_role", CONF.tempest.swift_operator_role),
            ("reseller_admin_role", CONF.tempest.swift_reseller_admin_role))
        result = self.tempest_conf.conf.items("object-storage")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_orchestration(self):
        self.tempest_conf._configure_orchestration()

        expected = (
            ("stack_owner_role", CONF.tempest.heat_stack_owner_role),
            ("stack_user_role", CONF.tempest.heat_stack_user_role))
        result = self.tempest_conf.conf.items("orchestration")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_scenario(self):
        self.tempest_conf._configure_scenario()

        image_name = parse.urlparse(
            config.CONF.tempest.img_url).path.split("/")[-1]
        expected = (("img_dir", self.tempest_conf.data_dir),
                    ("img_file", image_name))
        result = self.tempest_conf.conf.items("scenario")
        for item in expected:
            self.assertIn(item, result)

    def test__configure_service_available(self):
        available_services = ("nova", "cinder", "glance", "sahara")
        self.tempest_conf.available_services = available_services
        self.tempest_conf._configure_service_available()

        expected = (
            ("neutron", "False"), ("heat", "False"), ("nova", "True"),
            ("swift", "False"), ("cinder", "True"), ("sahara", "True"),
            ("glance", "True"))
        result = self.tempest_conf.conf.items("service_available")
        for item in expected:
            self.assertIn(item, result)

    @ddt.data({}, {"service": "neutron", "connect_method": "floating"})
    @ddt.unpack
    def test__configure_validation(self, service="nova",
                                   connect_method="fixed"):
        self.tempest_conf.available_services = [service]
        self.tempest_conf._configure_validation()

        expected = (("run_validation", "True"),
                    ("connect_method", connect_method))
        result = self.tempest_conf.conf.items("validation")
        for item in expected:
            self.assertIn(item, result)

    @mock.patch("rally.verification.tempest.config._write_config")
    @mock.patch("inspect.getmembers")
    def test_generate(self, mock_inspect_getmembers, mock__write_config):
        configure_something_method = mock.MagicMock()
        mock_inspect_getmembers.return_value = [("_configure_something",
                                                 configure_something_method)]

        fake_extra_conf = mock.MagicMock()
        fake_extra_conf.sections.return_value = ["section"]
        fake_extra_conf.items.return_value = [("option", "value")]

        self.tempest_conf.generate("/path/to/fake/conf", fake_extra_conf)
        self.assertEqual(configure_something_method.call_count, 1)
        self.assertIn(("option", "value"),
                      self.tempest_conf.conf.items("section"))
        self.assertEqual(mock__write_config.call_count, 1)

    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    def test__write_config(self, mock_open):
        conf_path = "/path/to/fake/conf"
        conf_data = mock.Mock()

        config._write_config(conf_path, conf_data)
        mock_open.assert_called_once_with(conf_path, "w+")
        conf_data.write.assert_called_once_with(mock_open.side_effect())


class TempestResourcesContextTestCase(test.TestCase):

    def setUp(self):
        super(TempestResourcesContextTestCase, self).setUp()

        mock.patch("rally.common.objects.deploy.db.deployment_get",
                   return_value=CREDS).start()
        mock.patch("rally.osclients.Clients").start()

        fake_verification = {"uuid": "uuid"}
        self.context = config.TempestResourcesContext("fake_deployment",
                                                      fake_verification,
                                                      "/fake/path/to/config")
        self.context.conf.add_section("compute")
        self.context.conf.add_section("orchestration")

    @mock.patch("rally.plugins.openstack.wrappers."
                "network.NeutronWrapper.create_network")
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    def test_options_configured_manually(
            self, mock_open, mock_neutron_wrapper_create_network):
        self.context.available_services = ["glance", "heat", "nova", "neutron"]

        self.context.conf.set("compute", "image_ref", "id1")
        self.context.conf.set("compute", "image_ref_alt", "id2")
        self.context.conf.set("compute", "flavor_ref", "id3")
        self.context.conf.set("compute", "flavor_ref_alt", "id4")
        self.context.conf.set("compute", "fixed_network_name", "name1")
        self.context.conf.set("orchestration", "instance_type", "id5")

        self.context.__enter__()

        glanceclient = self.context.clients.glance()
        novaclient = self.context.clients.nova()

        self.assertEqual(glanceclient.images.create.call_count, 0)
        self.assertEqual(novaclient.flavors.create.call_count, 0)
        self.assertEqual(mock_neutron_wrapper_create_network.call_count, 0)

    def test__create_tempest_roles(self):
        role1 = CONF.tempest.swift_operator_role
        role2 = CONF.tempest.swift_reseller_admin_role
        role3 = CONF.tempest.heat_stack_owner_role
        role4 = CONF.tempest.heat_stack_user_role

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
        self.context._configure_option("compute",
                                       "flavor_ref", create_method, 64)
        self.assertEqual(create_method.call_count, 1)

        result = self.context.conf.get("compute", "flavor_ref")
        self.assertEqual("id1", result)

    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test__discover_or_create_image_when_image_exists(self, mock_wrap):
        client = mock_wrap.return_value
        client.list_images.return_value = [fakes.FakeImage(name="CirrOS")]

        image = self.context._discover_or_create_image()
        self.assertEqual("CirrOS", image.name)
        self.assertEqual(0, client.create_image.call_count)
        self.assertEqual(0, len(self.context._created_images))

    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test__discover_or_create_image(self, mock_wrap):
        client = mock_wrap.return_value

        image = self.context._discover_or_create_image()
        self.assertEqual(image, client.create_image.return_value)
        self.assertEqual(self.context._created_images[0],
                         client.create_image.return_value)
        mock_wrap.assert_called_once_with(self.context.clients.glance,
                                          self.context)
        client.create_image.assert_called_once_with(
            container_format=CONF.tempest.img_container_format,
            image_location=mock.ANY,
            disk_format=CONF.tempest.img_disk_format,
            name=mock.ANY,
            visibility="public")

    def test__discover_or_create_flavor_when_flavor_exists(self):
        client = self.context.clients.nova()
        client.flavors.list.return_value = [fakes.FakeFlavor(id="id1", ram=64,
                                                             vcpus=1, disk=0)]

        flavor = self.context._discover_or_create_flavor(64)
        self.assertEqual("id1", flavor.id)
        self.assertEqual(0, len(self.context._created_flavors))

    def test__discover_or_create_flavor(self):
        client = self.context.clients.nova()
        client.flavors.create.side_effect = [fakes.FakeFlavor(id="id1")]

        flavor = self.context._discover_or_create_flavor(64)
        self.assertEqual("id1", flavor.id)
        self.assertEqual("id1", self.context._created_flavors[0].id)

    def test__create_network_resources(self):
        client = self.context.clients.neutron()
        fake_network = {
            "id": "nid1",
            "name": "network",
            "status": "status"}

        client.create_network.side_effect = [{"network": fake_network}]
        client.create_router.side_effect = [{"router": {"id": "rid1"}}]
        client.create_subnet.side_effect = [{"subnet": {"id": "subid1"}}]

        network = self.context._create_network_resources()
        self.assertEqual("nid1", network["id"])
        self.assertEqual("nid1", self.context._created_networks[0]["id"])
        self.assertEqual("rid1",
                         self.context._created_networks[0]["router_id"])
        self.assertEqual("subid1",
                         self.context._created_networks[0]["subnets"][0])

    def test__cleanup_tempest_roles(self):
        self.context._created_roles = [fakes.FakeRole(), fakes.FakeRole()]

        self.context._cleanup_tempest_roles()
        client = self.context.clients.keystone()
        self.assertEqual(client.roles.delete.call_count, 2)

    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test__cleanup_images(self, mock_wrap):
        self.context._created_images = [fakes.FakeImage(id="id1"),
                                        fakes.FakeImage(id="id2")]

        self.context.conf.set("compute", "image_ref", "id1")
        self.context.conf.set("compute", "image_ref_alt", "id2")

        wrapper = mock_wrap.return_value
        wrapper.get_image.side_effect = [
            fakes.FakeImage(id="id1", status="DELETED"),
            fakes.FakeImage(id="id2"),
            fakes.FakeImage(id="id2", status="DELETED")]

        self.context._cleanup_images()
        client = self.context.clients.glance()
        client.images.delete.assert_has_calls([mock.call("id1"),
                                               mock.call("id2")])

        self.assertEqual("", self.context.conf.get("compute", "image_ref"))
        self.assertEqual("", self.context.conf.get("compute", "image_ref_alt"))

    def test__cleanup_flavors(self):
        self.context._created_flavors = [fakes.FakeFlavor(id="id1"),
                                         fakes.FakeFlavor(id="id2"),
                                         fakes.FakeFlavor(id="id3")]

        self.context.conf.set("compute", "flavor_ref", "id1")
        self.context.conf.set("compute", "flavor_ref_alt", "id2")
        self.context.conf.set("orchestration", "instance_type", "id3")

        self.context._cleanup_flavors()
        client = self.context.clients.nova()
        self.assertEqual(client.flavors.delete.call_count, 3)

        self.assertEqual("", self.context.conf.get("compute", "flavor_ref"))
        self.assertEqual("", self.context.conf.get("compute",
                                                   "flavor_ref_alt"))
        self.assertEqual("", self.context.conf.get("orchestration",
                                                   "instance_type"))

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
