# Copyright 2014: The Rally team
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

import mock

from rally.cli.commands import show
from rally.common import objects
from tests.unit import fakes
from tests.unit import test


class ShowCommandsTestCase(test.TestCase):

    def setUp(self):
        super(ShowCommandsTestCase, self).setUp()
        self.show = show.ShowCommands()
        self.admin_credential = {
            "username": "admin",
            "password": "admin",
            "tenant_name": "admin",
            "auth_url": "http://fake.auth.url"
        }
        self.user_credentials = {
            "username": "user1",
            "password": "user2",
            "tenant_name": "user3",
            "auth_url": "http://fake.auth.url"
        }

        self.fake_deployment_id = "7f6e88e0-897e-45c0-947c-595ce2437bee"
        self.fake_clients = fakes.FakeClients()
        self.fake_glance_client = fakes.FakeGlanceClient()
        self.fake_nova_client = fakes.FakeNovaClient()

    @mock.patch("rally.cli.commands.show.print", create=True)
    @mock.patch("rally.cli.commands.show.cliutils.print_list")
    @mock.patch("rally.cli.commands.show.cliutils.pretty_float_formatter")
    @mock.patch("rally.cli.commands.show.utils.Struct")
    @mock.patch("rally.osclients.Glance.create_client")
    @mock.patch("rally.api.Deployment.get")
    def test_images(self, mock_deployment_get, mock_glance_create_client,
                    mock_struct, mock_pretty_float_formatter,
                    mock_print_list, mock_print):
        self.fake_glance_client.images.create("image", None, None, None)
        fake_image = list(self.fake_glance_client.images.cache.values())[0]
        fake_image.size = 1
        mock_glance_create_client.return_value = self.fake_glance_client
        mock_deployment_get.return_value = objects.Deployment({
            "admin": self.admin_credential,
            "users": [self.user_credentials, self.user_credentials]
        })

        self.show.images(self.fake_deployment_id)
        mock_deployment_get.assert_called_once_with(self.fake_deployment_id)

        mock_glance_create_client.assert_has_calls([mock.call()] * 3)
        self.assertEqual(3, mock_glance_create_client.call_count)

        headers = ["UUID", "Name", "Size (B)"]
        fake_data = dict(
            zip(headers, [fake_image.id, fake_image.name, fake_image.size])
        )
        mock_struct.assert_has_calls([mock.call(**fake_data)] * 3)

        fake_formatters = {"Size (B)": mock_pretty_float_formatter()}
        mixed_case_fields = ["UUID", "Name"]
        mock_print_list.assert_has_calls([mock.call(
            [mock_struct()],
            fields=headers,
            formatters=fake_formatters,
            mixed_case_fields=mixed_case_fields
        )] * 3)
        self.assertEqual(3, mock_print.call_count)

    @mock.patch("rally.cli.commands.show.cliutils.print_list")
    @mock.patch("rally.cli.commands.show.cliutils.pretty_float_formatter")
    @mock.patch("rally.cli.commands.show.utils.Struct")
    @mock.patch("rally.osclients.Nova.create_client")
    @mock.patch("rally.api.Deployment.get")
    def test_flavors(self, mock_deployment_get, mock_nova_create_client,
                     mock_struct, mock_pretty_float_formatter,
                     mock_print_list):
        self.fake_nova_client.flavors.create()
        fake_flavor = list(self.fake_nova_client.flavors.cache.values())[0]
        fake_flavor.id, fake_flavor.name, fake_flavor.vcpus = 1, "m1.fake", 1
        fake_flavor.ram, fake_flavor.swap, fake_flavor.disk = 1024, 128, 10
        mock_nova_create_client.return_value = self.fake_nova_client
        mock_deployment_get.return_value = objects.Deployment({
            "admin": self.admin_credential,
            "users": [self.user_credentials, self.user_credentials]
        })
        self.show.flavors(self.fake_deployment_id)
        mock_deployment_get.assert_called_once_with(self.fake_deployment_id)
        mock_nova_create_client.assert_has_calls([mock.call()] * 3)
        self.assertEqual(3, mock_nova_create_client.call_count)

        headers = ["ID", "Name", "vCPUs", "RAM (MB)", "Swap (MB)", "Disk (GB)"]
        fake_data = dict(
            zip(headers,
                [fake_flavor.id, fake_flavor.name, fake_flavor.vcpus,
                 fake_flavor.ram, fake_flavor.swap, fake_flavor.disk])
        )

        mock_struct.assert_has_calls([mock.call(**fake_data)] * 3)

        fake_formatters = {"RAM (MB)": mock_pretty_float_formatter(),
                           "Swap (MB)": mock_pretty_float_formatter(),
                           "Disk (GB)": mock_pretty_float_formatter()}
        mixed_case_fields = ["ID", "Name", "vCPUs"]
        mock_print_list.assert_has_calls([mock.call(
            [mock_struct()],
            fields=headers,
            formatters=fake_formatters,
            mixed_case_fields=mixed_case_fields
        )] * 3)

    @mock.patch("rally.cli.commands.show.cliutils.print_list")
    @mock.patch("rally.cli.commands.show.utils.Struct")
    @mock.patch("rally.osclients.Nova.create_client")
    @mock.patch("rally.api.Deployment.get")
    def test_networks(self, mock_deployment_get, mock_nova_create_client,
                      mock_struct, mock_print_list):
        self.fake_nova_client.networks.create(1234)
        fake_network = list(self.fake_nova_client.networks.cache.values())[0]
        fake_network.label = "fakenet"
        fake_network.cidr = "10.0.0.0/24"
        mock_nova_create_client.return_value = self.fake_nova_client
        mock_deployment_get.return_value = objects.Deployment({
            "admin": self.admin_credential,
            "users": [self.user_credentials, self.user_credentials]
        })
        self.show.networks(self.fake_deployment_id)
        mock_deployment_get.assert_called_once_with(self.fake_deployment_id)
        mock_nova_create_client.assert_has_calls([mock.call()] * 3)
        self.assertEqual(3, mock_nova_create_client.call_count)

        headers = ["ID", "Label", "CIDR"]
        fake_data = dict(
            zip(headers,
                [fake_network.id, fake_network.label, fake_network.cidr])
        )
        mock_struct.assert_has_calls([mock.call(**fake_data)] * 3)

        mixed_case_fields = ["ID", "Label", "CIDR"]
        mock_print_list.assert_has_calls([mock.call(
            [mock_struct()],
            fields=headers,
            mixed_case_fields=mixed_case_fields
        )] * 3)

    @mock.patch("rally.cli.commands.show.cliutils.print_list")
    @mock.patch("rally.cli.commands.show.utils.Struct")
    @mock.patch("rally.osclients.Nova.create_client")
    @mock.patch("rally.api.Deployment.get")
    def test_secgroups(self, mock_deployment_get, mock_nova_create_client,
                       mock_struct, mock_print_list):
        self.fake_nova_client.security_groups.create("othersg")
        fake_secgroup = list(
            self.fake_nova_client.security_groups.cache.values())[0]
        fake_secgroup.id = 0
        fake_secgroup2 = list(
            self.fake_nova_client.security_groups.cache.values())[1]
        fake_secgroup2.id = 1
        mock_nova_create_client.return_value = self.fake_nova_client
        mock_deployment_get.return_value = objects.Deployment({
            "admin": self.admin_credential,
            "users": [self.user_credentials]
        })
        self.show.secgroups(self.fake_deployment_id)
        mock_deployment_get.assert_called_once_with(self.fake_deployment_id)
        mock_nova_create_client.assert_has_calls([mock.call()] * 2)
        self.assertEqual(2, mock_nova_create_client.call_count)

        headers = ["ID", "Name", "Description"]
        fake_data = [fake_secgroup.id, fake_secgroup.name, ""]
        fake_data2 = [fake_secgroup2.id, fake_secgroup2.name, ""]
        calls = [mock.call(**dict(zip(headers, fake_data2))),
                 mock.call(**dict(zip(headers, fake_data)))]
        mock_struct.assert_has_calls(calls * 2, any_order=True)

        mixed_case_fields = ["ID", "Name", "Description"]
        mock_print_list.assert_has_calls([mock.call(
            [mock_struct(), mock_struct()],
            fields=headers,
            mixed_case_fields=mixed_case_fields
        )] * 2)

    @mock.patch("rally.cli.commands.show.cliutils.print_list")
    @mock.patch("rally.cli.commands.show.utils.Struct")
    @mock.patch("rally.osclients.Nova.create_client")
    @mock.patch("rally.api.Deployment.get")
    def test_keypairs(self, mock_deployment_get, mock_nova_create_client,
                      mock_struct, mock_print_list):
        self.fake_nova_client.keypairs.create("keypair")
        fake_keypair = list(self.fake_nova_client.keypairs.cache.values())[0]
        fake_keypair.fingerprint = "84:87:58"
        mock_nova_create_client.return_value = self.fake_nova_client
        mock_deployment_get.return_value = objects.Deployment({
            "admin": self.admin_credential,
            "users": [self.user_credentials, self.user_credentials]
        })
        self.show.keypairs(self.fake_deployment_id)
        mock_deployment_get.assert_called_once_with(self.fake_deployment_id)
        mock_nova_create_client.assert_has_calls([mock.call()] * 3)
        self.assertEqual(3, mock_nova_create_client.call_count)

        headers = ["Name", "Fingerprint"]
        fake_data = dict(
            zip(headers,
                [fake_keypair.name, fake_keypair.fingerprint])
        )
        mock_struct.assert_has_calls([mock.call(**fake_data)] * 3)

        mixed_case_fields = ["Name", "Fingerprint"]
        mock_print_list.assert_has_calls([mock.call(
            [mock_struct()],
            fields=headers,
            mixed_case_fields=mixed_case_fields
        )] * 3)
