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

        scenario.run(password="tttt", project_id="id")
        self.mock_identity.return_value.create_user.assert_called_once_with(
            password="tttt", project_id="id")

    def test_create_delete_user(self):
        identity_service = self.mock_identity.return_value

        fake_email = "abcd"
        fake_user = identity_service.create_user.return_value

        scenario = basic.CreateDeleteUser(self.context)

        scenario.run(email=fake_email, enabled=True)

        identity_service.create_user.assert_called_once_with(
            email=fake_email, enabled=True)
        identity_service.delete_user.assert_called_once_with(fake_user.id)

    def test_create_user_set_enabled_and_delete(self):
        identity_service = self.mock_identity.return_value

        scenario = basic.CreateUserSetEnabledAndDelete(self.context)

        fake_email = "abcd"
        fake_user = identity_service.create_user.return_value
        scenario.run(enabled=True, email=fake_email)

        identity_service.create_user.assert_called_once_with(
            email=fake_email, enabled=True)
        identity_service.update_user.assert_called_once_with(
            fake_user.id, enabled=False)
        identity_service.delete_user.assert_called_once_with(fake_user.id)

    def test_user_authenticate_and_validate_token(self):
        identity_service = self.mock_identity.return_value
        scenario = basic.AuthenticateUserAndValidateToken(self.context)

        fake_token = identity_service.fetch_token.return_value

        scenario.run()

        identity_service.fetch_token.assert_called_once_with()
        identity_service.validate_token.assert_called_once_with(fake_token)

    def test_create_tenant(self):
        scenario = basic.CreateTenant(self.context)

        scenario.run(enabled=True)

        self.mock_identity.return_value.create_project.assert_called_once_with(
            enabled=True)

    def test_create_tenant_with_users(self):
        identity_service = self.mock_identity.return_value

        fake_project = identity_service.create_project.return_value
        number_of_users = 1

        scenario = basic.CreateTenantWithUsers(self.context)

        scenario.run(users_per_tenant=number_of_users, enabled=True)

        identity_service.create_project.assert_called_once_with(enabled=True)
        identity_service.create_users.assert_called_once_with(
            fake_project.id, number_of_users=number_of_users)

    def test_create_and_list_users(self):
        scenario = basic.CreateAndListUsers(self.context)

        passwd = "tttt"
        project_id = "id"

        scenario.run(password=passwd, project_id=project_id)
        self.mock_identity.return_value.create_user.assert_called_once_with(
            password=passwd, project_id=project_id)
        self.mock_identity.return_value.list_users.assert_called_once_with()

    def test_create_and_list_tenants(self):
        identity_service = self.mock_identity.return_value
        scenario = basic.CreateAndListTenants(self.context)

        scenario.run(enabled=True)
        identity_service.create_project.assert_called_once_with(enabled=True)
        identity_service.list_projects.assert_called_once_with()

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
        identity_service = self.mock_identity.return_value

        fake_project = identity_service.create_project.return_value
        fake_user = identity_service.create_user.return_value
        fake_role = identity_service.create_role.return_value
        fake_service = identity_service.create_service.return_value

        scenario = basic.GetEntities(self.context)

        scenario.run(service_name)

        identity_service.create_project.assert_called_once_with()
        identity_service.create_user.assert_called_once_with(
            project_id=fake_project.id)
        identity_service.create_role.assert_called_once_with()

        identity_service.get_project.assert_called_once_with(fake_project.id)
        identity_service.get_user.assert_called_once_with(fake_user.id)
        identity_service.get_role.assert_called_once_with(fake_role.id)

        if service_name is None:
            identity_service.create_service.assert_called_once_with()
            self.assertFalse(identity_service.get_service_by_name.called)
            identity_service.get_service.assert_called_once_with(
                fake_service.id)
        else:
            identity_service.get_service_by_name.assert_called_once_with(
                service_name)
            self.assertFalse(identity_service.create_service.called)
            identity_service.get_service.assert_called_once_with(
                identity_service.get_service_by_name.return_value.id)

    def test_create_and_delete_service(self):
        identity_service = self.mock_identity.return_value
        scenario = basic.CreateAndDeleteService(self.context)

        service_type = "test_service_type"
        description = "test_description"
        fake_service = identity_service.create_service.return_value

        scenario.run(service_type=service_type, description=description)

        identity_service.create_service.assert_called_once_with(
            service_type=service_type, description=description)
        identity_service.delete_service.assert_called_once_with(
            fake_service.id)

    def test_create_update_and_delete_tenant(self):
        identity_service = self.mock_identity.return_value

        scenario = basic.CreateUpdateAndDeleteTenant(self.context)

        gen_name = mock.MagicMock()
        basic.CreateUpdateAndDeleteTenant.generate_random_name = gen_name
        fake_project = identity_service.create_project.return_value

        scenario.run()

        identity_service.create_project.assert_called_once_with()
        identity_service.update_project.assert_called_once_with(
            fake_project.id, description=gen_name.return_value,
            name=gen_name.return_value)
        identity_service.delete_project(fake_project.id)

    def test_create_user_update_password(self):
        identity_service = self.mock_identity.return_value

        scenario = basic.CreateUserUpdatePassword(self.context)

        fake_password = "pswd"
        fake_user = identity_service.create_user.return_value
        scenario.generate_random_name = mock.MagicMock(
            return_value=fake_password)

        scenario.run()

        scenario.generate_random_name.assert_called_once_with()
        identity_service.create_user.assert_called_once_with()
        identity_service.update_user.assert_called_once_with(
            fake_user.id, password=fake_password)

    def test_create_and_list_services(self):
        identity_service = self.mock_identity.return_value

        scenario = basic.CreateAndListServices(self.context)
        service_type = "test_service_type"
        description = "test_description"

        scenario.run(service_type=service_type, description=description)

        identity_service.create_service.assert_called_once_with(
            service_type=service_type, description=description)
        identity_service.list_services.assert_called_once_with()

    def test_create_and_list_ec2credentials(self):
        identity_service = self.mock_identity.return_value

        scenario = basic.CreateAndListEc2Credentials(self.context)

        scenario.run()

        identity_service.create_ec2credentials.assert_called_once_with(
            self.context["user"]["id"],
            project_id=self.context["tenant"]["id"])
        identity_service.list_ec2credentials.assert_called_with(
            self.context["user"]["id"])

    def test_create_and_delete_ec2credential(self):
        identity_service = self.mock_identity.return_value

        fake_creds = identity_service.create_ec2credentials.return_value

        scenario = basic.CreateAndDeleteEc2Credential(self.context)

        scenario.run()

        identity_service.create_ec2credentials.assert_called_once_with(
            self.context["user"]["id"],
            project_id=self.context["tenant"]["id"])
        identity_service.delete_ec2credential.assert_called_once_with(
            self.context["user"]["id"], access=fake_creds.access)

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
