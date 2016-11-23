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

import ddt
import mock

from rally.plugins.openstack.scenarios.keystone import basic
from tests.unit import test


@ddt.ddt
class KeystoneBasicTestCase(test.ScenarioTestCase):

    def get_test_context(self):
        context = super(KeystoneBasicTestCase, self).get_test_context()
        context.update({
            "admin": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "user": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake_tenant_id",
                       "name": "fake_tenant_name"}
        })
        return context

    def setUp(self):
        super(KeystoneBasicTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.identity.identity.Identity")
        self.addCleanup(patch.stop)
        self.mock_identity = patch.start()

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
        context = self.context
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
        fake_tenant = self.context["tenant"]["id"]
        fake_user = self.context["user"]["id"]
        fake_role = mock.MagicMock()

        self.mock_identity.return_value.create_role.return_value = fake_role

        scenario = basic.AddAndRemoveUserRole(self.context)
        scenario.run()

        self.mock_identity.return_value.create_role.assert_called_once_with()
        self.mock_identity.return_value.add_role.assert_called_once_with(
            role_id=fake_role.id, user_id=fake_user, project_id=fake_tenant)

        self.mock_identity.return_value.revoke_role.assert_called_once_with(
            fake_role.id, user_id=fake_user, project_id=fake_tenant)

    def test_create_and_delete_role(self):
        fake_role = mock.MagicMock()
        self.mock_identity.return_value.create_role.return_value = fake_role

        scenario = basic.CreateAndDeleteRole(self.context)
        scenario.run()

        self.mock_identity.return_value.create_role.assert_called_once_with()
        self.mock_identity.return_value.delete_role.assert_called_once_with(
            fake_role.id)

    def test_create_and_get_role(self):
        fake_role = mock.MagicMock()
        self.mock_identity.return_value.create_role.return_value = fake_role

        scenario = basic.CreateAndGetRole(self.context)
        scenario.run()

        self.mock_identity.return_value.create_role.assert_called_once_with()
        self.mock_identity.return_value.get_role.assert_called_once_with(
            fake_role.id)

    def test_create_and_list_user_roles(self):
        scenario = basic.CreateAddAndListUserRoles(self.context)
        fake_tenant = self.context["tenant"]["id"]
        fake_user = self.context["user"]["id"]
        fake_role = mock.MagicMock()
        self.mock_identity.return_value.create_role.return_value = fake_role

        scenario.run()

        self.mock_identity.return_value.create_role.assert_called_once_with()
        self.mock_identity.return_value.add_role.assert_called_once_with(
            user_id=fake_user, role_id=fake_role.id, project_id=fake_tenant)
        self.mock_identity.return_value.list_roles.assert_called_once_with(
            user_id=fake_user, project_id=fake_tenant)

    @ddt.data(None, "keystone", "fooservice")
    def test_get_entities(self, service_name):
        fake_tenant = mock.MagicMock()
        fake_user = mock.MagicMock()
        fake_role = mock.MagicMock()
        fake_service = mock.MagicMock()

        self.mock_identity.return_value.create_role.return_value = fake_role

        scenario = basic.GetEntities(self.context)

        scenario._tenant_create = mock.MagicMock(return_value=fake_tenant)
        scenario._user_create = mock.MagicMock(return_value=fake_user)

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
        self.mock_identity.return_value.create_role.assert_called_once_with()

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
        context = self.context
        scenario = basic.CreateAndListEc2Credentials(context)
        scenario._create_ec2credentials = mock.MagicMock()
        scenario._list_ec2credentials = mock.MagicMock()
        scenario.run()
        scenario._create_ec2credentials.assert_called_once_with(
            "fake_user_id", "fake_tenant_id")
        scenario._list_ec2credentials.assert_called_with("fake_user_id")

    def test_create_and_delete_ec2credential(self):
        fake_creds = mock.MagicMock()
        context = self.context
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
        context = self.context
        tenant_id = context["tenant"]["id"]
        user_id = context["user"]["id"]

        fake_role = mock.MagicMock()
        self.mock_identity.return_value.create_role.return_value = fake_role

        scenario = basic.AddAndRemoveUserRole(context)
        scenario.run()

        self.mock_identity.return_value.create_role.assert_called_once_with()
        self.mock_identity.return_value.add_role.assert_called_once_with(
            role_id=fake_role.id, user_id=user_id, project_id=tenant_id)
        self.mock_identity.return_value.revoke_role.assert_called_once_with(
            fake_role.id, user_id=user_id, project_id=tenant_id)
