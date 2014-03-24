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

import itertools
import mock
import uuid

from rally.benchmark.context import users
from rally.benchmark import utils
from tests import fakes
from tests import test


run_concurrent = lambda dummy, f, args: itertools.imap(f, args)


@mock.patch.object(utils, "run_concurrent", run_concurrent)
class UserGeneratorTestCase(test.TestCase):

    tenants_num = 10
    users_per_tenant = 5
    users_num = tenants_num * users_per_tenant
    concurrent = 10

    @property
    def context(self):
        return {
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                    "concurrent": self.concurrent,
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock()
        }

    @mock.patch("rally.benchmark.context.users.osclients")
    def test_create_tenant_users(self, mock_osclients):
        users_num = 5
        args = (mock.MagicMock(), users_num, str(uuid.uuid4()), 1)

        result = users.UserGenerator._create_tenant_users(args)

        self.assertEqual(len(result), 2)
        tenant, users_ = result
        self.assertIn("id", tenant)
        self.assertIn("name", tenant)
        self.assertEqual(len(users_), users_num)
        for user in users_:
            self.assertIn("id", user)
            self.assertIn("endpoint", user)

    @mock.patch("rally.benchmark.context.users.osclients")
    def test_setup_and_cleanup(self, mock_osclients):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        with users.UserGenerator(self.context) as generator:

            # Setup (must be called obviously)
            self.assertEqual(len(fc.keystone().users.list()), 0)
            self.assertEqual(len(fc.keystone().tenants.list()), 0)

            generator.setup()

            self.assertEqual(len(generator.context["users"]),
                             self.users_num)
            self.assertEqual(len(fc.keystone().users.list()),
                             self.users_num)
            self.assertEqual(len(generator.context["tenants"]),
                             self.tenants_num)
            self.assertEqual(len(fc.keystone().tenants.list()),
                             self.tenants_num)

        # Cleanup (called by content manager)
        self.assertEqual(len(fc.keystone().users.list()), 0)
        self.assertEqual(len(fc.keystone().tenants.list()), 0)
