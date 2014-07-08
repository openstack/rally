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

from rally.benchmark.context import users
from rally.benchmark import utils
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

    def setUp(self):
        super(UserGeneratorTestCase, self).setUp()
        self.osclients_patcher = mock.patch(
            "rally.benchmark.context.users.osclients")
        self.osclients = self.osclients_patcher.start()

        self.keystone_wrapper_patcher = mock.patch(
            "rally.benchmark.context.users.keystone")
        self.keystone_wrapper = self.keystone_wrapper_patcher.start()
        self.wrapped_keystone = self.keystone_wrapper.wrap.return_value

    def tearDown(self):
        self.keystone_wrapper_patcher.stop()
        self.osclients_patcher.stop()
        super(UserGeneratorTestCase, self).tearDown()

    def test_create_tenant_users(self):
        users_num = 5
        args = (mock.MagicMock(), users_num, 'default', 'default',
                'ad325aec-f7b4-4a62-832a-bb718e465bb7', 1)
        result = users.UserGenerator._create_tenant_users(args)

        self.assertEqual(len(result), 2)
        tenant, users_ = result
        self.assertIn("id", tenant)
        self.assertIn("name", tenant)
        self.assertEqual(len(users_), users_num)
        for user in users_:
            self.assertIn("id", user)
            self.assertIn("endpoint", user)

    def test_delete_tenants(self):
        tenant1 = mock.MagicMock()
        tenant2 = mock.MagicMock()
        args = (mock.MagicMock(), [tenant1, tenant2])
        users.UserGenerator._delete_tenants(args)
        self.keystone_wrapper.wrap.assert_called_once()
        self.wrapped_keystone.delete_project.assert_has_calls([
            mock.call(tenant1["id"]),
            mock.call(tenant2["id"])])

    def test_delete_users(self):
        user1 = mock.MagicMock()
        user2 = mock.MagicMock()
        args = (mock.MagicMock(), [user1, user2])
        users.UserGenerator._delete_users(args)
        self.wrapped_keystone.delete_user.assert_has_calls([
            mock.call(user1["id"]),
            mock.call(user2["id"])])

    def test_setup_and_cleanup(self):
        with users.UserGenerator(self.context) as ctx:
            self.assertEqual(self.wrapped_keystone.create_user.call_count, 0)
            self.assertEqual(self.wrapped_keystone.create_project.call_count,
                             0)

            ctx.setup()

            self.assertEqual(len(ctx.context["users"]),
                             self.users_num)
            self.assertEqual(self.wrapped_keystone.create_user.call_count,
                             self.users_num)
            self.assertEqual(len(ctx.context["tenants"]),
                             self.tenants_num)
            self.assertEqual(self.wrapped_keystone.create_project.call_count,
                             self.tenants_num)

            # Assert nothing is deleted yet
            self.assertEqual(self.wrapped_keystone.delete_user.call_count,
                             0)
            self.assertEqual(self.wrapped_keystone.delete_project.call_count,
                             0)

        # Cleanup (called by content manager)
        self.assertEqual(self.wrapped_keystone.delete_user.call_count,
                         self.users_num)
        self.assertEqual(self.wrapped_keystone.delete_project.call_count,
                         self.tenants_num)

    def test_users_and_tenants_in_context(self):
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

        user_list = [mock.MagicMock(id='id_%d' % i)
                     for i in range(self.users_num)]
        self.wrapped_keystone.create_user.side_effect = user_list

        with users.UserGenerator(config) as ctx:
            ctx.setup()

            create_tenant_calls = []
            for i, t in enumerate(ctx.context["tenants"]):
                pattern = users.UserGenerator.PATTERN_TENANT
                create_tenant_calls.append(
                    mock.call(pattern % {"task_id": task["uuid"], "iter": i},
                              ctx.config["project_domain"]))

            self.wrapped_keystone.create_project.assert_has_calls(
                create_tenant_calls, any_order=True)

            for user in ctx.context["users"]:
                self.assertEqual(set(["id", "endpoint", "tenant_id"]),
                                 set(user.keys()))

            tenants_ids = []
            for t in ctx.context["tenants"]:
                tenants_ids.extend([t["id"], t["id"]])

            for (user, tenant_id, orig_user) in zip(ctx.context["users"],
                                                    tenants_ids, user_list):
                self.assertEqual(user["id"], orig_user.id)
                self.assertEqual(user["tenant_id"], tenant_id)
