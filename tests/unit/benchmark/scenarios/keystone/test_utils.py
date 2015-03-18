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
import six

from rally.benchmark.scenarios.keystone import utils
from tests.unit import fakes
from tests.unit import test

UTILS = "rally.benchmark.scenarios.keystone.utils."


class KeystoneUtilsTestCase(test.TestCase):

    def test_RESOURCE_NAME_PREFIX(self):
        self.assertIsInstance(utils.KeystoneScenario.RESOURCE_NAME_PREFIX,
                              six.string_types)
        # Prefix must be long enough to guarantee that resource
        # to be recognized as created by rally
        self.assertTrue(
            len(utils.KeystoneScenario.RESOURCE_NAME_PREFIX) > 7)

    def test_is_temporary(self):
        prefix = utils.KeystoneScenario.RESOURCE_NAME_PREFIX
        tests = [
            (fakes.FakeResource(
                    name=prefix + "abc"),
                True),
            (fakes.FakeResource(name="another"), False),
            (fakes.FakeResource(
                    name=prefix[:-3] + "abc"),
                False)
        ]

        for resource, is_valid in tests:
            self.assertEqual(utils.is_temporary(resource), is_valid)


class KeystoneScenarioTestCase(test.TestCase):

    @mock.patch(UTILS + "uuid.uuid4", return_value="pwd")
    @mock.patch(UTILS + "KeystoneScenario._generate_random_name",
                return_value="abc")
    def test_user_create(self, mock_gen_name, mock_uuid4):
        user = {}
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.users.create = mock.MagicMock(return_value=user)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        result = scenario._user_create()

        self.assertEqual(user, result)
        fake_keystone.users.create.assert_called_once_with(
                    mock_gen_name.return_value,
                    password=mock_uuid4.return_value,
                    email=mock_gen_name.return_value + "@rally.me")
        mock_uuid4.assert_called_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_user")

    @mock.patch(UTILS + "KeystoneScenario._generate_random_name")
    def test_role_create(self, mock_gen_name):
        name = "abc"
        mock_gen_name.return_value = name

        role = {}
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.roles.create = mock.MagicMock(return_value=role)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        result = scenario._role_create()

        self.assertEqual(role, result)
        fake_keystone.roles.create.assert_called_once_with(name)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_role")

    def test_user_delete(self):
        resource = fakes.FakeResource()
        resource.delete = mock.MagicMock()

        scenario = utils.KeystoneScenario()
        scenario._resource_delete(resource)
        resource.delete.assert_called_once_with()
        r = "keystone.delete_%s" % resource.__class__.__name__.lower()
        self._test_atomic_action_timer(scenario.atomic_actions(), r)

    @mock.patch(UTILS + "KeystoneScenario._generate_random_name")
    def test_tenant_create(self, mock_gen_name):
        name = "abc"
        mock_gen_name.return_value = name

        tenant = {}
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.tenants.create = mock.MagicMock(return_value=tenant)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        result = scenario._tenant_create()

        self.assertEqual(tenant, result)
        fake_keystone.tenants.create.assert_called_once_with(name)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_tenant")

    @mock.patch(UTILS + "KeystoneScenario._generate_random_name")
    def test_service_create(self, mock_gen_name):
        name = "abc"
        mock_gen_name.return_value = name
        service_type = name + "service_type"
        description = name + "_description"

        service = {}
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.services.create = mock.MagicMock(return_value=service)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        result = scenario._service_create(name=name,
                                          service_type=service_type,
                                          description=description)

        self.assertEqual(service, result)
        fake_keystone.services.create.assert_called_once_with(name,
                                                              service_type,
                                                              description)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_service")

    @mock.patch(UTILS + "KeystoneScenario._generate_random_name")
    def test_tenant_create_with_users(self, mock_gen_name):
        name = "abc"
        mock_gen_name.return_value = name

        tenant = mock.MagicMock()
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.users.create = mock.MagicMock()
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._users_create(tenant, users_per_tenant=1, name_length=10)

        fake_keystone.users.create.assert_called_once_with(
                    name, password=name, email=name + "@rally.me",
                    tenant_id=tenant.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.create_users")

    def test_list_users(self):
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.users.list = mock.MagicMock()
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)
        scenario._list_users()
        fake_keystone.users.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.list_users")

    def test_list_tenants(self):
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.tenants.list = mock.MagicMock()
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)
        scenario._list_tenants()
        fake_keystone.tenants.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.list_tenants")

    def test_list_services(self):
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.services.list = mock.MagicMock()
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._list_services()

        fake_keystone.services.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.service_list")

    def test_delete_service(self):
        service = mock.MagicMock()
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.services.delete = mock.MagicMock()
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._delete_service(service_id=service.id)

        fake_keystone.services.delete.assert_called_once_with(service.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.delete_service")

    def test_get_tenant(self):
        tenant = mock.MagicMock()
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.tenants.get = mock.MagicMock(return_value=tenant)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._get_tenant(tenant_id=tenant.id)

        fake_keystone.tenants.get.assert_called_once_with(tenant.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_tenant")

    def test_get_user(self):
        user = mock.MagicMock()
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.users.get = mock.MagicMock(return_value=user)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._get_user(user_id=user.id)

        fake_keystone.users.get.assert_called_once_with(user.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_user")

    def test_get_role(self):
        role = mock.MagicMock()
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.roles.get = mock.MagicMock(return_value=role)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._get_role(role_id=role.id)

        fake_keystone.roles.get.assert_called_once_with(role.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_role")

    def test_get_service(self):
        service = mock.MagicMock()
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.services.get = mock.MagicMock(return_value=service)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        scenario._get_service(service_id=service.id)

        fake_keystone.services.get.assert_called_once_with(service.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "keystone.get_service")
