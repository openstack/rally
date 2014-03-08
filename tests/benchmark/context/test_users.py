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
from tests import test


class UserGeneratorTestCase(test.TestCase):

    @mock.patch("rally.benchmark.context.users.osclients")
    def test_with_statement(self, mock_create_osclients):
        context = {
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock()
        }
        with users.UserGenerator(context) as generator:
            generator.setup()

    @mock.patch("rally.benchmark.context.users.osclients.Clients.keystone")
    @mock.patch("rally.benchmark.context.users.osclients.Clients")
    def test_create_and_delete_users_and_tenants(self, mock_osclients,
                                                 mock_keystone):
        tenants = 10
        users_per_tenant = 5
        context = {
            "config": {
                "users": {
                    "tenants": tenants,
                    "users_per_tenant": users_per_tenant
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock()
        }

        with users.UserGenerator(context) as generator:
            generator.setup()
            self.assertEqual(len(generator.context["users"]),
                             tenants * users_per_tenant)
            self.assertEqual(len(generator.context["tenants"]),
                             tenants)
            mock_osclients.reset_mock()

        expected_calls = map(lambda u:
                             mock.call().keystone().users.delete(u["id"]),
                             generator.context["users"])
        expected_calls.extend(map(lambda t:
                                  mock.call().keystone().tenants.delete(
                                  t["id"]),
                                  generator.context["tenants"]))

        mock_osclients.assert_has_calls(expected_calls, any_order=True)
