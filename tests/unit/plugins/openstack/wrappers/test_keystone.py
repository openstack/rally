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

from keystoneclient import exceptions
import mock

from rally.plugins.openstack.wrappers import keystone
from tests.unit import test


class KeystoneWrapperTestBase(object):
    def test_list_services(self):
        service = mock.MagicMock()
        service.id = "fake_id"
        service.name = "Foobar"
        service.extra_field = "extra_field"
        self.client.services.list.return_value = [service]
        result = list(self.wrapped_client.list_services())
        self.assertEqual([("fake_id", "Foobar")], result)
        self.assertEqual("fake_id", result[0].id)
        self.assertEqual("Foobar", result[0].name)
        self.assertFalse(hasattr(result[0], "extra_field"))

    def test_wrap(self):
        client = mock.MagicMock()
        client.version = "dummy"
        self.assertRaises(NotImplementedError, keystone.wrap, client)

    def test_delete_service(self):
        self.wrapped_client.delete_service("fake_id")
        self.client.services.delete.assert_called_once_with("fake_id")

    def test_list_roles(self):
        role = mock.MagicMock()
        role.id = "fake_id"
        role.name = "Foobar"
        role.extra_field = "extra_field"
        self.client.roles.list.return_value = [role]
        result = list(self.wrapped_client.list_roles())
        self.assertEqual([("fake_id", "Foobar")], result)
        self.assertEqual("fake_id", result[0].id)
        self.assertEqual("Foobar", result[0].name)
        self.assertFalse(hasattr(result[0], "extra_field"))

    def test_delete_role(self):
        self.wrapped_client.delete_role("fake_id")
        self.client.roles.delete.assert_called_once_with("fake_id")


class KeystoneV2WrapperTestCase(test.TestCase, KeystoneWrapperTestBase):
    def setUp(self):
        super(KeystoneV2WrapperTestCase, self).setUp()
        self.client = mock.MagicMock()
        self.client.version = "v2.0"
        self.wrapped_client = keystone.wrap(self.client)

    def test_create_project(self):
        self.wrapped_client.create_project("Foobar")
        self.client.tenants.create.assert_called_once_with("Foobar")

    def test_create_project_in_non_default_domain_fail(self):
        self.assertRaises(
            NotImplementedError, self.wrapped_client.create_project,
            "Foobar", "non-default-domain")

    def test_delete_project(self):
        self.wrapped_client.delete_project("fake_id")
        self.client.tenants.delete.assert_called_once_with("fake_id")

    def test_list_projects(self):
        tenant = mock.MagicMock()
        tenant.id = "fake_id"
        tenant.name = "Foobar"
        tenant.extra_field = "extra_field"
        self.client.tenants.list.return_value = [tenant]
        result = list(self.wrapped_client.list_projects())
        self.assertEqual([("fake_id", "Foobar", "default")], result)
        self.assertEqual("fake_id", result[0].id)
        self.assertEqual("Foobar", result[0].name)
        self.assertEqual("default", result[0].domain_id)
        self.assertFalse(hasattr(result[0], "extra_field"))

    def test_create_user(self):
        self.wrapped_client.create_user("foo", "bar", email="foo@bar.com",
                                        project_id="tenant_id",
                                        domain_name="default")
        self.client.users.create.assert_called_once_with(
            "foo", "bar", "foo@bar.com", "tenant_id")

    def test_create_user_in_non_default_domain_fail(self):
        self.assertRaises(
            NotImplementedError, self.wrapped_client.create_user,
            "foo", "bar", email="foo@bar.com", project_id="tenant_id",
            domain_name="non-default-domain")

    def test_delete_user(self):
        self.wrapped_client.delete_user("fake_id")
        self.client.users.delete.assert_called_once_with("fake_id")

    def test_list_users(self):
        user = mock.MagicMock()
        user.id = "fake_id"
        user.name = "foo"
        user.tenantId = "tenant_id"
        user.extra_field = "extra_field"
        self.client.users.list.return_value = [user]
        result = list(self.wrapped_client.list_users())
        self.assertEqual([("fake_id", "foo", "tenant_id", "default")], result)
        self.assertEqual("fake_id", result[0].id)
        self.assertEqual("foo", result[0].name)
        self.assertEqual("tenant_id", result[0].project_id)
        self.assertEqual("default", result[0].domain_id)
        self.assertFalse(hasattr(result[0], "extra_field"))

    def test_create_role(self):
        self.wrapped_client.create_role("foo_name")
        self.client.roles.create.assert_called_once_with("foo_name")

    def test_add_role(self):
        self.wrapped_client.add_role("fake_role_id", "fake_user_id",
                                     "fake_project_id")
        self.client.roles.add_user_role.assert_called_once_with(
            "fake_user_id", "fake_role_id", tenant="fake_project_id")

    def test_remove_role(self):
        self.wrapped_client.remove_role("fake_role_id", "fake_user_id",
                                        "fake_project_id")
        self.client.roles.remove_user_role.assert_called_once_with(
            "fake_user_id", "fake_role_id", tenant="fake_project_id")


