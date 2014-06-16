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
import uuid

import mock

from rally.benchmark.context import users
from rally.benchmark import utils
from tests import fakes
from tests import test


run_concurrent = (lambda dummy, cls, f, args: list(
    itertools.imap(getattr(cls, f), args)))


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
    def test_delete_tenants(self, mock_osclients):
        tenant1 = mock.MagicMock()
        tenant2 = mock.MagicMock()
        args = (mock.MagicMock(), [tenant1, tenant2])
        users.UserGenerator._delete_tenants(args)
        mock_osclients.Clients().keystone().tenants.delete.assert_has_calls([
            mock.call(tenant1["id"]),
            mock.call(tenant2["id"])])

    @mock.patch("rally.benchmark.context.users.osclients")
    def test_delete_users(self, mock_osclients):
        user1 = mock.MagicMock()
        user2 = mock.MagicMock()
        args = (mock.MagicMock(), [user1, user2])
        users.UserGenerator._delete_users(args)
        mock_osclients.Clients().keystone().users.delete.assert_has_calls([
            mock.call(user1["id"]),
            mock.call(user2["id"])])

    @mock.patch("rally.benchmark.context.users.osclients")
    def test_setup_and_cleanup(self, mock_osclients):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        with users.UserGenerator(self.context) as ctx:
            self.assertEqual(len(fc.keystone().users.list()), 0)
            self.assertEqual(len(fc.keystone().tenants.list()), 0)

            ctx.setup()

            self.assertEqual(len(ctx.context["users"]),
                             self.users_num)
            self.assertEqual(len(fc.keystone().users.list()),
                             self.users_num)
            self.assertEqual(len(ctx.context["tenants"]),
                             self.tenants_num)
            self.assertEqual(len(fc.keystone().tenants.list()),
                             self.tenants_num)

        # Cleanup (called by content manager)
        self.assertEqual(len(fc.keystone().users.list()), 0)
        self.assertEqual(len(fc.keystone().tenants.list()), 0)

    @mock.patch("rally.benchmark.context.users.osclients")
    def test_users_and_tenants_in_context(self, mock_osclients):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        task = {"uuid": "abcdef"}

        config = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 2,
                    "concurrent": 1
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": task
        }

        with users.UserGenerator(config) as ctx:
            ctx.setup()

            tenants = []
            for i, t in enumerate(fc.keystone().tenants.list()):
                pattern = users.UserGenerator.PATTERN_TENANT
                tenants.append({
                    "id": t.id,
                    "name": pattern % {"task_id": task["uuid"], "iter": i}
                })

            self.assertEqual(ctx.context["tenants"], tenants)

            for user in ctx.context["users"]:
                self.assertEqual(set(["id", "endpoint", "tenant_id"]),
                                 set(user.keys()))

            tenants_ids = []
            for t in tenants:
                tenants_ids.extend([t["id"], t["id"]])

            users_ids = [user.id for user in fc.keystone().users.list()]

            for (user, tenant_id, user_id) in zip(ctx.context["users"],
                                                  tenants_ids, users_ids):
                self.assertEqual(user["id"], user_id)
                self.assertEqual(user["tenant_id"], tenant_id)
