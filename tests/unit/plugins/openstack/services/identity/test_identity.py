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

    def test_delete_project(self):
        service = self.get_service_with_fake_impl()
        project = "id"
        service.delete_project(project)
        service._impl.delete_project.assert_called_once_with(project)

    def test_list_projects(self):
        service = self.get_service_with_fake_impl()
        service.list_projects()
        service._impl.list_projects.assert_called_once_with()

    def test_create_user(self):
        service = self.get_service_with_fake_impl()

        username = "username"
        password = "password"
        email = "email"
        project_id = "project_id"
        domain_name = "domain_name"

        service.create_user(username=username, password=password, email=email,
                            project_id=project_id, domain_name=domain_name)
        service._impl.create_user.assert_called_once_with(
            username=username, password=password, email=email,
            project_id=project_id, domain_name=domain_name,
            default_role="member")

    def test_delete_user(self):
        service = self.get_service_with_fake_impl()
        user_id = "fake_id"
        service.delete_user(user_id)
        service._impl.delete_user.assert_called_once_with(user_id)

    def test_list_users(self):
        service = self.get_service_with_fake_impl()
        service.list_users()
        service._impl.list_users.assert_called_once_with()

    def test_delete_service(self):
        service = self.get_service_with_fake_impl()
        service_id = "id"

        service.delete_service(service_id)
        service._impl.delete_service.assert_called_once_with(service_id)

    def test_list_services(self):
        service = self.get_service_with_fake_impl()
        service.list_services()
        service._impl.list_services.assert_called_once_with()

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

    def test__unify_service(self):
        class SomeFakeService(object):
            id = 123123123123123
            name = "asdfasdfasdfasdfadf"
            other_var = "asdfasdfasdfasdfasdfasdfasdf"

        service = self.get_service_with_fake_impl()._unify_service(
            SomeFakeService())
        self.assertIsInstance(service, identity.Service)
        self.assertEqual(SomeFakeService.id, service.id)
        self.assertEqual(SomeFakeService.name, service.name)

    def test__unify_role(self):
        class SomeFakeRole(object):
            id = 123123123123123
            name = "asdfasdfasdfasdfadf"
            other_var = "asdfasdfasdfasdfasdfasdfasdf"

        role = self.get_service_with_fake_impl()._unify_role(
            SomeFakeRole())
        self.assertIsInstance(role, identity.Role)
        self.assertEqual(SomeFakeRole.id, role.id)
        self.assertEqual(SomeFakeRole.name, role.name)
