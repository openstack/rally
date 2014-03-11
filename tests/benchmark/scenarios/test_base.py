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

from rally.benchmark.scenarios import base
from rally.benchmark import validation
from rally import consts
from rally import exceptions
from tests import fakes
from tests import test


class ScenarioTestCase(test.TestCase):

    @mock.patch("rally.benchmark.scenarios.base.utils")
    def test_register(self, mock_utils):
        base.Scenario.registred = False
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

    def test__validate_helper(self):
        validators = [
            mock.MagicMock(return_value=validation.ValidationResult()),
            mock.MagicMock(return_value=validation.ValidationResult())
        ]
        clients = mock.MagicMock()
        args = {"a": 1, "b": 2}
        base.Scenario._validate_helper(validators, clients, args)
        for validator in validators:
            validator.assert_called_with(clients=clients, **args)

    def test__validate_helper__no_valid(self):
        validators = [
            mock.MagicMock(return_value=validation.ValidationResult()),
            mock.MagicMock(
                return_value=validation.ValidationResult(is_valid=False)
            )
        ]
        clients = mock.MagicMock()
        args = {"a": 1, "b": 2}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          base.Scenario._validate_helper,
                          validators, clients, args)

    @mock.patch("rally.benchmark.scenarios.base.Scenario.get_by_name")
    def test_validate__no_validators(self, mock_base_get_by_name):

        class FakeScenario(fakes.FakeScenario):
            pass

        FakeScenario.do_it = mock.MagicMock()
        FakeScenario.do_it.validators = []
        mock_base_get_by_name.return_value = FakeScenario

        base.Scenario.validate("FakeScenario.do_it", {"a": 1, "b": 2})

        mock_base_get_by_name.assert_called_once_with("FakeScenario")

    @mock.patch("rally.benchmark.scenarios.base.Scenario._validate_helper")
    @mock.patch("rally.benchmark.scenarios.base.Scenario.get_by_name")
    def test_validate__admin_validators(self, mock_base_get_by_name,
                                        mock_validate_helper):

        class FakeScenario(fakes.FakeScenario):
            pass

        FakeScenario.do_it = mock.MagicMock()
        mock_base_get_by_name.return_value = FakeScenario

        validators = [mock.MagicMock(), mock.MagicMock()]
        for validator in validators:
            validator.permission = consts.EndpointPermission.ADMIN

        FakeScenario.do_it.validators = validators
        args = {"a": 1, "b": 2}
        base.Scenario.validate("FakeScenario.do_it", args, admin="admin")
        mock_validate_helper.assert_called_once_with(validators, "admin", args)

    @mock.patch("rally.benchmark.scenarios.base.Scenario._validate_helper")
    @mock.patch("rally.benchmark.scenarios.base.Scenario.get_by_name")
    def test_validate_user_validators(self, mock_base_get_by_name,
                                      mock_validate_helper):

        class FakeScenario(fakes.FakeScenario):
            pass

        FakeScenario.do_it = mock.MagicMock()
        mock_base_get_by_name.return_value = FakeScenario

        validators = [mock.MagicMock(), mock.MagicMock()]
        for validator in validators:
            validator.permission = consts.EndpointPermission.USER

        FakeScenario.do_it.validators = validators
        args = {"a": 1, "b": 2}
        base.Scenario.validate("FakeScenario.do_it", args, users=["u1", "u2"])

        mock_validate_helper.assert_has_calls([
            mock.call(validators, "u1", args),
            mock.call(validators, "u2", args)
        ])

    @mock.patch("rally.benchmark.scenarios.base.time.sleep")
    @mock.patch("rally.benchmark.scenarios.base.random.uniform")
    def test_sleep_between(self, mock_uniform, mock_sleep):
        scenario = base.Scenario()

        mock_uniform.return_value = 10
        scenario.sleep_between(5, 15)
        scenario.sleep_between(10, 10)

        expected = [mock.call(5, 15), mock.call(10, 10)]
        self.assertEqual(mock_uniform.mock_calls, expected)
        expected = [mock.call(10), mock.call(10)]
        self.assertEqual(mock_sleep.mock_calls, expected)

        self.assertEqual(scenario.idle_time(), 20)
        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.sleep_between, 15, 5)
        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.sleep_between, -1, 0)
        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.sleep_between, 0, -2)

    def test_context(self):
        context = mock.MagicMock()
        scenario = base.Scenario(context=context)
        self.assertEqual(context, scenario.context())

    def test_clients(self):
        clients = fakes.FakeClients()

        scenario = base.Scenario(clients=clients)
        self.assertEqual(clients.nova(), scenario.clients("nova"))
        self.assertEqual(clients.glance(), scenario.clients("glance"))

    def test_admin_clients(self):
        clients = fakes.FakeClients()

        scenario = base.Scenario(admin_clients=clients)
        self.assertEqual(clients.nova(), scenario.admin_clients("nova"))
        self.assertEqual(clients.glance(), scenario.admin_clients("glance"))
