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

import mock

from rally.benchmark.context import users
from rally import exceptions
from tests.unit import test


class UserGeneratorTestCase(test.TestCase):

    tenants_num = 10
    users_per_tenant = 5
    users_num = tenants_num * users_per_tenant
    threads = 10

    @property
    def context(self):
        return {
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                    "resource_management_workers": self.threads,
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": {"uuid": "task_id"}
        }

    def setUp(self):
        super(UserGeneratorTestCase, self).setUp()
        self.osclients_patcher = mock.patch(
            "rally.benchmark.context.users.osclients")
        self.osclients = self.osclients_patcher.start()

    def tearDown(self):
        self.osclients_patcher.stop()
        super(UserGeneratorTestCase, self).tearDown()

    @mock.patch("rally.benchmark.utils.check_service_status",
                return_value=True)
    def test__remove_associated_networks(self, mock_check_service_status):
        def fake_get_network(req_network):
            for network in networks:
                if network.project_id == req_network.project_id:
                    return network

        tenant1 = {'id': 1}
        tenant2 = {'id': 4}
        networks = [mock.MagicMock(project_id=1),
                    mock.MagicMock(project_id=2)]
        nova_admin = mock.MagicMock()
        clients = mock.MagicMock()
        self.osclients.Clients.return_value = clients
        clients.services.return_value = {'compute': 'nova'}
        clients.nova.return_value = nova_admin
        nova_admin.networks.list.return_value = networks
        nova_admin.networks.get = fake_get_network
        user_generator = users.UserGenerator(self.context)
        user_generator.context["tenants"] = [tenant1, tenant2]
        user_generator._remove_associated_networks()
        mock_check_service_status.assert_called_once_with(mock.ANY,
                                                          'nova-network')
        nova_admin.networks.disassociate.assert_called_once_with(networks[0])

    @mock.patch("rally.benchmark.utils.check_service_status",
                return_value=True)
    def test__remove_associated_networks_failure(self,
                                                 mock_check_service_status):
        def fake_get_network(req_network):
            for network in networks:
                if network.project_id == req_network.project_id:
                    return network

        tenant1 = {'id': 1}
        tenant2 = {'id': 4}
        networks = [mock.MagicMock(project_id=1),
                    mock.MagicMock(project_id=2)]
        nova_admin = mock.MagicMock()
        clients = mock.MagicMock()
        self.osclients.Clients.return_value = clients
        clients.services.return_value = {'compute': 'nova'}
        clients.nova.return_value = nova_admin
        nova_admin.networks.list.return_value = networks
        nova_admin.networks.get = fake_get_network
        nova_admin.networks.disassociate.side_effect = Exception()
        user_generator = users.UserGenerator(self.context)
        user_generator.context["tenants"] = [tenant1, tenant2]
        user_generator._remove_associated_networks()
        mock_check_service_status.assert_called_once_with(mock.ANY,
                                                          'nova-network')
        nova_admin.networks.disassociate.assert_called_once_with(networks[0])

    @mock.patch("rally.benchmark.context.users.broker.time.sleep")
    @mock.patch("rally.benchmark.context.users.keystone")
    def test__create_tenants(self, mock_keystone, mock_sleep):
        user_generator = users.UserGenerator(self.context)
        user_generator.config["tenants"] = 2
        tenants = user_generator._create_tenants()
        self.assertEqual(2, len(tenants))
        for tenant in tenants:
            self.assertIn("id", tenant)
            self.assertIn("name", tenant)

    @mock.patch("rally.benchmark.context.users.broker.time.sleep")
    @mock.patch("rally.benchmark.context.users.keystone")
    def test__create_users(self, mock_keystone, mock_sleep):
        user_generator = users.UserGenerator(self.context)
        tenant1 = mock.MagicMock()
        tenant2 = mock.MagicMock()
        user_generator.context["tenants"] = [tenant1, tenant2]
        user_generator.config["users_per_tenant"] = 2
        users_ = user_generator._create_users()
        self.assertEqual(4, len(users_))
        for user in users_:
            self.assertIn("id", user)
            self.assertIn("endpoint", user)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test__delete_tenants(self, mock_keystone):
        user_generator = users.UserGenerator(self.context)
        tenant1 = mock.MagicMock()
        tenant2 = mock.MagicMock()
        user_generator.context["tenants"] = [tenant1, tenant2]
        user_generator._delete_tenants()
        self.assertEqual(len(user_generator.context["tenants"]), 0)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test__delete_tenants_failure(self, mock_keystone):
        wrapped_keystone = mock_keystone.wrap.return_value
        wrapped_keystone.delete_project.side_effect = Exception()
        user_generator = users.UserGenerator(self.context)
        tenant1 = mock.MagicMock()
        tenant2 = mock.MagicMock()
        user_generator.context["tenants"] = [tenant1, tenant2]
        user_generator._delete_tenants()
        self.assertEqual(len(user_generator.context["tenants"]), 0)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test__delete_users(self, mock_keystone):
        user_generator = users.UserGenerator(self.context)
        user1 = mock.MagicMock()
        user2 = mock.MagicMock()
        user_generator.context["users"] = [user1, user2]
        user_generator._delete_users()
        self.assertEqual(len(user_generator.context["users"]), 0)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test__delete_users_failure(self, mock_keystone):
        wrapped_keystone = mock_keystone.wrap.return_value
        wrapped_keystone.delete_user.side_effect = Exception()
        user_generator = users.UserGenerator(self.context)
        user1 = mock.MagicMock()
        user2 = mock.MagicMock()
        user_generator.context["users"] = [user1, user2]
        user_generator._delete_users()
        self.assertEqual(len(user_generator.context["users"]), 0)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test_setup_and_cleanup(self, mock_keystone):
        wrapped_keystone = mock.MagicMock()
        mock_keystone.wrap.return_value = wrapped_keystone
        with users.UserGenerator(self.context) as ctx:

            ctx.setup()

            self.assertEqual(len(ctx.context["users"]),
                             self.users_num)
            self.assertEqual(len(ctx.context["tenants"]),
                             self.tenants_num)

        # Cleanup (called by content manager)
        self.assertEqual(len(ctx.context["users"]), 0)
        self.assertEqual(len(ctx.context["tenants"]), 0)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test_setup_and_cleanup_failure(self, mock_keystone):
        wrapped_keystone = mock_keystone.wrap.return_value
        wrapped_keystone.create_user.side_effect = Exception()
        with users.UserGenerator(self.context) as ctx:
            self.assertRaises(exceptions.ContextSetupFailure, ctx.setup)

        # Ensure that tenants get deleted anyway
        self.assertEqual(len(ctx.context["tenants"]), 0)

    @mock.patch("rally.benchmark.context.users.keystone")
    def test_users_and_tenants_in_context(self, mock_keystone):
        wrapped_keystone = mock.MagicMock()
        mock_keystone.wrap.return_value = wrapped_keystone
        task = {"uuid": "abcdef"}

        config = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 2,
                    "resource_management_workers": 1
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": task
        }

        user_list = [mock.MagicMock(id='id_%d' % i)
                     for i in range(self.users_num)]
        wrapped_keystone.create_user.side_effect = user_list

        with users.UserGenerator(config) as ctx:
            ctx.setup()

            create_tenant_calls = []
            for i, t in enumerate(ctx.context["tenants"]):
                pattern = users.UserGenerator.PATTERN_TENANT
                create_tenant_calls.append(
                    mock.call(pattern % {"task_id": task["uuid"], "iter": i},
                              ctx.config["project_domain"]))

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
