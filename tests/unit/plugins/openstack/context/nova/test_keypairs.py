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
        self.keypair_name = keypairs.Keypair.KEYPAIR_NAME + "_foo_task_id"

        task = {"uuid": "foo_task_id"}
        self.ctx_with_keys = {
            "users": [
                {
                    "keypair": {
                        "id": "key_id",
                        "key": "key",
                        "name": self.keypair_name
                    },
                    "endpoint": "endpoint"
                },
            ] * self.users,
            "task": task
        }
        self.ctx_without_keys = {
            "users": [{"endpoint": "endpoint"}] * self.users,
            "task": task
        }

    @mock.patch("%s.keypairs.Keypair._generate_keypair" % CTX)
    def test_keypair_setup(self, mock_keypair__generate_keypair):
        mock_keypair__generate_keypair.side_effect = [
            {"id": "key_id", "key": "key", "name": self.keypair_name},
            {"id": "key_id", "key": "key", "name": self.keypair_name},
        ]

        keypair_ctx = keypairs.Keypair(self.ctx_without_keys)
        keypair_ctx.setup()
        self.assertEqual(self.ctx_with_keys, keypair_ctx.context)

        self.assertEqual(
            [mock.call("endpoint")] * 2,
            mock_keypair__generate_keypair.mock_calls)

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
        key = keypair_ctx._generate_keypair("endpoint")

        self.assertEqual({
            "id": "key_id",
            "name": "rally_ssh_key_foo_task_id",
            "private": "private_key",
            "public": "public_key"
        }, key)

        mock_clients.assert_has_calls([
            mock.call().nova().keypairs.delete("rally_ssh_key_foo_task_id"),
            mock.call().nova().keypairs.create("rally_ssh_key_foo_task_id"),
        ])
