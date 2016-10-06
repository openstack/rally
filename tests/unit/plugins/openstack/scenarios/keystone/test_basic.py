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

from rally.plugins.openstack.scenarios.keystone import basic
from tests.unit import test


class KeystoneBasicTestCase(test.ScenarioTestCase):

    @staticmethod
    def _get_context():
        context = test.get_test_context()
        context.update({
            "user": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake_tenant_id",
                       "name": "fake_tenant_name"}
        })
        return context

    def test_create_user(self):
        scenario = basic.CreateUser(self.context)
        scenario._user_create = mock.MagicMock()
        scenario.run(password="tttt", tenant_id="id")
        scenario._user_create.assert_called_once_with(password="tttt",
                                                      tenant_id="id")

    def test_create_delete_user(self):
        create_result = mock.MagicMock()

        scenario = basic.CreateDeleteUser(self.context)
        scenario._user_create = mock.MagicMock(return_value=create_result)
        scenario._resource_delete = mock.MagicMock()

        scenario.run(email="abcd", enabled=True)

        scenario._user_create.assert_called_once_with(email="abcd",
                                                      enabled=True)
        scenario._resource_delete.assert_called_once_with(create_result)

    def test_create_user_set_enabled_and_delete(self):
        scenario = basic.CreateUserSetEnabledAndDelete(self.context)
        scenario._user_create = mock.Mock()
        scenario._update_user_enabled = mock.Mock()
        scenario._resource_delete = mock.Mock()

        scenario.run(enabled=True, email="abcd")
        scenario._user_create.assert_called_once_with(email="abcd",
                                                      enabled=True)
        scenario._update_user_enabled.assert_called_once_with(
            scenario._user_create.return_value, False)
        scenario._resource_delete.assert_called_once_with(
            scenario._user_create.return_value)

    def test_user_authenticate_and_validate_token(self):
        fake_token = mock.MagicMock()
        context = self._get_context()
        scenario = basic.AuthenticateUserAndValidateToken(context)

        fake_user = context["user"]["credential"].username
        fake_paswd = context["user"]["credential"].password
        fake_tenant_id = context["tenant"]["id"]
        fake_tenant_name = context["tenant"]["name"]

        scenario._authenticate_token = mock.MagicMock(return_value=fake_token)
        scenario._token_validate = mock.MagicMock()
        scenario.run()
        scenario._authenticate_token.assert_called_once_with(
            fake_user, fake_paswd, fake_tenant_id,
            fake_tenant_name, atomic_action=False)
        scenario._token_validate.assert_called_once_with(fake_token.id)

    def test_create_tenant(self):
        scenario = basic.CreateTenant(self.context)
        scenario._tenant_create = mock.MagicMock()
        scenario.run(enabled=True)
        scenario._tenant_create.assert_called_once_with(enabled=True)

    def test_create_tenant_with_users(self):
        scenario = basic.CreateTenantWithUsers(self.context)
        fake_tenant = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._users_create = mock.MagicMock()
        scenario.run(users_per_tenant=1, enabled=True)
        scenario._tenant_create.assert_called_once_with(enabled=True)
        scenario._users_create.assert_called_once_with(fake_tenant,
                                                       users_per_tenant=1)

    def test_create_and_list_users(self):
        scenario = basic.CreateAndListUsers(self.context)
        scenario._user_create = mock.MagicMock()
        scenario._list_users = mock.MagicMock()
        scenario.run(password="tttt", tenant_id="id")
        scenario._user_create.assert_called_once_with(password="tttt",
                                                      tenant_id="id")
        scenario._list_users.assert_called_once_with()

    def test_create_and_list_tenants(self):
        scenario = basic.CreateAndListTenants(self.context)
        scenario._tenant_create = mock.MagicMock()
        scenario._list_tenants = mock.MagicMock()
        scenario.run(enabled=True)
        scenario._tenant_create.assert_called_once_with(enabled=True)
        scenario._list_tenants.assert_called_with()

    def test_assign_and_remove_user_role(self):
        context = self._get_context()
        scenario = basic.AddAndRemoveUserRole(context)
        fake_tenant = context["tenant"]["id"]
        fake_user = context["user"]["id"]
        fake_role = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._user_create = mock.MagicMock(return_value=fake_user)
        scenario._role_create = mock.MagicMock(return_value=fake_role)
        scenario._role_add = mock.MagicMock()
        scenario._role_remove = mock.MagicMock()
        scenario.run()
        scenario._role_create.assert_called_once_with()
        scenario._role_add.assert_called_once_with(fake_user,
                                                   fake_role,
                                                   fake_tenant)
        scenario._role_remove.assert_called_once_with(fake_user,
                                                      fake_role,
                                                      fake_tenant)

    def test_create_and_delete_role(self):
        scenario = basic.CreateAndDeleteRole(self.context)
        fake_role = mock.MagicMock()
        scenario._role_create = mock.MagicMock(return_value=fake_role)
        scenario._resource_delete = mock.MagicMock()
        scenario.run()
        scenario._role_create.assert_called_once_with()
        scenario._resource_delete.assert_called_once_with(fake_role)

    def test_create_and_list_user_roles(self):
        context = self._get_context()
        scenario = basic.CreateAddAndListUserRoles(context)
        fake_tenant = context["tenant"]["id"]
        fake_user = context["user"]["id"]
        fake_role = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._user_create = mock.MagicMock(return_value=fake_user)
        scenario._role_create = mock.MagicMock(return_value=fake_role)
        scenario._role_add = mock.MagicMock()
        scenario._list_roles_for_user = mock.MagicMock()
        scenario.run()
        scenario._role_create.assert_called_once_with()
        scenario._role_add.assert_called_once_with(fake_user,
                                                   fake_role, fake_tenant)
        scenario._list_roles_for_user.assert_called_once_with(fake_user,
                                                              fake_tenant)

    def _test_get_entities(self, service_name="keystone"):
        scenario = basic.GetEntities(self.context)
        fake_tenant = mock.MagicMock()
        fake_user = mock.MagicMock()
        fake_role = mock.MagicMock()
        fake_service = mock.MagicMock()

        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._user_create = mock.MagicMock(return_value=fake_user)
        scenario._role_create = mock.MagicMock(return_value=fake_role)
        scenario._service_create = mock.MagicMock(return_value=fake_service)

        scenario._get_tenant = mock.MagicMock(return_value=fake_tenant)
        scenario._get_user = mock.MagicMock(return_value=fake_user)
        scenario._get_role = mock.MagicMock(return_value=fake_role)
        scenario._get_service_by_name = mock.MagicMock(
            return_value=fake_service)
        scenario._get_service = mock.MagicMock(return_value=fake_service)

        scenario.run(service_name)

        scenario._tenant_create.assert_called_once_with()
        scenario._user_create.assert_called_once_with()
        scenario._role_create.assert_called_once_with()

        scenario._get_tenant.assert_called_once_with(fake_tenant.id)
        scenario._get_user.assert_called_once_with(fake_user.id)
        scenario._get_role.assert_called_once_with(fake_role.id)

        if service_name is None:
            scenario._service_create.assert_called_once_with()
            self.assertFalse(scenario._get_service_by_name.called)
        else:
            scenario._get_service_by_name.assert_called_once_with(service_name)
            self.assertFalse(scenario._service_create.called)
        scenario._get_service.assert_called_once_with(fake_service.id)

    def test_get_entities(self):
        self._test_get_entities()

    def test_get_entities_with_service_name(self):
        self._test_get_entities(service_name="fooservice")

    def test_get_entities_create_service(self):
        self._test_get_entities(service_name=None)

    def test_create_and_delete_service(self):
        scenario = basic.CreateAndDeleteService(self.context)
        service_type = "test_service_type"
        description = "test_description"
        fake_service = mock.MagicMock()
        scenario._service_create = mock.MagicMock(return_value=fake_service)
        scenario._delete_service = mock.MagicMock()
        scenario.run(service_type=service_type, description=description)
        scenario._service_create.assert_called_once_with(service_type,
                                                         description)
        scenario._delete_service.assert_called_once_with(fake_service.id)

    def test_create_update_and_delete_tenant(self):
        scenario = basic.CreateUpdateAndDeleteTenant(self.context)
        fake_tenant = mock.MagicMock()
        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._update_tenant = mock.MagicMock()
        scenario._resource_delete = mock.MagicMock()
        scenario.run()
        scenario._update_tenant.assert_called_once_with(fake_tenant)
        scenario._resource_delete.assert_called_once_with(fake_tenant)

    def test_create_user_update_password(self):
        scenario = basic.CreateUserUpdatePassword(self.context)
        fake_password = "pswd"
        fake_user = mock.MagicMock()
        scenario._user_create = mock.MagicMock(return_value=fake_user)
        scenario.generate_random_name = mock.MagicMock(
            return_value=fake_password)
        scenario._update_user_password = mock.MagicMock()

        scenario.run()
        scenario.generate_random_name.assert_called_once_with()
        scenario._user_create.assert_called_once_with()
        scenario._update_user_password.assert_called_once_with(fake_user.id,
                                                               fake_password)

    def test_create_and_list_services(self):
        scenario = basic.CreateAndListServices(self.context)
        service_type = "test_service_type"
        description = "test_description"
        fake_service = mock.MagicMock()
        scenario._service_create = mock.MagicMock(return_value=fake_service)
        scenario._list_services = mock.MagicMock()
        scenario.run(service_type=service_type, description=description)
        scenario._service_create.assert_called_once_with(service_type,
                                                         description)
        scenario._list_services.assert_called_once_with()

    def test_create_and_list_ec2credentials(self):
        context = self._get_context()
        scenario = basic.CreateAndListEc2Credentials(context)
        scenario._create_ec2credentials = mock.MagicMock()
        scenario._list_ec2credentials = mock.MagicMock()
        scenario.run()
        scenario._create_ec2credentials.assert_called_once_with(
            "fake_user_id", "fake_tenant_id")
        scenario._list_ec2credentials.assert_called_with("fake_user_id")

    def test_create_and_delete_ec2credential(self):
        fake_creds = mock.MagicMock()
        context = self._get_context()
        scenario = basic.CreateAndDeleteEc2Credential(context)
        scenario._create_ec2credentials = mock.MagicMock(
            return_value=fake_creds)
        scenario._delete_ec2credential = mock.MagicMock()
        scenario.run()
        scenario._create_ec2credentials.assert_called_once_with(
            "fake_user_id", "fake_tenant_id")
        scenario._delete_ec2credential.assert_called_once_with(
            "fake_user_id", fake_creds.access)

    def test_add_and_remove_user_role(self):
        context = self._get_context()
        tenant_id = context["tenant"]["id"]
        user_id = context["user"]["id"]

        scenario = basic.AddAndRemoveUserRole(context)
        fake_role = mock.MagicMock()
        scenario._role_create = mock.MagicMock(return_value=fake_role)
        scenario._role_add = mock.MagicMock()
        scenario._role_remove = mock.MagicMock()

        scenario.run()

        scenario._role_create.assert_called_once_with()
        scenario._role_add.assert_called_once_with(
            user_id, fake_role, tenant_id)
        scenario._role_remove.assert_called_once_with(
            user_id, fake_role, tenant_id)
