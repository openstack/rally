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
from tests import fakes
from tests import test


class UserGeneratorTestCase(test.TestCase):

    @mock.patch("rally.benchmark.context.users.utils.create_openstack_clients")
    def test_with_statement(self, mock_create_os_clients):
        admin_endpoint = "admin"
        with users.UserGenerator(admin_endpoint):
            pass

    @mock.patch("rally.benchmark.context.users.utils.create_openstack_clients")
    def test_create_and_delete_users_and_tenants(self, mock_create_os_clients):
        fc = fakes.FakeClients()
        # TODO(msdubov): This indicates that osclients.Clients should be
        #                perhaps refactored to support dictionary-like access.
        mock_create_os_clients.return_value = {
            "keystone": fc.get_keystone_client()
        }
        admin_user = {"username": "admin", "password": "pwd",
                      "tenant_name": "admin", "auth_url": "url"}
        created_users = []
        created_tenants = []
        with users.UserGenerator(admin_user) as generator:
            tenants = 10
            users_per_tenant = 5
            endpoints = generator.create_users_and_tenants(tenants,
                                                           users_per_tenant)
            self.assertEqual(len(endpoints), tenants * users_per_tenant)
            created_users = generator.users
            created_tenants = generator.tenants
        self.assertTrue(all(u.status == "DELETED" for u in created_users))
        self.assertTrue(all(t.status == "DELETED" for t in created_tenants))
