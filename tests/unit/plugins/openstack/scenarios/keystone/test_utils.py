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

from rally.plugins.openstack.scenarios.keystone import utils
from tests.unit import fakes
from tests.unit import test

UTILS = "rally.plugins.openstack.scenarios.keystone.utils."


@ddt.ddt
class KeystoneScenarioTestCase(test.ScenarioTestCase):

    @mock.patch("uuid.uuid4", return_value="pwd")
    def test_user_create(self, mock_uuid4):
        scenario = utils.KeystoneScenario(self.context)
        scenario.generate_random_name = mock.Mock(return_value="foobarov")
        result = scenario._user_create()

        self.assertEqual(
            self.admin_clients("keystone").users.create.return_value, result)
        self.admin_clients("keystone").users.create.assert_called_once_with(
            "foobarov",
            password=mock_uuid4.return_value,
            email="foobarov@rally.me")
        mock_uuid4.assert_called_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_user")

    def test_update_user_enabled(self):
        user = mock.Mock()
        enabled = mock.Mock()
        scenario = utils.KeystoneScenario(self.context)

        scenario._update_user_enabled(user, enabled)
        self.admin_clients(
            "keystone").users.update_enabled.assert_called_once_with(user,
                                                                     enabled)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.update_user_enabled")

    def test_token_validate(self):
        token = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)

        scenario._token_validate(token)
        self.admin_clients(
            "keystone").tokens.validate.assert_called_once_with(token)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.validate_token")

    def test_token_authenticate(self):
        name = mock.MagicMock()
        psswd = "foopsswd"
        tenant_id = mock.MagicMock()
        tenant_name = mock.MagicMock()

        scenario = utils.KeystoneScenario(self.context)
        scenario._authenticate_token(name, psswd, tenant_id, tenant_name)
        self.admin_clients(
            "keystone").tokens.authenticate.assert_called_once_with(
            name, tenant_id, tenant_name, "foopsswd")

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.token_authenticate")

    def test_role_create(self):
        scenario = utils.KeystoneScenario(self.context)
        scenario.generate_random_name = mock.Mock()
        result = scenario._role_create()

        self.assertEqual(
            self.admin_clients("keystone").roles.create.return_value, result)
        self.admin_clients("keystone").roles.create.assert_called_once_with(
            scenario.generate_random_name.return_value)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_role")

    def test_list_roles_for_user(self):
        user = mock.MagicMock()
        tenant = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)

        scenario._list_roles_for_user(user, tenant)

        self.admin_clients(
            "keystone").roles.roles_for_user.assert_called_once_with(user,
                                                                     tenant)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.list_roles")

    def test_role_add(self):
        user = mock.MagicMock()
        role = mock.MagicMock()
        tenant = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)

        scenario._role_add(user=user.id, role=role.id, tenant=tenant.id)

        self.admin_clients(
            "keystone").roles.add_user_role.assert_called_once_with(user.id,
                                                                    role.id,
                                                                    tenant.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.add_role")

    def test_user_delete(self):
        resource = fakes.FakeResource()
        resource.delete = mock.MagicMock()

        scenario = utils.KeystoneScenario(self.context)
        scenario._resource_delete(resource)
        resource.delete.assert_called_once_with()
        r = "keystone.delete_%s" % resource.__class__.__name__.lower()
        self._test_atomic_action_timer(scenario.atomic_actions(), r)

    def test_role_remove(self):
        user = mock.MagicMock()
        role = mock.MagicMock()
        tenant = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)

        scenario._role_remove(user=user, role=role, tenant=tenant)

        self.admin_clients(
            "keystone").roles.remove_user_role.assert_called_once_with(user,
                                                                       role,
                                                                       tenant)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.remove_role")

    def test_tenant_create(self):
        scenario = utils.KeystoneScenario(self.context)
        scenario.generate_random_name = mock.Mock()
        result = scenario._tenant_create()

        self.assertEqual(
            self.admin_clients("keystone").tenants.create.return_value, result)
        self.admin_clients("keystone").tenants.create.assert_called_once_with(
            scenario.generate_random_name.return_value)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_tenant")

    @ddt.data(
        {"service_type": "service_type"},
        {"service_type": None}
    )
    def test_service_create(self, service_type):
        scenario = utils.KeystoneScenario(self.context)
        scenario.generate_random_name = mock.Mock()

        result = scenario._service_create(
            service_type=service_type, description="description")

        self.assertEqual(
            self.admin_clients("keystone").services.create.return_value,
            result)
        if service_type == "service_type":
            self.admin_clients(
                "keystone").services.create.assert_called_once_with(
                scenario.generate_random_name.return_value,
                service_type, description="description")
        elif service_type is None:
            self.admin_clients(
                "keystone").services.create.assert_called_once_with(
                scenario.generate_random_name.return_value,
                "rally_test_type", description="description")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_service")

    def test_tenant_create_with_users(self):
        tenant = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)
        scenario.generate_random_name = mock.Mock(return_value="foobarov")

        scenario._users_create(tenant, users_per_tenant=1)

        self.admin_clients("keystone").users.create.assert_called_once_with(
            "foobarov", password="foobarov", email="foobarov@rally.me",
            tenant_id=tenant.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_users")

    def test_list_users(self):
        scenario = utils.KeystoneScenario(self.context)
        scenario._list_users()
        self.admin_clients("keystone").users.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.list_users")

    def test_list_tenants(self):
        scenario = utils.KeystoneScenario(self.context)
        scenario._list_tenants()
        self.admin_clients("keystone").tenants.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.list_tenants")

    def test_list_services(self):
        scenario = utils.KeystoneScenario(self.context)
        scenario._list_services()

        self.admin_clients("keystone").services.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.service_list")

    def test_delete_service(self):
        service = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)
        scenario._delete_service(service_id=service.id)

        self.admin_clients("keystone").services.delete.assert_called_once_with(
            service.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.delete_service")

    def test_get_tenant(self):
        tenant = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)
        scenario._get_tenant(tenant_id=tenant.id)

        self.admin_clients("keystone").tenants.get.assert_called_once_with(
            tenant.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_tenant")

    def test_get_user(self):
        user = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)
        scenario._get_user(user_id=user.id)

        self.admin_clients("keystone").users.get.assert_called_once_with(
            user.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_user")

    def test_get_role(self):
        role = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)
        scenario._get_role(role_id=role.id)

        self.admin_clients("keystone").roles.get.assert_called_once_with(
            role.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_role")

    def test_get_service(self):
        service = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)
        scenario._get_service(service_id=service.id)

        self.admin_clients("keystone").services.get.assert_called_once_with(
            service.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_service")

    def test_update_tenant(self):
        tenant = mock.MagicMock()
        description = "new description"

        scenario = utils.KeystoneScenario(self.context)
        scenario.generate_random_name = mock.Mock()
        scenario._update_tenant(tenant=tenant, description=description)

        self.admin_clients("keystone").tenants.update.assert_called_once_with(
            tenant.id, scenario.generate_random_name.return_value,
            description)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.update_tenant")

    def test_update_user_password(self):
        password = "pswd"
        user = mock.MagicMock()
        scenario = utils.KeystoneScenario(self.context)

        scenario._update_user_password(password=password, user_id=user.id)

        self.admin_clients(
            "keystone").users.update_password.assert_called_once_with(user.id,
                                                                      password)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.update_user_password")

    @mock.patch("rally.plugins.openstack.scenario.OpenStackScenario."
                "admin_clients")
    def test_update_user_password_v3(self,
                                     mock_open_stack_scenario_admin_clients):
        password = "pswd"
        user = mock.MagicMock()
        scenario = utils.KeystoneScenario()

        type(mock_open_stack_scenario_admin_clients.return_value).version = (
            mock.PropertyMock(return_value="v3"))
        scenario._update_user_password(password=password, user_id=user.id)

        mock_open_stack_scenario_admin_clients(
            "keystone").users.update.assert_called_once_with(
            user.id, password=password)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.update_user_password")

    def test_get_service_by_name(self):
        scenario = utils.KeystoneScenario(self.context)
        svc_foo, svc_bar = mock.Mock(), mock.Mock()
        scenario._list_services = mock.Mock(return_value=[svc_foo, svc_bar])
        self.assertEqual(scenario._get_service_by_name(svc_bar.name), svc_bar)
        self.assertIsNone(scenario._get_service_by_name("spam"))

    @mock.patch(UTILS + "KeystoneScenario.clients")
    def test_create_ec2credentials(self, mock_clients):
        scenario = utils.KeystoneScenario(self.context)
        creds = mock.Mock()
        mock_clients("keystone").ec2.create.return_value = creds
        create_creds = scenario._create_ec2credentials("user_id",
                                                       "tenant_id")
        self.assertEqual(create_creds, creds)
        mock_clients("keystone").ec2.create.assert_called_once_with(
            "user_id", "tenant_id")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_ec2creds")

    @mock.patch(UTILS + "KeystoneScenario.clients")
    def test_list_ec2credentials(self, mock_clients):
        scenario = utils.KeystoneScenario(self.context)
        creds_list = mock.Mock()
        mock_clients("keystone").ec2.list.return_value = creds_list
        list_creds = scenario._list_ec2credentials("user_id")
        self.assertEqual(list_creds, creds_list)
        mock_clients("keystone").ec2.list.assert_called_once_with("user_id")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.list_ec2creds")

    @mock.patch(UTILS + "KeystoneScenario.clients")
    def test_delete_ec2credentials(self, mock_clients):
        scenario = utils.KeystoneScenario(self.context)
        mock_clients("keystone").ec2.delete = mock.MagicMock()
        scenario._delete_ec2credential("user_id", "access")
        mock_clients("keystone").ec2.delete.assert_called_once_with("user_id",
                                                                    "access")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.delete_ec2creds")
