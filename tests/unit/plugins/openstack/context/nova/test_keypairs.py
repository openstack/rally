# Copyright 2014: Rackspace UK
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

from rally.plugins.openstack.context.nova import keypairs
from tests.unit import test

CTX = "rally.plugins.openstack.context.nova"


class KeyPairContextTestCase(test.TestCase):

    def setUp(self):
        super(KeyPairContextTestCase, self).setUp()
        self.users = 2

        task = {"uuid": "foo_task_id"}
        self.ctx_with_keys = {
            "users": [
                {
                    "keypair": {
                        "id": "key_id_1",
                        "key": "key_1",
                        "name": "key_name_1"
                    },
                    "credential": "credential_1"
                },
                {
                    "keypair": {
                        "id": "key_id_2",
                        "key": "key_2",
                        "name": "key_name_2"
                    },
                    "credential": "credential_2"
                },
            ],
            "task": task
        }
        self.ctx_without_keys = {
            "users": [{"credential": "credential_1"},
                      {"credential": "credential_2"}],
            "task": task
        }

    def test_keypair_setup(self):
        keypair_ctx = keypairs.Keypair(self.ctx_without_keys)
        keypair_ctx._generate_keypair = mock.Mock(side_effect=[
            {"id": "key_id_1", "key": "key_1", "name": "key_name_1"},
            {"id": "key_id_2", "key": "key_2", "name": "key_name_2"},
        ])

        keypair_ctx.setup()
        self.assertEqual(keypair_ctx.context, self.ctx_with_keys)

        keypair_ctx._generate_keypair.assert_has_calls(
            [mock.call("credential_1"), mock.call("credential_2")])

    @mock.patch("%s.keypairs.resource_manager.cleanup" % CTX)
    def test_keypair_cleanup(self, mock_cleanup):
        keypair_ctx = keypairs.Keypair(self.ctx_with_keys)
        keypair_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["nova.keypairs"],
                                             users=self.ctx_with_keys["users"])

    @mock.patch("rally.osclients.Clients")
    def test_keypair_generate(self, mock_clients):
        mock_keypairs = mock_clients.return_value.nova.return_value.keypairs
        mock_keypair = mock_keypairs.create.return_value
        mock_keypair.public_key = "public_key"
        mock_keypair.private_key = "private_key"
        mock_keypair.id = "key_id"
        keypair_ctx = keypairs.Keypair(self.ctx_without_keys)
        keypair_ctx.generate_random_name = mock.Mock()
        key = keypair_ctx._generate_keypair("credential")

        self.assertEqual({
            "id": "key_id",
            "name": keypair_ctx.generate_random_name.return_value,
            "private": "private_key",
            "public": "public_key"
        }, key)

        mock_clients.assert_has_calls([
            mock.call().nova().keypairs.delete(
                keypair_ctx.generate_random_name.return_value),
            mock.call().nova().keypairs.create(
                keypair_ctx.generate_random_name.return_value)
        ])
