# Copyright 2015: Hewlett-Packard Development Company, L.P.
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

from rally import exceptions
from rally.plugins.openstack.scenarios.nova import keypairs
from tests.unit import fakes
from tests.unit import test


class NovaKeypairTestCase(test.ScenarioTestCase):

    def test_create_and_list_keypairs(self):

        fake_nova_client = fakes.FakeNovaClient()
        fake_nova_client.keypairs.create("keypair")
        fake_keypair = list(fake_nova_client.keypairs.cache.values())[0]

        scenario = keypairs.CreateAndListKeypairs(self.context)
        scenario._create_keypair = mock.MagicMock()
        scenario._list_keypairs = mock.MagicMock()

        scenario._list_keypairs.return_value = [fake_keypair] * 3
        # Positive case:
        scenario._create_keypair.return_value = fake_keypair.id
        scenario.run(fakearg="fakearg")

        scenario._create_keypair.assert_called_once_with(fakearg="fakearg")
        scenario._list_keypairs.assert_called_once_with()

        # Negative case1: keypair isn't created
        scenario._create_keypair.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, fakearg="fakearg")
        scenario._create_keypair.assert_called_with(fakearg="fakearg")

        # Negative case2: new keypair not in the list of keypairs
        scenario._create_keypair.return_value = "fake_keypair"
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, fakearg="fakearg")
        scenario._create_keypair.assert_called_with(fakearg="fakearg")
        scenario._list_keypairs.assert_called_with()

    def test_create_and_delete_keypair(self):
        scenario = keypairs.CreateAndDeleteKeypair(self.context)
        scenario.generate_random_name = mock.MagicMock(return_value="name")
        scenario._create_keypair = mock.MagicMock(return_value="foo_keypair")
        scenario._delete_keypair = mock.MagicMock()

        scenario.run(fakearg="fakearg")

        scenario._create_keypair.assert_called_once_with(fakearg="fakearg")
        scenario._delete_keypair.assert_called_once_with("foo_keypair")

    def test_boot_and_delete_server_with_keypair(self):
        scenario = keypairs.BootAndDeleteServerWithKeypair(self.context)
        scenario.generate_random_name = mock.MagicMock(return_value="name")
        scenario._create_keypair = mock.MagicMock(return_value="foo_keypair")
        scenario._boot_server = mock.MagicMock(return_value="foo_server")
        scenario._delete_server = mock.MagicMock()
        scenario._delete_keypair = mock.MagicMock()

        fake_server_args = {
            "foo": 1,
            "bar": 2,
        }

        scenario.run("img", 1, boot_server_kwargs=fake_server_args,
                     fake_arg1="foo", fake_arg2="bar")

        scenario._create_keypair.assert_called_once_with(
            fake_arg1="foo", fake_arg2="bar")

        scenario._boot_server.assert_called_once_with(
            "img", 1, foo=1, bar=2, key_name="foo_keypair")

        scenario._delete_server.assert_called_once_with("foo_server")

        scenario._delete_keypair.assert_called_once_with("foo_keypair")
