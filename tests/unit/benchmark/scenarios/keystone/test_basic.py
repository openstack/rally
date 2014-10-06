# Copyright 2013: Mirantis Inc.
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

from rally.benchmark.scenarios.keystone import basic
from tests.unit import test

BASE = "rally.benchmark.scenarios.keystone."
BASIC = BASE + "basic.KeystoneBasic."


class KeystoneBasicTestCase(test.TestCase):

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_user(self, mock_gen_name):
        scenario = basic.KeystoneBasic()
        mock_gen_name.return_value = "teeeest"
        scenario._user_create = mock.MagicMock()
        scenario.create_user(name_length=20, password="tttt", tenant_id="id")
        scenario._user_create.assert_called_once_with(name_length=20,
                                                      password="tttt",
                                                      tenant_id="id")

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_delete_user(self, mock_gen_name):
        create_result = mock.MagicMock()

        scenario = basic.KeystoneBasic()
        scenario._user_create = mock.MagicMock(return_value=create_result)
        scenario._resource_delete = mock.MagicMock()
        mock_gen_name.return_value = "teeeest"

        scenario.create_delete_user(name_length=30, email="abcd", enabled=True)

        scenario._user_create.assert_called_once_with(name_length=30,
                                                      email="abcd",
                                                      enabled=True)
        scenario._resource_delete.assert_called_once_with(create_result)

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_tenant(self, mock_gen_name):
        scenario = basic.KeystoneBasic()
        mock_gen_name.return_value = "teeeest"
        scenario._tenant_create = mock.MagicMock()
        scenario.create_tenant(name_length=20, enabled=True)
        scenario._tenant_create.assert_called_once_with(name_length=20,
                                                        enabled=True)

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_tenant_with_users(self, mock_gen_name):
        scenario = basic.KeystoneBasic()
        mock_gen_name.return_value = "teeeest"
        fake_tenant = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._users_create = mock.MagicMock()
        scenario.create_tenant_with_users(users_per_tenant=1, name_length=20,
                                          enabled=True)
        scenario._tenant_create.assert_called_once_with(name_length=20,
                                                        enabled=True)
        scenario._users_create.assert_called_once_with(fake_tenant,
                                                       users_per_tenant=1,
                                                       name_length=20)

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_and_list_users(self, mock_gen_name):
        scenario = basic.KeystoneBasic()
        mock_gen_name.return_value = "teeeest"
        scenario._user_create = mock.MagicMock()
        scenario._list_users = mock.MagicMock()
        scenario.create_and_list_users(name_length=20, password="tttt",
                                       tenant_id="id")
        scenario._user_create.assert_called_once_with(name_length=20,
                                                      password="tttt",
                                                      tenant_id="id")
        scenario._list_users.assert_called_once_with()

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_and_list_tenants(self, mock_gen_name):
        scenario = basic.KeystoneBasic()
        mock_gen_name.return_value = "teeeest"
        scenario._tenant_create = mock.MagicMock()
        scenario._list_tenants = mock.MagicMock()
        scenario.create_and_list_tenants(name_length=20, enabled=True)
        scenario._tenant_create.assert_called_once_with(name_length=20,
                                                        enabled=True)
        scenario._list_tenants.assert_called_with()
