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

import uuid

import ddt
import mock

from rally.plugins.openstack.services.identity import identity
from rally.plugins.openstack.services.identity import keystone_v2
from tests.unit import test


PATH = "rally.plugins.openstack.services.identity.keystone_v2"


@ddt.ddt
class KeystoneV2ServiceTestCase(test.TestCase):
    def setUp(self):
        super(KeystoneV2ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.kc = self.clients.keystone.return_value
        self.name_generator = mock.MagicMock()
        self.service = keystone_v2.KeystoneV2Service(
            self.clients, name_generator=self.name_generator)

    def test_create_tenant(self):
        name = "name"
        tenant = self.service.create_tenant(name)

        self.assertEqual(tenant, self.kc.tenants.create.return_value)
        self.kc.tenants.create.assert_called_once_with(name)

    @ddt.data({"tenant_id": "fake_id", "name": True, "enabled": True,
               "description": True},
              {"tenant_id": "fake_id", "name": "some", "enabled": False,
               "description": "descr"})
    @ddt.unpack
    def test_update_tenant(self, tenant_id, name, enabled, description):

        self.name_generator.side_effect = ("foo", "bar")
        self.service.update_tenant(tenant_id,
                                   name=name,
                                   description=description,
                                   enabled=enabled)

        name = "foo" if name is True else name
        description = "bar" if description is True else description

        self.kc.tenants.update.assert_called_once_with(
            tenant_id, name=name, description=description, enabled=enabled)

    def test_delete_tenant(self):
        tenant_id = "fake_id"
        self.service.delete_tenant(tenant_id)
        self.kc.tenants.delete.assert_called_once_with(tenant_id)

    def test_list_tenants(self):
        self.assertEqual(self.kc.tenants.list.return_value,
                         self.service.list_tenants())
        self.kc.tenants.list.assert_called_once_with()

    def test_get_tenant(self):
        tenant_id = "fake_id"
        self.service.get_tenant(tenant_id)
        self.kc.tenants.get.assert_called_once_with(tenant_id)

    def test_create_user(self):
        name = "name"
        password = "passwd"
        email = "rally@example.com"
        tenant_id = "project"

        user = self.service.create_user(name, password=password, email=email,
                                        tenant_id=tenant_id)

        self.assertEqual(user, self.kc.users.create.return_value)
        self.kc.users.create.assert_called_once_with(
            name=name, password=password, email=email, tenant_id=tenant_id,
            enabled=True)

    def test_create_users(self):
        self.service.create_user = mock.MagicMock()

        n = 2
        tenant_id = "some"
        self.assertEqual([self.service.create_user.return_value] * n,
                         self.service.create_users(number_of_users=n,
                                                   tenant_id=tenant_id))
        self.assertEqual([mock.call(tenant_id=tenant_id)] * n,
                         self.service.create_user.call_args_list)

    def test_update_user_with_wrong_params(self):
        user_id = "fake_id"
        card_with_cvv2 = "1234 5678 9000 0000 : 666"
        self.assertRaises(NotImplementedError, self.service.update_user,
                          user_id, card_with_cvv2=card_with_cvv2)

    def test_update_user(self):
        user_id = "fake_id"
        name = "new name"
        email = "new.name2016@example.com"
        enabled = True
        self.service.update_user(user_id, name=name, email=email,
                                 enabled=enabled)
        self.kc.users.update.assert_called_once_with(
            user_id, name=name, email=email, enabled=enabled)

    def test_update_user_password(self):
        user_id = "fake_id"
        password = "qwerty123"
        self.service.update_user_password(user_id, password=password)
        self.kc.users.update_password.assert_called_once_with(
            user_id, password=password)

    @ddt.data({"name": None, "service_type": None, "description": None},
              {"name": "some", "service_type": "st", "description": "d"})
    @ddt.unpack
    def test_create_service(self, name, service_type, description):
        self.assertEqual(self.kc.services.create.return_value,
                         self.service.create_service(name=name,
                                                     service_type=service_type,
                                                     description=description))
        name = name or self.name_generator.return_value
        service_type = service_type or "rally_test_type"
        description = description or self.name_generator.return_value
        self.kc.services.create.assert_called_once_with(
            name, service_type=service_type, description=description)

    def test_create_role(self):
        name = "some"
        self.service.create_role(name)
        self.kc.roles.create.assert_called_once_with(name)

    def test_add_role(self):
        role_id = "fake_id"
        user_id = "user_id"
        tenant_id = "tenant_id"

        self.service.add_role(role_id, user_id=user_id, tenant_id=tenant_id)
        self.kc.roles.add_user_role.assert_called_once_with(
            user=user_id, role=role_id, tenant=tenant_id)

    def test_list_roles(self):
        self.assertEqual(self.kc.roles.list.return_value,
                         self.service.list_roles())
        self.kc.roles.list.assert_called_once_with()

    def test_list_roles_for_user(self):
        user_id = "user_id"
        tenant_id = "tenant_id"
        self.assertEqual(self.kc.roles.roles_for_user.return_value,
                         self.service.list_roles_for_user(user_id,
                                                          tenant_id=tenant_id))
        self.kc.roles.roles_for_user.assert_called_once_with(user_id,
                                                             tenant_id)

    def test_revoke_role(self):
        role_id = "fake_id"
        user_id = "user_id"
        tenant_id = "tenant_id"

        self.service.revoke_role(role_id, user_id=user_id,
                                 tenant_id=tenant_id)

        self.kc.roles.remove_user_role.assert_called_once_with(
            user=user_id, role=role_id, tenant=tenant_id)

    def test_create_ec2credentials(self):
        user_id = "fake_id"
        tenant_id = "fake_id"

        self.assertEqual(self.kc.ec2.create.return_value,
                         self.service.create_ec2credentials(
                             user_id, tenant_id=tenant_id))
        self.kc.ec2.create.assert_called_once_with(user_id,
                                                   tenant_id=tenant_id)


@ddt.ddt
class UnifiedKeystoneV2ServiceTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedKeystoneV2ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.service = keystone_v2.UnifiedKeystoneV2Service(self.clients)
        self.service._impl = mock.MagicMock()

    def test_init_identity_service(self):
        self.clients.keystone.return_value.version = "v2.0"
        self.assertIsInstance(identity.Identity(self.clients)._impl,
                              keystone_v2.UnifiedKeystoneV2Service)

    def test__check_domain(self):
        self.service._check_domain("Default")
        self.service._check_domain("default")
        self.assertRaises(NotImplementedError, self.service._check_domain,
                          "non-default")

    def test__unify_tenant(self):
        class KeystoneV2Tenant(object):
            def __init__(self, domain_id="domain_id"):
                self.id = str(uuid.uuid4())
                self.name = str(uuid.uuid4())
                self.domain_id = domain_id

        tenant = KeystoneV2Tenant()
        project = self.service._unify_tenant(tenant)
        self.assertIsInstance(project, identity.Project)
        self.assertEqual(tenant.id, project.id)
        self.assertEqual(tenant.name, project.name)
        self.assertEqual("default", project.domain_id)
        self.assertNotEqual(tenant.domain_id, project.domain_id)

    def test__unify_user(self):
        class KeystoneV2User(object):
            def __init__(self, tenantId=None):
                self.id = str(uuid.uuid4())
                self.name = str(uuid.uuid4())
                if tenantId is not None:
                    self.tenantId = tenantId

        user = KeystoneV2User()

        unified_user = self.service._unify_user(user)
        self.assertIsInstance(unified_user, identity.User)
        self.assertEqual(user.id, unified_user.id)
        self.assertEqual(user.name, unified_user.name)
        self.assertEqual("default", unified_user.domain_id)
        self.assertIsNone(unified_user.project_id)

        tenant_id = "tenant_id"
        user = KeystoneV2User(tenantId=tenant_id)
        unified_user = self.service._unify_user(user)
        self.assertIsInstance(unified_user, identity.User)
        self.assertEqual(user.id, unified_user.id)
        self.assertEqual(user.name, unified_user.name)
        self.assertEqual("default", unified_user.domain_id)
        self.assertEqual(tenant_id, unified_user.project_id)

    @mock.patch("%s.UnifiedKeystoneV2Service._check_domain" % PATH)
    @mock.patch("%s.UnifiedKeystoneV2Service._unify_tenant" % PATH)
    def test_create_project(
            self, mock_unified_keystone_v2_service__unify_tenant,
            mock_unified_keystone_v2_service__check_domain):
        mock_unify_tenant = mock_unified_keystone_v2_service__unify_tenant
        mock_check_domain = mock_unified_keystone_v2_service__check_domain
        name = "name"

        self.assertEqual(mock_unify_tenant.return_value,
                         self.service.create_project(name))
        mock_check_domain.assert_called_once_with("Default")
        mock_unify_tenant.assert_called_once_with(
            self.service._impl.create_tenant.return_value)
        self.service._impl.create_tenant.assert_called_once_with(name)

    def test_update_project(self):
        tenant_id = "fake_id"
        name = "name"
        description = "descr"
        enabled = False

        self.service.update_project(project_id=tenant_id, name=name,
                                    description=description, enabled=enabled)
        self.service._impl.update_tenant.assert_called_once_with(
            tenant_id=tenant_id, name=name, description=description,
            enabled=enabled)

    def test_delete_project(self):
        tenant_id = "fake_id"
        self.service.delete_project(tenant_id)
        self.service._impl.delete_tenant.assert_called_once_with(tenant_id)

    @mock.patch("%s.UnifiedKeystoneV2Service._unify_tenant" % PATH)
    def test_get_project(self,
                         mock_unified_keystone_v2_service__unify_tenant):
        mock_unify_tenant = mock_unified_keystone_v2_service__unify_tenant
        tenant_id = "id"

        self.assertEqual(mock_unify_tenant.return_value,
                         self.service.get_project(tenant_id))
        mock_unify_tenant.assert_called_once_with(
            self.service._impl.get_tenant.return_value)
        self.service._impl.get_tenant.assert_called_once_with(tenant_id)

    @mock.patch("%s.UnifiedKeystoneV2Service._unify_tenant" % PATH)
    def test_list_projects(self,
                           mock_unified_keystone_v2_service__unify_tenant):
        mock_unify_tenant = mock_unified_keystone_v2_service__unify_tenant

        tenants = [mock.MagicMock()]
        self.service._impl.list_tenants.return_value = tenants

        self.assertEqual([mock_unify_tenant.return_value],
                         self.service.list_projects())
        mock_unify_tenant.assert_called_once_with(tenants[0])

    @mock.patch("%s.UnifiedKeystoneV2Service._check_domain" % PATH)
    @mock.patch("%s.UnifiedKeystoneV2Service._unify_user" % PATH)
    def test_create_user(self, mock_unified_keystone_v2_service__unify_user,
                         mock_unified_keystone_v2_service__check_domain):
        mock_check_domain = mock_unified_keystone_v2_service__check_domain
        mock_unify_user = mock_unified_keystone_v2_service__unify_user

        name = "name"
        password = "passwd"
        tenant_id = "project"

        self.assertEqual(mock_unify_user.return_value,
                         self.service.create_user(name, password=password,
                                                  project_id=tenant_id))
        mock_check_domain.assert_called_once_with("Default")
        mock_unify_user.assert_called_once_with(
            self.service._impl.create_user.return_value)
        self.service._impl.create_user.assert_called_once_with(
            username=name, password=password, tenant_id=tenant_id,
            enabled=True)

    @mock.patch("%s.UnifiedKeystoneV2Service._check_domain" % PATH)
    @mock.patch("%s.UnifiedKeystoneV2Service._unify_user" % PATH)
    def test_create_users(self, mock_unified_keystone_v2_service__unify_user,
                          mock_unified_keystone_v2_service__check_domain):
        mock_check_domain = mock_unified_keystone_v2_service__check_domain

        tenant_id = "project"
        n = 3
        domain_name = "Default"

        self.service.create_users(
            tenant_id, number_of_users=3,
            user_create_args={"domain_name": domain_name})
        mock_check_domain.assert_called_once_with(domain_name)
        self.service._impl.create_users.assert_called_once_with(
            tenant_id=tenant_id, number_of_users=n,
            user_create_args={"domain_name": domain_name})

    @mock.patch("%s.UnifiedKeystoneV2Service._unify_user" % PATH)
    def test_list_users(self, mock_unified_keystone_v2_service__unify_user):
        mock_unify_user = mock_unified_keystone_v2_service__unify_user

        users = [mock.MagicMock()]
        self.service._impl.list_users.return_value = users

        self.assertEqual([mock_unify_user.return_value],
                         self.service.list_users())
        mock_unify_user.assert_called_once_with(users[0])

    @ddt.data({"user_id": "id", "enabled": False, "name": "Fake",
               "email": "badboy@example.com", "password": "pass"},
              {"user_id": "id", "enabled": None, "name": None,
               "email": None, "password": None})
    @ddt.unpack
    def test_update_user(self, user_id, enabled, name, email, password):
        self.service.update_user(user_id, enabled=enabled, name=name,
                                 email=email, password=password)
        if password:
            self.service._impl.update_user_password.assert_called_once_with(
                user_id=user_id, password=password)

        args = {}
        if enabled is not None:
            args["enabled"] = enabled
        if name is not None:
            args["name"] = name
        if email is not None:
            args["email"] = email

        if args:
            self.service._impl.update_user.assert_called_once_with(
                user_id, **args)

    @mock.patch("%s.UnifiedKeystoneV2Service._unify_service" % PATH)
    def test_list_services(self,
                           mock_unified_keystone_v2_service__unify_service):
        mock_unify_service = mock_unified_keystone_v2_service__unify_service

        services = [mock.MagicMock()]
        self.service._impl.list_services.return_value = services

        self.assertEqual([mock_unify_service.return_value],
                         self.service.list_services())
        mock_unify_service.assert_called_once_with(services[0])

    @mock.patch("%s.UnifiedKeystoneV2Service._unify_role" % PATH)
    def test_create_role(self, mock_unified_keystone_v2_service__unify_role):
        mock_unify_role = mock_unified_keystone_v2_service__unify_role
        name = "some"

        self.assertEqual(mock_unify_role.return_value,
                         self.service.create_role(name))

        self.service._impl.create_role.assert_called_once_with(name)
        mock_unify_role.assert_called_once_with(
            self.service._impl.create_role.return_value)

    def test_add_role(self):

        role_id = "fake_id"
        user_id = "user_id"
        project_id = "user_id"

        self.service.add_role(role_id, user_id=user_id,
                              project_id=project_id)

        self.service._impl.add_role.assert_called_once_with(
            user_id=user_id, role_id=role_id, tenant_id=project_id)

    def test_delete_role(self):
        role_id = "fake_id"
        self.service.delete_role(role_id)
        self.service._impl.delete_role.assert_called_once_with(role_id)

    def test_revoke_role(self):
        role_id = "fake_id"
        user_id = "user_id"
        project_id = "user_id"

        self.service.revoke_role(role_id, user_id=user_id,
                                 project_id=project_id)

        self.service._impl.revoke_role.assert_called_once_with(
            user_id=user_id, role_id=role_id, tenant_id=project_id)

    @mock.patch("%s.UnifiedKeystoneV2Service._unify_role" % PATH)
    def test_list_roles(self, mock_unified_keystone_v2_service__unify_role):
        mock_unify_role = mock_unified_keystone_v2_service__unify_role

        roles = [mock.MagicMock()]
        another_roles = [mock.MagicMock()]
        self.service._impl.list_roles.return_value = roles
        self.service._impl.list_roles_for_user.return_value = another_roles

        # case 1
        self.assertEqual([mock_unify_role.return_value],
                         self.service.list_roles())
        self.service._impl.list_roles.assert_called_once_with()
        mock_unify_role.assert_called_once_with(roles[0])
        self.assertFalse(self.service._impl.list_roles_for_user.called)

        self.service._impl.list_roles.reset_mock()
        mock_unify_role.reset_mock()

        # case 2
        user = "user"
        project = "project"
        self.assertEqual([mock_unify_role.return_value],
                         self.service.list_roles(user_id=user,
                                                 project_id=project))
        self.service._impl.list_roles_for_user.assert_called_once_with(
            user, tenant_id=project)
        self.assertFalse(self.service._impl.list_roles.called)
        mock_unify_role.assert_called_once_with(another_roles[0])

        # case 3
        self.assertRaises(NotImplementedError, self.service.list_roles,
                          domain_name="some")

    def test_create_ec2credentials(self):
        user_id = "id"
        tenant_id = "tenant-id"

        self.assertEqual(self.service._impl.create_ec2credentials.return_value,
                         self.service.create_ec2credentials(
                             user_id=user_id, project_id=tenant_id))

        self.service._impl.create_ec2credentials.assert_called_once_with(
            user_id=user_id, tenant_id=tenant_id)
