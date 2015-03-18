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

    @mock.patch(BASIC + "_generate_random_name")
    def test_get_entities(self, mock_gen_name):
        scenario = basic.KeystoneBasic()
        mock_gen_name.return_value = "teeeeest"
        fake_tenant = mock.MagicMock()
        fake_user = mock.MagicMock()
        fake_role = mock.MagicMock()
        fake_service = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._user_create = mock.MagicMock(return_value=fake_user)
        scenario._role_create = mock.MagicMock(return_value=fake_role)
        scenario._get_tenant = mock.MagicMock(return_value=fake_tenant)
        scenario._get_user = mock.MagicMock(return_value=fake_user)
        scenario._get_role = mock.MagicMock(return_value=fake_role)
        scenario._get_service_by_name = mock.MagicMock(
            return_value=fake_service)
        scenario._get_service = mock.MagicMock(return_value=fake_service)
        scenario.get_entities()
        scenario._tenant_create.assert_called_once_with(name_length=5)
        scenario._user_create.assert_called_once_with(name_length=10)
        scenario._role_create.assert_called_once_with()
        scenario._get_tenant.assert_called_once_with(fake_tenant.id)
        scenario._get_user.assert_called_once_with(fake_user.id)
        scenario._get_role.assert_called_once_with(fake_role.id)
        scenario._get_service_by_name("keystone")
        scenario._get_service.assert_called_once_with(fake_service.id)

    def test_create_and_delete_service(self):
        scenario = basic.KeystoneBasic()
        name = "Rally_test_service"
        service_type = "rally_test_type"
        description = "test_description"
        fake_service = mock.MagicMock()
        scenario._service_create = mock.MagicMock(return_value=fake_service)
        scenario._delete_service = mock.MagicMock()
        scenario.create_and_delete_service(name=name,
                                           service_type=service_type,
                                           description=description)
        scenario._service_create.assert_called_once_with(name,
                                                         service_type,
                                                         description)
        scenario._delete_service.assert_called_once_with(fake_service.id)

    def test_create_update_and_delete_tenant(self):
        scenario = basic.KeystoneBasic()
        fake_tenant = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._update_tenant = mock.MagicMock()
        scenario._resource_delete = mock.MagicMock()
        scenario.create_update_and_delete_tenant()
        scenario._update_tenant.assert_called_once_with(fake_tenant)
        scenario._resource_delete.assert_called_once_with(fake_tenant)

    def test_create_user_update_password(self):
        scenario = basic.KeystoneBasic()
        fake_password = "pswd"
        fake_user = mock.MagicMock()
        scenario._user_create = mock.MagicMock(return_value=fake_user)
        scenario._generate_random_name = mock.MagicMock(
            return_value=fake_password)
        scenario._update_user_password = mock.MagicMock()

        scenario.create_user_update_password(name_length=9, password_length=9)
        scenario._generate_random_name.assert_called_once_with(length=9)
        scenario._user_create.assert_called_once_with(name_length=9)
        scenario._update_user_password.assert_called_once_with(fake_user.id,
                                                               fake_password)

    def test_create_and_list_services(self):
        scenario = basic.KeystoneBasic()
        name = "Rally_test_service"
        service_type = "rally_test_type"
        description = "test_description"
        fake_service = mock.MagicMock()
        scenario._service_create = mock.MagicMock(return_value=fake_service)
        scenario._list_services = mock.MagicMock()
        scenario.create_and_list_services(name=name,
                                          service_type=service_type,
                                          description=description)
        scenario._service_create.assert_called_once_with(name,
                                                         service_type,
                                                         description)
        scenario._list_services.assert_called_once_with()
