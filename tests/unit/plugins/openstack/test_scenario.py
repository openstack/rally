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
from oslotest import mockpatch

from rally.plugins.openstack import scenario as base_scenario
from tests.unit import test


@ddt.ddt
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

        scenario = base_scenario.OpenStackScenario(
            self.context, admin_clients="foobar")

    def test_init_admin_clients(self):
        scenario = base_scenario.OpenStackScenario(
            self.context, admin_clients="foobar")
        self.assertEqual(self.context, scenario.context)

        self.assertEqual("foobar", scenario._admin_clients)

    def test_init_user_context(self):
        user = {"credential": mock.Mock(), "tenant_id": "foo"}
        self.context["users"] = [user]
        self.context["tenants"] = {"foo": {"name": "bar"}}
        self.context["user_choice_method"] = "random"

        scenario = base_scenario.OpenStackScenario(self.context)

        self.assertEqual(user, scenario.context["user"])
        self.assertEqual(self.context["tenants"]["foo"],
                         scenario.context["tenant"])

        self.osclients.mock.assert_called_once_with(user["credential"], {})

    def test_init_clients(self):
        scenario = base_scenario.OpenStackScenario(self.context,
                                                   admin_clients="spam",
                                                   clients="ham")
        self.assertEqual("spam", scenario._admin_clients)
        self.assertEqual("ham", scenario._clients)

    def test_init_user_clients(self):
        scenario = base_scenario.OpenStackScenario(
            self.context, clients="foobar")
        self.assertEqual(self.context, scenario.context)

        self.assertEqual("foobar", scenario._clients)

    def test__choose_user_random(self):
        users = [{"credential": mock.Mock(), "tenant_id": "foo"}
                 for _ in range(5)]
        self.context["users"] = users
        self.context["tenants"] = {"foo": {"name": "bar"},
                                   "baz": {"name": "spam"}}
        self.context["user_choice_method"] = "random"

        scenario = base_scenario.OpenStackScenario()
        scenario._choose_user(self.context)
        self.assertIn("user", self.context)
        self.assertIn(self.context["user"], self.context["users"])
        self.assertIn("tenant", self.context)
        tenant_id = self.context["user"]["tenant_id"]
        self.assertEqual(self.context["tenants"][tenant_id],
                         self.context["tenant"])

    @ddt.data((1, "0", "bar"),
              (2, "0", "foo"),
              (3, "1", "bar"),
              (4, "1", "foo"),
              (5, "0", "bar"),
              (6, "0", "foo"),
              (7, "1", "bar"),
              (8, "1", "foo"))
    @ddt.unpack
    def test__choose_user_round_robin(self, iteration,
                                      expected_user_id, expected_tenant_id):
        self.context["iteration"] = iteration
        self.context["user_choice_method"] = "round_robin"
        self.context["users"] = []
        self.context["tenants"] = {}
        for tid in ("foo", "bar"):
            users = [{"id": str(i), "tenant_id": tid} for i in range(2)]
            self.context["users"] += users
            self.context["tenants"][tid] = {"name": tid, "users": users}

        scenario = base_scenario.OpenStackScenario()
        scenario._choose_user(self.context)
        self.assertIn("user", self.context)
        self.assertIn(self.context["user"], self.context["users"])
        self.assertEqual(expected_user_id, self.context["user"]["id"])
        self.assertIn("tenant", self.context)
        tenant_id = self.context["user"]["tenant_id"]
        self.assertEqual(self.context["tenants"][tenant_id],
                         self.context["tenant"])
        self.assertEqual(expected_tenant_id, tenant_id)
