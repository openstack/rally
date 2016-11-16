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

from rally.plugins.openstack.services.identity import identity
from tests.unit import test


@ddt.ddt
class IdentityTestCase(test.TestCase):
    def setUp(self):
        super(IdentityTestCase, self).setUp()
        self.clients = mock.MagicMock()

    def get_service_with_fake_impl(self):
        path = "rally.plugins.openstack.services.identity.identity"
        with mock.patch("%s.Identity.discover_impl" % path) as mock_discover:
            mock_discover.return_value = mock.MagicMock(), None
            service = identity.Identity(self.clients)
        return service

    def test_create_project(self):
        service = self.get_service_with_fake_impl()
        project_name = "name"
        domain_name = "domain"
        service.create_project(project_name, domain_name=domain_name)
        service._impl.create_project.assert_called_once_with(
            project_name, domain_name=domain_name)

    def test_update_project(self):
        service = self.get_service_with_fake_impl()

        project_id = "id"
        project_name = "name"
        description = "descr"
        enabled = False
        service.update_project(project_id=project_id, name=project_name,
                               description=description, enabled=enabled)
        service._impl.update_project.assert_called_once_with(
            project_id, name=project_name, description=description,
            enabled=enabled)

    def test_delete_project(self):
        service = self.get_service_with_fake_impl()
        project = "id"
        service.delete_project(project)
        service._impl.delete_project.assert_called_once_with(project)

    def test_list_projects(self):
        service = self.get_service_with_fake_impl()
        service.list_projects()
        service._impl.list_projects.assert_called_once_with()

    def test_get_project(self):
        service = self.get_service_with_fake_impl()
        project = "id"
        service.get_project(project)
        service._impl.get_project.assert_called_once_with(project)

    def test_create_user(self):
        service = self.get_service_with_fake_impl()

        username = "username"
        password = "password"
        project_id = "project_id"
        domain_name = "domain_name"

        service.create_user(username=username, password=password,
                            project_id=project_id, domain_name=domain_name)
        service._impl.create_user.assert_called_once_with(
            username=username, password=password, project_id=project_id,
            domain_name=domain_name, default_role="member")

    def test_create_users(self):
        service = self.get_service_with_fake_impl()

        project_id = "project_id"
        n = 3
        user_create_args = {}

        service.create_users(project_id, number_of_users=n,
                             user_create_args=user_create_args)
        service._impl.create_users.assert_called_once_with(
            project_id, number_of_users=n, user_create_args=user_create_args)

    def test_delete_user(self):
        service = self.get_service_with_fake_impl()
        user_id = "fake_id"
        service.delete_user(user_id)
        service._impl.delete_user.assert_called_once_with(user_id)

    def test_list_users(self):
        service = self.get_service_with_fake_impl()
        service.list_users()
        service._impl.list_users.assert_called_once_with()

    def test_update_user(self):
        service = self.get_service_with_fake_impl()

        user_id = "id"
        user_name = "name"
        email = "mail"
        password = "pass"
        enabled = False
        service.update_user(user_id, name=user_name, password=password,
                            email=email, enabled=enabled)
        service._impl.update_user.assert_called_once_with(
            user_id, name=user_name, password=password, email=email,
            enabled=enabled)

    def test_get_user(self):
        service = self.get_service_with_fake_impl()
        user = "id"
        service.get_user(user)
        service._impl.get_user.assert_called_once_with(user)

    def test_create_service(self):
        service = self.get_service_with_fake_impl()

        service_name = "name"
        service_type = "service_type"
        description = "descr"
        service.create_service(service_name, service_type=service_type,
                               description=description)
        service._impl.create_service.assert_called_once_with(
            name=service_name, service_type=service_type,
            description=description)

    def test_delete_service(self):
        service = self.get_service_with_fake_impl()
        service_id = "id"

        service.delete_service(service_id)
        service._impl.delete_service.assert_called_once_with(service_id)

    def test_list_services(self):
        service = self.get_service_with_fake_impl()
        service.list_services()
        service._impl.list_services.assert_called_once_with()

    def test_get_service(self):
        service = self.get_service_with_fake_impl()
        service_id = "id"
        service.get_service(service_id)
        service._impl.get_service.assert_called_once_with(service_id)

    def test_get_service_by_name(self):
        service = self.get_service_with_fake_impl()
        service_name = "name"
        service.get_service_by_name(service_name)
        service._impl.get_service_by_name.assert_called_once_with(service_name)

    def test_create_role(self):
        service = self.get_service_with_fake_impl()

        name = "name"
        service.create_role(name)
        service._impl.create_role.assert_called_once_with(
            name=name, domain_name="Default")

    def test_add_role(self):
        service = self.get_service_with_fake_impl()

        role_id = "id"
        user_id = "user_id"
        project_id = "project_id"
        service.add_role(role_id, user_id=user_id, project_id=project_id)
        service._impl.add_role.assert_called_once_with(role_id=role_id,
                                                       user_id=user_id,
                                                       project_id=project_id)

    def test_delete_role(self):
        service = self.get_service_with_fake_impl()
        role = "id"
        service.delete_role(role)
        service._impl.delete_role.assert_called_once_with(role)

    def test_revoke_role(self):
        service = self.get_service_with_fake_impl()

        role_id = "id"
        user_id = "user_id"
        project_id = "project_id"

        service.revoke_role(role_id, user_id=user_id, project_id=project_id)

        service._impl.revoke_role.assert_called_once_with(
            role_id=role_id, user_id=user_id, project_id=project_id)

    @ddt.data((None, None, None), ("user_id", "project_id", "domain"))
    def test_list_roles(self, params):
        user, project, domain = params
        service = self.get_service_with_fake_impl()
        service.list_roles(user_id=user, project_id=project,
                           domain_name=domain)
        service._impl.list_roles.assert_called_once_with(user_id=user,
                                                         project_id=project,
                                                         domain_name=domain)

    def test_get_role(self):
        service = self.get_service_with_fake_impl()
        role = "id"
        service.get_role(role)
        service._impl.get_role.assert_called_once_with(role)

    def test_create_ec2credentials(self):
        service = self.get_service_with_fake_impl()

        user_id = "id"
        project_id = "project-id"

        service.create_ec2credentials(user_id=user_id, project_id=project_id)
        service._impl.create_ec2credentials.assert_called_once_with(
            user_id=user_id, project_id=project_id)

    def test_list_ec2credentials(self):
        service = self.get_service_with_fake_impl()

        user_id = "id"

        service.list_ec2credentials(user_id=user_id)
        service._impl.list_ec2credentials.assert_called_once_with(user_id)

    def test_delete_ec2credential(self):
        service = self.get_service_with_fake_impl()

        user_id = "id"
        access = "access"

        service.delete_ec2credential(user_id=user_id, access=access)
        service._impl.delete_ec2credential.assert_called_once_with(
            user_id=user_id, access=access)

    def test_fetch_token(self):
        service = self.get_service_with_fake_impl()
        service.fetch_token()
        service._impl.fetch_token.assert_called_once_with()

    def test_validate_token(self):
        service = self.get_service_with_fake_impl()

        token = "id"
        service.validate_token(token)
        service._impl.validate_token.assert_called_once_with(token)
