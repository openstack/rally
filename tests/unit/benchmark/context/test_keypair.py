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

from rally.benchmark.context import keypair
from tests.unit import test

CTX = "rally.benchmark.context"


class KeyPairContextTestCase(test.TestCase):

    def setUp(self):
        super(KeyPairContextTestCase, self).setUp()
        self.users = 2
        task = mock.MagicMock()
        self.ctx_with_keys = {
            "users": [
                {"keypair": "key", "endpoint": "endpoint"},
            ] * self.users,
            "task": task
        }
        self.ctx_without_keys = {
            "users": [{'endpoint': 'endpoint'}] * self.users,
            "task": task
        }

    @mock.patch("%s.keypair.Keypair._generate_keypair" % CTX)
    def test_keypair_setup(self, mock_generate):
        mock_generate.return_value = "key"
        keypair_ctx = keypair.Keypair(self.ctx_without_keys)
        keypair_ctx.setup()
        self.assertEqual(self.ctx_without_keys, self.ctx_with_keys)

    @mock.patch("%s.keypair.resource_manager.cleanup" % CTX)
    def test_keypair_cleanup(self, mock_cleanup):
        keypair_ctx = keypair.Keypair(self.ctx_with_keys)
        keypair_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["nova.keypairs"],
                                             users=self.ctx_with_keys["users"])

    @mock.patch("rally.osclients.Clients")
    def test_keypair_generate(self, mock_osclients):
        keypair_ctx = keypair.Keypair(self.ctx_without_keys)
        keypair_ctx._generate_keypair("endpoint")

        mock_osclients.assert_has_calls([
            mock.call().nova().keypairs.delete("rally_ssh_key"),
            mock.call().nova().keypairs.create("rally_ssh_key"),
        ])
