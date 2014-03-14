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
from tests import test

CTX = "rally.benchmark.context"


class KeyPairContextTestCase(test.TestCase):

    def setUp(self):
        super(KeyPairContextTestCase, self).setUp()
        self.users = 2
        self.ctx_with_keys = {
            "users": [
                {"keypair": "key", "endpoint": "endpoint"},
            ] * self.users,
            "task": {}
        }
        self.ctx_without_keys = {
                "users": [{'endpoint': 'endpoint'}] * self.users,
            "task": {}
        }

    @mock.patch("%s.keypair.Keypair._generate_keypair" % CTX)
    def test_keypair_setup(self, mock_generate):
        mock_generate.return_value = "key"
        keypair_ctx = keypair.Keypair(self.ctx_without_keys)
        keypair_ctx.setup()
        self.assertEqual(self.ctx_without_keys, self.ctx_with_keys)

    @mock.patch('rally.osclients.Clients')
    @mock.patch("%s.keypair.Keypair._keypair_safe_remove" % CTX)
    def test_keypair_cleanup(self, mock_safe_remove, mock_osclients):
        keypair_ctx = keypair.Keypair(self.ctx_with_keys)
        keypair_ctx.cleanup()
        mock_clients = mock_osclients.return_value
        mock_nova = mock_clients.nova.return_value
        self.assertEqual(
            [mock.call(mock_nova)]
            * self.users,
            mock_safe_remove.mock_calls
        )

    @mock.patch("%s.keypair.Keypair._keypair_safe_remove" % CTX)
    @mock.patch('rally.osclients.Clients')
    def test_keypair_generate(self, mock_osclients, mock_safe_remove):
        keypair_ctx = keypair.Keypair(self.ctx_without_keys)
        keypair_ctx._generate_keypair('endpoint')
        mock_clients = mock_osclients.return_value
        mock_nova = mock_clients.nova.return_value
        self.assertIn(
            mock.call().nova().keypairs.create('rally_ssh_key'),
            mock_osclients.mock_calls
        )
        mock_safe_remove.assert_called_once_with(mock_nova)

    def test_keypair_safe_remove(self):
        mock_nova = mock.MagicMock()
        keypair_ctx = keypair.Keypair(self.ctx_without_keys)
        keypair_ctx._keypair_safe_remove(mock_nova)
        self.assertEqual(
            [mock.call.delete('rally_ssh_key')],
            mock_nova.keypairs.mock_calls)
