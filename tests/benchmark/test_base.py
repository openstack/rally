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

from rally.benchmark import base
from rally import exceptions
from rally import test


class ScenarioTestCase(test.TestCase):

    def test_register(self):
        with mock.patch("rally.benchmark.base.utils") as mock_utils:
            base.Scenario.register()
            base.Scenario.register()

        expected = [
            mock.call.import_modules_from_package("rally.benchmark.scenarios")
        ]
        self.assertEqual(mock_utils.mock_calls, expected)

    def test_get_by_name(self):

        class Scenario1(base.Scenario):
            pass

        class Scenario2(base.Scenario):
            pass

        for s in [Scenario1, Scenario2]:
            self.assertEqual(s, base.Scenario.get_by_name(s.__name__))

    def test_get_by_name_not_found(self):
        self.assertRaises(exceptions.NoSuchScenario,
                          base.Scenario.get_by_name, "non existing scenario")

    def test_class_init(self):

        class FakeClients(object):

            def get_keystone_client(self):
                return "keystone"

            def get_nova_client(self):
                return "nova"

            def get_glance_client(self):
                return "glance"

            def get_cinder_client(self):
                return "cinder"

        with mock.patch('rally.benchmark.base.osclients') as mock_osclients:
            mock_osclients.Clients = mock.MagicMock(return_value=FakeClients())

            admin_keys = ["admin_username", "admin_password",
                          "admin_tenant_name", "uri"]
            temp_keys = ["username", "password", "tenant_name", "uri"]
            kw = dict(zip(admin_keys, admin_keys))
            kw["temp_users"] = [dict(zip(temp_keys, temp_keys))]

            base.Scenario.class_init(kw)
            self.assertEqual(mock_osclients.Clients.mock_calls,
                             [mock.call(*temp_keys)])

            clients = ["keystone", "nova", "glance", "cinder"]
            clients_dict = dict((client, [client]) for client in clients)
            self.assertEqual(base.Scenario.clients, clients_dict)

    def test_init(self):
        self.assertEqual({}, base.Scenario.init(None))

    def test_cleanup(self):
        base.Scenario.cleanup(None)
