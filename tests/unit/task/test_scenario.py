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

import traceback

import mock
import six

from rally import consts
from rally import exceptions
from rally.plugins.common.scenarios.dummy import dummy
from rally.task import context
from rally.task import scenario
from rally.task import validation
from tests.unit import fakes
from tests.unit import test


class ScenarioTestCase(test.TestCase):

    def test_get_by_name(self):
        self.assertEqual(dummy.Dummy, scenario.Scenario.get_by_name("Dummy"))

    def test_get_by_name_not_found(self):
        self.assertRaises(exceptions.NoSuchScenario,
                          scenario.Scenario.get_by_name,
                          "non existing scenario")

    def test_get_scenario_by_name(self):
        scenario_method = scenario.Scenario.get_scenario_by_name("Dummy.dummy")
        self.assertEqual(dummy.Dummy.dummy, scenario_method)

    def test_get_scenario_by_name_shortened(self):
        scenario_method = scenario.Scenario.get_scenario_by_name("dummy")
        self.assertEqual(dummy.Dummy.dummy, scenario_method)

    def test_get_scenario_by_name_shortened_not_found(self):
        self.assertRaises(exceptions.NoSuchScenario,
                          scenario.Scenario.get_scenario_by_name,
                          "dumy")

    def test_get_scenario_by_name_bad_group_name(self):
        self.assertRaises(exceptions.NoSuchScenario,
                          scenario.Scenario.get_scenario_by_name,
                          "Dumy.dummy")

    def test_get_scenario_by_name_bad_scenario_name(self):
        self.assertRaises(exceptions.NoSuchScenario,
                          scenario.Scenario.get_scenario_by_name,
                          "Dummy.dumy")

    def test__validate_helper(self):
        validators = [
            mock.MagicMock(return_value=validation.ValidationResult(True)),
            mock.MagicMock(return_value=validation.ValidationResult(True))
        ]
        clients = mock.MagicMock()
        config = {"a": 1, "b": 2}
        deployment = mock.MagicMock()
        scenario.Scenario._validate_helper(validators, clients, config,
                                           deployment)
        for validator in validators:
            validator.assert_called_with(config, clients=clients,
                                         deployment=deployment)

    def test__validate_helper_somethingwent_wrong(self):
        validator = mock.MagicMock()
        validator.side_effect = Exception()

        self.assertRaises(exceptions.InvalidScenarioArgument,
                          scenario.Scenario._validate_helper,
                          [validator], "cl", "config", "deployment")
        validator.assert_called_once_with("config", clients="cl",
                                          deployment="deployment")

    def test__validate_helper__no_valid(self):
        validators = [
            mock.MagicMock(return_value=validation.ValidationResult(True)),
            mock.MagicMock(
                return_value=validation.ValidationResult(is_valid=False)
            )
        ]
        clients = mock.MagicMock()
        args = {"a": 1, "b": 2}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          scenario.Scenario._validate_helper,
                          validators, clients, args, "fake_uuid")

    @mock.patch("rally.task.scenario.Scenario.get_by_name")
    def test_validate__no_validators(self, mock_scenario_get_by_name):

        class FakeScenario(fakes.FakeScenario):
            pass

        FakeScenario.do_it = mock.MagicMock()
        FakeScenario.do_it.validators = []
        mock_scenario_get_by_name.return_value = FakeScenario

        scenario.Scenario.validate("FakeScenario.do_it", {"a": 1, "b": 2})

        mock_scenario_get_by_name.assert_called_once_with("FakeScenario")

    @mock.patch("rally.task.scenario.Scenario._validate_helper")
    @mock.patch("rally.task.scenario.Scenario.get_by_name")
    def test_validate__admin_validators(self, mock_scenario_get_by_name,
                                        mock_scenario__validate_helper):

        class FakeScenario(fakes.FakeScenario):
            pass

        FakeScenario.do_it = mock.MagicMock()
        mock_scenario_get_by_name.return_value = FakeScenario

        validators = [mock.MagicMock(), mock.MagicMock()]
        for validator in validators:
            validator.permission = consts.EndpointPermission.ADMIN

        FakeScenario.do_it.validators = validators
        deployment = mock.MagicMock()
        args = {"a": 1, "b": 2}
        scenario.Scenario.validate(
            "FakeScenario.do_it", args, admin="admin", deployment=deployment)
        mock_scenario__validate_helper.assert_called_once_with(
            validators, "admin", args, deployment)

    @mock.patch("rally.task.scenario.Scenario._validate_helper")
    @mock.patch("rally.task.scenario.Scenario.get_by_name")
    def test_validate_user_validators(self, mock_scenario_get_by_name,
                                      mock_scenario__validate_helper):

        class FakeScenario(fakes.FakeScenario):
            pass

        FakeScenario.do_it = mock.MagicMock()
        mock_scenario_get_by_name.return_value = FakeScenario

        validators = [mock.MagicMock(), mock.MagicMock()]
        for validator in validators:
            validator.permission = consts.EndpointPermission.USER

        FakeScenario.do_it.validators = validators
        args = {"a": 1, "b": 2}
        scenario.Scenario.validate(
            "FakeScenario.do_it", args, users=["u1", "u2"])

        mock_scenario__validate_helper.assert_has_calls([
            mock.call(validators, "u1", args, None),
            mock.call(validators, "u2", args, None)
        ])

    def test_meta_string_returns_non_empty_list(self):

        class MyFakeScenario(fakes.FakeScenario):
            pass

        attr_name = "preprocessors"
        preprocessors = [mock.MagicMock(), mock.MagicMock()]
        MyFakeScenario.do_it.__dict__[attr_name] = preprocessors

        inst = MyFakeScenario()
        self.assertEqual(inst.meta(cls="MyFakeScenario.do_it",
                                   attr_name=attr_name), preprocessors)

    def test_meta_class_returns_non_empty_list(self):

        class MyFakeScenario(fakes.FakeScenario):
            pass

        attr_name = "preprocessors"
        preprocessors = [mock.MagicMock(), mock.MagicMock()]
        MyFakeScenario.do_it.__dict__[attr_name] = preprocessors

        inst = MyFakeScenario()
        self.assertEqual(inst.meta(cls=fakes.FakeScenario,
                                   method_name="do_it",
                                   attr_name=attr_name), preprocessors)

    def test_meta_string_returns_empty_list(self):
        empty_list = []
        inst = fakes.FakeScenario()
        self.assertEqual(inst.meta(cls="FakeScenario.do_it",
                                   attr_name="foo", default=empty_list),
                         empty_list)

    def test_meta_class_returns_empty_list(self):
        empty_list = []
        inst = fakes.FakeScenario()
        self.assertEqual(inst.meta(cls=fakes.FakeScenario,
                                   method_name="do_it", attr_name="foo",
                                   default=empty_list),
                         empty_list)

    def test_is_scenario_success(self):
        self.assertTrue(scenario.Scenario.is_scenario(dummy.Dummy(), "dummy"))

    def test_is_scenario_not_scenario(self):
        self.assertFalse(scenario.Scenario.is_scenario(dummy.Dummy(),
                                                       "_random_fail_emitter"))

    def test_is_scenario_non_existing(self):
        self.assertFalse(scenario.Scenario.is_scenario(dummy.Dummy(),
                                                       "non_existing"))

    def test_sleep_between_invalid_args(self):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.Scenario().sleep_between, 15, 5)

        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.Scenario().sleep_between, -1, 0)

        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.Scenario().sleep_between, 0, -2)

    def test_sleep_between(self):
        scenario_inst = scenario.Scenario()
        scenario_inst.sleep_between(0.001, 0.002)
        self.assertTrue(0.001 <= scenario_inst.idle_duration() <= 0.002)

    def test_sleep_beetween_multi(self):
        scenario_inst = scenario.Scenario()
        scenario_inst.sleep_between(0.001, 0.001)
        scenario_inst.sleep_between(0.004, 0.004)
        self.assertEqual(scenario_inst.idle_duration(), 0.005)

    @mock.patch("rally.task.scenario.time.sleep")
    @mock.patch("rally.task.scenario.random.uniform")
    def test_sleep_between_internal(self, mock_uniform, mock_sleep):
        scenario_inst = scenario.Scenario()

        mock_uniform.return_value = 1.5
        scenario_inst.sleep_between(1, 2)

        mock_sleep.assert_called_once_with(mock_uniform.return_value)
        self.assertEqual(scenario_inst.idle_duration(),
                         mock_uniform.return_value)

    def test_context(self):
        ctx = mock.MagicMock()
        self.assertEqual(ctx, scenario.Scenario(context=ctx).context)

    def test_scenario_context_are_valid(self):
        scenarios = scenario.Scenario.list_benchmark_scenarios()

        for name in scenarios:
            cls_name, method_name = name.split(".", 1)
            cls = scenario.Scenario.get_by_name(cls_name)
            ctx = getattr(cls, method_name).context
            try:
                context.ContextManager.validate(ctx)
            except Exception:
                print(traceback.format_exc())
                self.assertTrue(False,
                                "Scenario `%s` has wrong context" % scenario)

    def test_RESOURCE_NAME_PREFIX(self):
        self.assertIsInstance(scenario.Scenario.RESOURCE_NAME_PREFIX,
                              six.string_types)

    def test_RESOURCE_NAME_LENGTH(self):
        self.assertIsInstance(scenario.Scenario.RESOURCE_NAME_LENGTH, int)
        self.assertTrue(scenario.Scenario.RESOURCE_NAME_LENGTH > 4)

    def test_generate_random_name(self):
        set_by_length = lambda lst: set(map(len, lst))
        len_by_prefix = (lambda lst, prefix:
                         len([i.startswith(prefix) for i in lst]))
        range_num = 50

        # Defaults
        result = [scenario.Scenario._generate_random_name()
                  for i in range(range_num)]
        self.assertEqual(len(result), len(set(result)))
        self.assertEqual(
            set_by_length(result),
            set([(len(
                scenario.Scenario.RESOURCE_NAME_PREFIX) +
                scenario.Scenario.RESOURCE_NAME_LENGTH)]))
        self.assertEqual(
            len_by_prefix(result, scenario.Scenario.RESOURCE_NAME_PREFIX),
            range_num)

        # Custom prefix
        prefix = "another_prefix_"
        result = [scenario.Scenario._generate_random_name(prefix)
                  for i in range(range_num)]
        self.assertEqual(len(result), len(set(result)))
        self.assertEqual(
            set_by_length(result),
            set([len(prefix) + scenario.Scenario.RESOURCE_NAME_LENGTH]))
        self.assertEqual(
            len_by_prefix(result, prefix), range_num)

        # Custom length
        name_length = 12
        result = [
            scenario.Scenario._generate_random_name(length=name_length)
            for i in range(range_num)]
        self.assertEqual(len(result), len(set(result)))
        self.assertEqual(
            set_by_length(result),
            set([len(
                scenario.Scenario.RESOURCE_NAME_PREFIX) + name_length]))
        self.assertEqual(
            len_by_prefix(result, scenario.Scenario.RESOURCE_NAME_PREFIX),
            range_num)


class AtomicActionTestCase(test.TestCase):
    def test__init__(self):
        fake_scenario_instance = fakes.FakeScenario()
        c = scenario.AtomicAction(fake_scenario_instance, "asdf")
        self.assertEqual(c.scenario_instance, fake_scenario_instance)
        self.assertEqual(c.name, "asdf")

    @mock.patch("tests.unit.fakes.FakeScenario._add_atomic_actions")
    @mock.patch("rally.common.utils.time")
    def test__exit__(self, mock_time, mock_fake_scenario__add_atomic_actions):
        fake_scenario_instance = fakes.FakeScenario()
        self.start = mock_time.time()
        with scenario.AtomicAction(fake_scenario_instance, "asdf"):
            pass
        duration = mock_time.time() - self.start
        mock_fake_scenario__add_atomic_actions.assert_called_once_with(
            "asdf", duration)
