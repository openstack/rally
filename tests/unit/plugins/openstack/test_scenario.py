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
from oslotest import mockpatch

from rally.plugins.openstack import scenario as base_scenario
from tests.unit import test


class OpenStackScenarioTestCase(test.TestCase):
    def setUp(self):
        super(OpenStackScenarioTestCase, self).setUp()
        self.osclients = mockpatch.Patch(
            "rally.osclients.Clients")
        self.useFixture(self.osclients)
        self.context = test.get_test_context()
        self.context.update({"foo": "bar"})

    def test_init(self):
        scenario = base_scenario.OpenStackScenario(self.context)
        self.assertEqual(self.context, scenario.context)

    def test_init_admin_context(self):
        self.context["admin"] = {"credential": mock.Mock()}
        scenario = base_scenario.OpenStackScenario(self.context)
        self.assertEqual(self.context, scenario.context)
        self.osclients.mock.assert_called_once_with(
            self.context["admin"]["credential"], {})

        self.assertRaises(
            ValueError, base_scenario.OpenStackScenario,
            self.context, admin_clients="foobar")

    def test_init_admin_clients(self):
        scenario = base_scenario.OpenStackScenario(
            self.context, admin_clients="foobar")
        self.assertEqual(self.context, scenario.context)

        self.assertEqual("foobar", scenario._admin_clients)

    def test_init_user_context(self):
        self.context["user"] = {"credential": mock.Mock()}
        scenario = base_scenario.OpenStackScenario(self.context)
        self.assertEqual(self.context, scenario.context)
        self.osclients.mock.assert_called_once_with(
            self.context["user"]["credential"], {})

        self.assertRaises(
            ValueError, base_scenario.OpenStackScenario,
            self.context, clients="foobar")

    def test_init_user_clients(self):
        scenario = base_scenario.OpenStackScenario(
            self.context, clients="foobar")
        self.assertEqual(self.context, scenario.context)

        self.assertEqual("foobar", scenario._clients)