class KeystoneV3WrapperTestCase(test.TestCase, KeystoneWrapperTestBase):
    def setUp(self):
        super(KeystoneV3WrapperTestCase, self).setUp()
        self.client = mock.MagicMock()
        self.client.version = "v3"
        self.wrapped_client = keystone.wrap(self.client)
        self.client.domains.get.side_effect = exceptions.NotFound
        self.client.domains.list.return_value = [
            mock.MagicMock(id="domain_id")]

    def test_create_project(self):
        self.wrapped_client.create_project("Foobar", "domain")
        self.client.projects.create.assert_called_once_with(
            name="Foobar", domain="domain_id")

    def test_create_project_with_non_existing_domain_fail(self):
        self.client.domains.list.return_value = []
        self.assertRaises(exceptions.NotFound,
                          self.wrapped_client.create_project,
                          "Foobar", "non-existing-domain")

    def test_delete_project(self):
        self.wrapped_client.delete_project("fake_id")
        self.client.projects.delete.assert_called_once_with("fake_id")

    def test_list_projects(self):
        project = mock.MagicMock()
        project.id = "fake_id"
        project.name = "Foobar"
        project.domain_id = "domain_id"
        project.extra_field = "extra_field"
        self.client.projects.list.return_value = [project]
        result = list(self.wrapped_client.list_projects())
        self.assertEqual([("fake_id", "Foobar", "domain_id")], result)
        self.assertEqual("fake_id", result[0].id)
        self.assertEqual("Foobar", result[0].name)
        self.assertEqual("domain_id", result[0].domain_id)
        self.assertFalse(hasattr(result[0], "extra_field"))

    def test_create_user(self):
        fake_role = mock.MagicMock(id="fake_role_id")
        fake_role.name = "__member__"
        self.client.roles.list.return_value = [fake_role]
        self.client.users.create.return_value = mock.MagicMock(
            id="fake_user_id")

        self.wrapped_client.create_user(
            "foo", "bar", email="foo@bar.com",
            project_id="project_id", domain_name="domain")
        self.client.users.create.assert_called_once_with(
            name="foo", password="bar",
            email="foo@bar.com", default_project="project_id",
            domain="domain_id")

    def test_create_user_with_non_existing_domain_fail(self):
        self.client.domains.list.return_value = []
        self.assertRaises(exceptions.NotFound,
                          self.wrapped_client.create_user, "foo", "bar",
                          email="foo@bar.com", project_id="project_id",
                          domain_name="non-existing-domain")

    def test_delete_user(self):
        self.wrapped_client.delete_user("fake_id")
        self.client.users.delete.assert_called_once_with("fake_id")

    def test_list_users(self):
        user = mock.MagicMock()
        user.id = "fake_id"
        user.name = "foo"
        user.default_project_id = "project_id"
        user.domain_id = "domain_id"
        user.extra_field = "extra_field"
        self.client.users.list.return_value = [user]
        result = list(self.wrapped_client.list_users())
        self.assertEqual([("fake_id", "foo", "project_id", "domain_id")],
                         result)
        self.assertEqual("fake_id", result[0].id)
        self.assertEqual("foo", result[0].name)
        self.assertEqual("project_id", result[0].project_id)
        self.assertEqual("domain_id", result[0].domain_id)
        self.assertFalse(hasattr(result[0], "extra_field"))

    def test_create_role(self, **kwargs):
        self.wrapped_client.create_role("foo_name", domain="domain",
                                        **kwargs)
        self.client.roles.create.assert_called_once_with(
            "foo_name", domain="domain", **kwargs)

    def test_add_role(self):
        self.wrapped_client.add_role("fake_role_id", "fake_user_id",
                                     "fake_project_id")
        self.client.roles.grant.assert_called_once_with(
            "fake_role_id", user="fake_user_id", project="fake_project_id")

    def test_remove_role(self):
        self.wrapped_client.remove_role("fake_role_id", "fake_user_id",
                                        "fake_project_id")
        self.client.roles.revoke.assert_called_once_with(
            "fake_role_id", user="fake_user_id", project="fake_project_id")
