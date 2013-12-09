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
        base.Scenario.registred = False
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

    def test_init(self):
        self.assertEqual({}, base.Scenario.init(None))

    def test_cleanup(self):
        base.Scenario.cleanup()

    def test_sleep_between(self):
        base.Scenario.idle_time = 0
        with mock.patch("rally.benchmark.base.random.uniform") as mock_uniform:
            mock_uniform.return_value = 10
            with mock.patch("rally.benchmark.base.time.sleep") as mock_sleep:
                base.Scenario.sleep_between(5, 15)
                base.Scenario.sleep_between(10, 10)
        expected = [
            mock.call(5, 15),
            mock.call(10, 10),
        ]
        self.assertEqual(mock_uniform.mock_calls, expected)
        expected = [
            mock.call(10),
            mock.call(10)
        ]
        self.assertEqual(mock_sleep.mock_calls, expected)
        self.assertEqual(base.Scenario.idle_time, 20)
        self.assertRaises(exceptions.InvalidArgumentsException,
                          base.Scenario.sleep_between, 15, 5)
        self.assertRaises(exceptions.InvalidArgumentsException,
                          base.Scenario.sleep_between, -1, 0)
        self.assertRaises(exceptions.InvalidArgumentsException,
                          base.Scenario.sleep_between, 0, -2)

    def test_context(self):

        context = {"test": "context"}

        class Scenario(base.Scenario):
            @classmethod
            def init(cls, config):
                return context

        Scenario._context = Scenario.init({})
        self.assertEqual(context, Scenario.context())

    def test_clients(self):

        nova_client = object()
        glance_client = object()
        clients = {"nova": nova_client, "glance": glance_client}

        class Scenario(base.Scenario):
            pass

        Scenario._clients = clients
        self.assertEqual(nova_client, Scenario.clients("nova"))
        self.assertEqual(glance_client, Scenario.clients("glance"))

    def test_admin_clients(self):

        nova_client = object()
        glance_client = object()
        clients = {"nova": nova_client, "glance": glance_client}

        class Scenario(base.Scenario):
            pass

        Scenario._admin_clients = clients
        self.assertEqual(nova_client, Scenario.admin_clients("nova"))
        self.assertEqual(glance_client, Scenario.admin_clients("glance"))
