# Copyright 2017: Mirantis Inc.
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

from rally.common.plugin import plugin
from rally.common import validation
from rally.plugins.common import validators
from rally.task import scenario
from tests.unit import test


class JsonSchemaValidatorTestCase(test.TestCase):

    def test_validate(self):
        @plugin.base()
        class DummyPluginBase(plugin.Plugin,
                              validation.ValidatablePluginMixin):
            pass

        @validation.add(name="jsonschema")
        @plugin.configure(name="dummy_plugin")
        class DummyPlugin(DummyPluginBase):
            CONFIG_SCHEMA = {"type": "string"}

        result = DummyPluginBase.validate("dummy_plugin", None, {}, "foo")
        self.assertEqual(0, len(result))

        result = DummyPluginBase.validate("dummy_plugin", None, {}, 10)
        self.assertEqual(1, len(result))
        self.assertFalse(result[0].is_valid)
        self.assertIsNone(result[0].etype)
        self.assertIn("10 is not of type 'string'", result[0].msg)

        DummyPlugin.unregister()


@ddt.ddt
class ArgsValidatorTestCase(test.TestCase):

    @ddt.data(({"args": {"a": 10, "b": 20}}, None),
              ({"args": {"a": 10, "b": 20, "c": 30}}, None),
              ({}, "Argument(s) 'a', 'b' should be specified"),
              ({"args": {"foo": 1}},
               "Argument(s) 'a', 'b' should be specified"),
              ({"args": {"a": 1}}, "Argument(s) 'b' should be specified"),
              ({"args": {"a": 1, "b": 1, "foo": 2}},
               "Unexpected argument(s) found ['foo']."))
    @ddt.unpack
    def test_validate(self, config, err_msg):
        @plugin.base()
        class DummyPluginBase(plugin.Plugin,
                              validation.ValidatablePluginMixin):
            is_classbased = True

        @validation.add(name="args-spec")
        @plugin.configure(name="dummy_plugin")
        class DummyPlugin(DummyPluginBase):
            def run(self, a, b, c="spam"):
                pass

        result = DummyPluginBase.validate("dummy_plugin", None, config, None)
        if err_msg is None:
            self.assertEqual(0, len(result))
        else:
            self.assertEqual(1, len(result))
            self.assertFalse(result[0].is_valid)
            self.assertIn(err_msg, result[0].msg)

        DummyPlugin.unregister()

        class DummyPlugin2(DummyPluginBase):
            @scenario.configure(name="dummy_plugin.func_based")
            def func_based(self, a, b, c="spam"):
                pass

        result = scenario.Scenario.validate(
            "dummy_plugin.func_based", None, config, None)

        if err_msg is None:
            self.assertEqual(0, len(result))
        else:
            self.assertEqual(1, len(result))
            self.assertFalse(result[0].is_valid)
            self.assertIn(err_msg, result[0].msg)

        DummyPlugin2.func_based.unregister()


@ddt.ddt
class RequiredParameterValidatorTestCase(test.TestCase):

    @ddt.data(({"args": {"a": 10, "b": 20}}, "a", None, None),
              ({"args": {"a": 10, "b": 20}}, "c", None,
               "c parameters are not defined in the benchmark config file"),
              ({"args": {"a": 10, "b": {"c": 20}}}, [("b", "c")],
               None, None),
              ({"args": {"a": 10, "c": 20}}, [("b", "c")],
               None, None),
              ({"args": {"a": 10}}, [("b", "c")], None,
               "c parameters are not defined in the benchmark config file"))
    @ddt.unpack
    def test_validate(self, config, params, subdict, err_msg):
        validator = validators.RequiredParameterValidator(params, subdict)
        result = validator.validate(None, config, None, None)
        if err_msg:
            self.assertEqual(err_msg, result.msg)
        else:
            self.assertIsNone(result)


class NumberValidatorTestCase(test.TestCase):

    @staticmethod
    def get_validator(minval=None, maxval=None, nullable=False,
                      integer_only=False):
        validator_cls = validation.Validator.get("number")
        return validator_cls("foo", minval=minval, maxval=maxval,
                             nullable=nullable, integer_only=integer_only)

    def test_number_not_nullable(self):
        result = self.get_validator().validate({}, {}, None, None)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)
        self.assertEqual("foo is None which is not a valid float",
                         "%s" % result)

    def test_number_nullable(self):
        self.assertIsNone(self.get_validator(nullable=True).validate(
            {}, {}, None, None))

    def test_number_min_max_value(self):
        validator = self.get_validator(minval=4, maxval=10)

        result = validator.validate({}, {"args": {validator.param_name: 3.9}},
                                    None, None)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)
        self.assertEqual("foo is 3.9 which is less than the minimum (4)",
                         "%s" % result)

        result = validator.validate({}, {"args": {validator.param_name: 4.1}},
                                    None, None)
        self.assertIsNone(result)

        result = validator.validate({}, {"args": {validator.param_name: 11}},
                                    None, None)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)
        self.assertEqual("foo is 11.0 which is greater than the maximum (10)",
                         "%s" % result)

    def test_number_integer_only(self):
        validator = self.get_validator(integer_only=True)

        result = validator.validate({}, {"args": {validator.param_name: 3.9}},
                                    None, None)
        self.assertFalse(result.is_valid, result.msg)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)
        self.assertEqual("foo is 3.9 which hasn't int type", "%s" % result)

        result = validator.validate({}, {"args": {validator.param_name: 3}},
                                    None, None)
        self.assertIsNone(result)
