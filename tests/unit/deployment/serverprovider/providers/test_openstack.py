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

"""Tests for OpenStack VM provider."""

import textwrap

import jsonschema
import mock
from oslotest import mockpatch

from rally.deployment.serverprovider.providers import openstack as provider
from rally import exceptions
from tests.unit import fakes
from tests.unit import test

MOD_NAME = "rally.deployment.serverprovider.providers.openstack"
OSProvider = provider.OpenStackProvider


class FakeOSClients(object):

    def nova(self):
        return "nova"

    def glance(self):
        return "glance"


class OpenStackProviderTestCase(test.TestCase):

    def setUp(self):
        super(OpenStackProviderTestCase, self).setUp()
        self.useFixture(mockpatch.Patch(
            "rally.deployment.serverprovider.provider.ResourceManager"))

    def _get_valid_config(self):
        return {
            "image": {
                "url": "http://example.net/img.qcow2",
                "format": "qcow2",
                "name": "Image",
                "checksum": "0123456789abcdef",
            },
            "deployment_name": "rally-dep-1",
            "auth_url": "urlto",
            "user": "name",
            "password": "mypass",
            "tenant": "tenant",
            "flavor_id": "22"}

    def _init_mock_clients(self):
        self.clients = mock.MagicMock()

        self.image = mock.MagicMock()
        self.image.checksum = "0123456789abcdef"
        self.image.get = mock.MagicMock(return_value=self.image)
        self.image.id = "fake-uuid"
        self.glance_client = mock.Mock(return_value=self.image)
        self.glance_client.images.create = mock.Mock(return_value=self.image)
        self.glance_client.images.list = mock.Mock(return_value=[self.image])
        self.clients.glance = mock.Mock(return_value=self.glance_client)

        self.instance = mock.MagicMock()
        self.instance.status = "ACTIVE"

        self.nova_client = mock.MagicMock()
        self.nova_client.servers.create = mock.MagicMock(
            return_value=self.instance)

        self.clients.nova = mock.MagicMock(return_value=self.nova_client)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init(self, mock_osclients):
        cfg = self._get_valid_config()
        mock_osclients.Clients = mock.MagicMock(return_value=FakeOSClients())
        os_provider = OSProvider(mock.MagicMock(), cfg)
        self.assertEqual("nova", os_provider.nova)
        self.assertEqual("glance", os_provider.glance)

    @mock.patch("rally.osclients.Clients")
    def test_init_no_glance(self, mock_clients):
        mock_clients.return_value.glance.side_effect = KeyError("image")
        cfg = self._get_valid_config()
        provider = OSProvider(mock.MagicMock(), cfg)
        self.assertIsNone(provider.glance)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_no_user(self,
                                                               mock_osclients):
        cfg = self._get_valid_config()
        cfg.pop("user")
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_no_url(self,
                                                              mock_osclients):
        cfg = self._get_valid_config()
        del cfg["image"]["url"]
        del cfg["image"]["checksum"]
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_extra_key(
            self, mock_osclients):
        cfg = self._get_valid_config()
        cfg["aaaaa"] = "bbbbb"
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_init_with_invalid_conf_flavor_(self,
                                                               mock_osclients):
        cfg = self._get_valid_config()["user"] = 1111
        self.assertRaises(jsonschema.ValidationError, OSProvider,
                          mock.MagicMock(), cfg)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_with_valid_config(self,
                                                  mock_osclients):
        cfg = self._get_valid_config()
        OSProvider(mock.MagicMock(), cfg)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_with_valid_config_uuid(self, mock_osclients):
        cfg = self._get_valid_config()
        cfg["image"] = dict(uuid="289D7A51-1A0C-43C4-800D-706EA8A3CDF3")
        OSProvider(mock.MagicMock(), cfg)

    @mock.patch(
        "rally.deployment.serverprovider.providers.openstack.osclients")
    def test_openstack_provider_with_valid_config_checksum(self,
                                                           mock_osclients):
        cfg = self._get_valid_config()
        cfg["image"] = dict(checksum="checksum")
        OSProvider(mock.MagicMock(), cfg)

    def test_cloud_init_success_notready(self):
        fake_server = mock.Mock()
        fake_server.ssh.execute.return_value = (1, "", "")

        # Not ready yet -> False
        self.assertFalse(provider._cloud_init_success(fake_server))

    def test_cloud_init_success_completed(self):
        fake_server = mock.Mock()
        result_json_text = textwrap.dedent("""
        {
          "v1": {
            "errors": [],
            "datasource": "DataSourceFoo"
          }
        }
        """)
        fake_server.ssh.execute.return_value = (0, result_json_text, "")
        # Completed (with no errors) -> True
        self.assertTrue(provider._cloud_init_success(fake_server))

    def test_cloud_init_success_errors(self):
        fake_server = mock.Mock()
        result_json_text = textwrap.dedent("""
        {
          "v1": {
            "errors": ["omg!"],
            "datasource": "DataSourceFoo"
          }
        }
        """)
        fake_server.ssh.execute.return_value = (0, result_json_text, "")
        # Completed with errors -> Exception
        self.assertRaises(RuntimeError,
                          provider._cloud_init_success, fake_server)

    @mock.patch("time.sleep")
    @mock.patch(MOD_NAME + ".provider.Server")
    @mock.patch(MOD_NAME + ".osclients")
    @mock.patch(MOD_NAME + ".utils")
    def test_create_servers(self, mock_utils, mock_osclients,
                            mock_server, mock_sleep):
        fake_keypair = mock.Mock()
        fake_keypair.name = "fake_key_name"
        provider = OSProvider(mock.Mock(), self._get_valid_config())
        provider.sg = mock.Mock(id="33")
        provider.config["secgroup_name"] = "some_sg"
        provider.nova = mock.Mock()
        provider.get_image_uuid = mock.Mock(return_value="fake_image_uuid")
        provider.get_userdata = mock.Mock(return_value="fake_userdata")
        provider.get_nics = mock.Mock(return_value="fake_nics")
        provider.create_keypair = mock.Mock(return_value=(fake_keypair,
                                                          "fake_path"))
        mock_utils.wait_for = lambda x, **kw: x
        mock_server.return_value = fake_server = mock.Mock()
        provider.nova.servers.create.return_value = fake_instance = mock.Mock()
        fake_instance.accessIPv4 = None
        fake_instance.accessIPv6 = None
        fake_instance.addresses = {"private": [{"addr": "1.2.3.4"}]}

        servers = provider.create_servers()
        provider.nova.security_groups.create.assert_called_once_with(
            provider.config["secgroup_name"], provider.config["secgroup_name"])

        mock_server.assert_called_once_with(host="1.2.3.4", user="root",
                                            key="fake_path")
        self.assertEqual([fake_server], servers)
        fake_server.ssh.wait.assert_called_once_with(interval=5, timeout=120)
        provider.nova.servers.create.assert_called_once_with(
            "rally-dep-1-0", "fake_image_uuid", "22", userdata="fake_userdata",
            nics="fake_nics", key_name="fake_key_name", config_drive=False,
            security_groups=[provider.sg.name])

    @mock.patch(MOD_NAME + ".osclients")
    def test_get_image_found_by_checksum(self, mock_osclients):
        self._init_mock_clients()
        mock_osclients.Clients = mock.MagicMock(return_value=self.clients)
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        image_uuid = prov.get_image_uuid()
        self.assertEqual(image_uuid, "fake-uuid")

    @mock.patch(MOD_NAME + ".osclients")
    def test_get_image_download(self, mock_osclients):
        self._init_mock_clients()
        self.glance_client.images.list = mock.Mock(return_value=[])
        mock_osclients.Clients = mock.MagicMock(return_value=self.clients)
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        image_uuid = prov.get_image_uuid()
        self.assertEqual(image_uuid, "fake-uuid")

    @mock.patch(MOD_NAME + ".osclients")
    def test_get_image_no_glance_exception(
            self, mock_osclients):
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        prov.glance = None
        self.assertRaises(exceptions.InvalidConfigException,
                          prov.get_image_uuid)

    @mock.patch(MOD_NAME + ".osclients")
    def test_get_image_from_uuid_no_glance(self, mock_osclients):
        conf = self._get_valid_config()
        conf["image"]["uuid"] = "EC7A1DB7-C5BD-49A2-8066-613809CB22F5"
        prov = OSProvider(mock.MagicMock(), conf)
        prov.glance = True
        self.assertEqual(conf["image"]["uuid"], prov.get_image_uuid())

    @mock.patch(MOD_NAME + ".osclients")
    def test_destroy_servers(self, mock_osclients):
        prov = OSProvider(mock.MagicMock(), self._get_valid_config())
        prov.resources.get_all.side_effect = [
            [fakes.FakeResource(
                id=1,
                items={"info": {"id": "35FC0503-FED6-419F-B6EE-B704198CE642"}}
            )],
            [fakes.FakeResource(
                id=2,
                items={"info": {"id": "keypair_name"}}
            )],
        ]
        prov.destroy_servers()
        prov.resources.get_all.assert_has_calls([
            mock.call(type="server"),
            mock.call(type="keypair"),
        ])
        prov.nova.servers.delete.assert_called_once_with(
            "35FC0503-FED6-419F-B6EE-B704198CE642")
        prov.nova.keypairs.delete.assert_called_once_with("keypair_name")
        prov.resources.delete.assert_has_calls([
            mock.call(1),
            mock.call(2),
        ])
