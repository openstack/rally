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

from rally.benchmark.scenarios.keystone import utils
from tests.benchmark.scenarios import test_utils
from tests import test

from tests import fakes


UTILS = "rally.benchmark.scenarios.keystone.utils."


class KeystoneUtilsTestCase(test.TestCase):

    @mock.patch(UTILS + "random.choice")
    def test_generate_keystone_name(self, mock_random_choice):
        mock_random_choice.return_value = "a"

        for length in [10, 20]:
            result = utils.generate_keystone_name(length)
            self.assertEqual(result, utils.TEMP_TEMPLATE + "a" * length)

    def test_is_temporary(self):
        tests = [
            (fakes.FakeResource(name=utils.TEMP_TEMPLATE + "abc"), True),
            (fakes.FakeResource(name="fdaffdafa"), False),
            (fakes.FakeResource(name=utils.TEMP_TEMPLATE[:-3] + "agag"), False)
        ]

        for resource, is_valid in tests:
            self.assertEqual(utils.is_temporary(resource), is_valid)


class KeystoneScenarioTestCase(test.TestCase):

    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions_time, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(UTILS + "generate_keystone_name")
    def test_user_create(self, mock_gen_name):
        name = "abc"
        mock_gen_name.return_value = name

        user = {}
        fake_keystone = fakes.FakeKeystoneClient()
        fake_keystone.users.create = mock.MagicMock(return_value=user)
        fake_clients = fakes.FakeClients()
        fake_clients._keystone = fake_keystone
        scenario = utils.KeystoneScenario(admin_clients=fake_clients)

        result = scenario._user_create()

        self.assertEqual(user, result)
        fake_keystone.users.create.assert_called_once_with(name, name,
                                                           name + "@rally.me")
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'keystone.create_user')

    def test_user_delete(self):
        resource = fakes.FakeResource()
        resource.delete = mock.MagicMock()

        scenario = utils.KeystoneScenario()
        scenario._resource_delete(resource)
        resource.delete.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'keystone.delete_resource')

    @mock.patch(UTILS + "generate_keystone_name")
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
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'keystone.create_tenant')
