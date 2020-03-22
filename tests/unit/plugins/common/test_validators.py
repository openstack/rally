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

import os
from unittest import mock

import ddt

from rally.common.plugin import plugin
from rally.common import validation
from rally.plugins.common import validators
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
        self.assertIn("10 is not of type 'string'", result[0])

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
            pass

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
            self.assertIn(err_msg, result[0])

        DummyPlugin.unregister()


@ddt.ddt
class RequiredParameterValidatorTestCase(test.TestCase):

    @ddt.data(({"args": {"a": 10, "b": 20}}, "a"),
              ({"args": {"a": 10, "b": {"c": 20}}}, [("b", "c")]),
              ({"args": {"a": 10, "c": 20}}, [("b", "c")]))
    @ddt.unpack
    def test_validate(self, config, params):
        validator = validators.RequiredParameterValidator(params)

        self.assertIsNone(validator.validate(None, config, None, None))

    @ddt.data(({"args": {"a": 10, "b": 20}}, "c",
               "'c' parameter(s) are not defined in the input task file"),
              ({"args": {"a": 10}}, [("b", "c")],
               "'b'/'c' (at least one parameter should be specified) "
               "parameter(s) are not defined in the input task file"))
    @ddt.unpack
    def test_validate_failed(self, config, params, err_msg):
        validator = validators.RequiredParameterValidator(params)

        e = self.assertRaises(validation.ValidationError,
                              validator.validate, None, config, None, None)
        self.assertEqual(err_msg, e.message)


class NumberValidatorTestCase(test.TestCase):

    @staticmethod
    def get_validator(minval=None, maxval=None, nullable=False,
                      integer_only=False):
        validator_cls = validation.Validator.get("number")
        return validator_cls("foo", minval=minval, maxval=maxval,
                             nullable=nullable, integer_only=integer_only)

    def test_number_not_nullable(self):
        e = self.assertRaises(
            validation.ValidationError,
            self.get_validator().validate, {}, {}, None, None)
        self.assertEqual("foo is None which is not a valid float", e.message)

    def test_number_nullable(self):
        self.assertIsNone(self.get_validator(nullable=True).validate(
            {}, {}, None, None))

    def test_number_min_max_value(self):
        validator = self.get_validator(minval=4, maxval=10)

        e = self.assertRaises(
            validation.ValidationError, validator.validate,
            {}, {"args": {validator.param_name: 3.9}}, None, None)
        self.assertEqual("foo is 3.9 which is less than the minimum (4)",
                         e.message)

        validator.validate({}, {"args": {validator.param_name: 4.1}},
                           None, None)
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, {}, {"args": {validator.param_name: 11}},
            None, None)
        self.assertEqual("foo is 11.0 which is greater than the maximum (10)",
                         e.message)

    def test_number_integer_only(self):
        validator = self.get_validator(integer_only=True)

        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, {}, {"args": {validator.param_name: 3.9}},
            None, None)
        self.assertEqual("foo is 3.9 which hasn't int type", e.message)

        validator.validate({}, {"args": {validator.param_name: 3}}, None, None)


class EnumValidatorTestCase(test.TestCase):

    @staticmethod
    def get_validator(values, missed=False, case_insensitive=False):
        validator_cls = validation.Validator.get("enum")
        return validator_cls("foo", values=values, missed=missed,
                             case_insensitive=case_insensitive)

    def test_param_defined(self):
        validator = self.get_validator(values=["a", "b"])

        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, {}, {"args": {}}, None, None)
        self.assertEqual("foo parameter is not defined in the task "
                         "config file", e.message)

    def test_right_value(self):
        validator = self.get_validator(values=["a", "b"])
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, {}, {"args": {validator.param_name: "c"}},
            None, None)
        self.assertEqual("foo is c which is not a valid value from ['a', 'b']",
                         e.message)

    def test_case_insensitive(self):
        validator = self.get_validator(values=["A", "B"],
                                       case_insensitive=True)

        validator.validate(
            {}, {"args": {validator.param_name: "a"}}, None, None)

        e = self.assertRaises(
            validation.ValidationError,
            validator.validate,
            {}, {"args": {validator.param_name: "C"}}, None, None)

        self.assertEqual("foo is c which is not a valid value from ['a', 'b']",
                         e.message)


@ddt.ddt
class RestrictedParametersValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RestrictedParametersValidatorTestCase, self).setUp()
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()]})

    @ddt.data(
        {"config": {"args": {}}},
        {"config": {"args": {"subdict": {}}}, "subdict": "subdict"}
    )
    @ddt.unpack
    def test_validate(self, config, subdict=None):
        validator = validators.RestrictedParametersValidator(
            ["param_name"], subdict)
        validator.validate(self.credentials, config, None, None)

    @ddt.data(
        {"config": {"args": {"param_name": "value"}},
         "err_msg": "You can't specify parameters 'param_name' in 'args'"},
        {"config": {"args": {"subdict": {"param_name": "value"}}},
         "subdict": "subdict",
         "err_msg": "You can't specify parameters 'param_name' in 'subdict'"}
    )
    @ddt.unpack
    def test_validate_failed(self, config, subdict=None, err_msg=None):
        validator = validators.RestrictedParametersValidator(
            ["param_name"], subdict)
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, self.credentials, config, None, None)
        self.assertEqual(err_msg, e.message)

    def test_restricted_parameters_string_param_names(self):
        validator = validators.RestrictedParametersValidator("param_name")
        validator.validate(self.credentials, {"args": {}}, None, None)


@ddt.ddt
class RequiredContextsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredContextsValidatorTestCase, self).setUp()
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()], })

    @ddt.data(
        {"config": {"contexts": {"c1": 1, "c2": 2, "c3": 3}}},
        {"config": {"contexts": {"c1": 1, "c2": 2, "c3": 3, "a": 1}}}
    )
    @ddt.unpack
    def test_validate(self, config):
        validator = validators.RequiredContextsValidator(
            contexts=("c1", "c2", "c3"))
        validator.validate(self.credentials, config, None, None)

    def test_validate_failed(self):
        validator = validators.RequiredContextsValidator(
            contexts=("c1", "c2", "c3"))
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, self.credentials, {"contexts": {"a": 1}},
            None, None)
        self.assertEqual(
            "The following context(s) are required but missing from "
            "the input task file: c1, c2, c3", e.message)

    @ddt.data(
        {"config": {
            "contexts": {"c1": 1, "c2": 2, "c3": 3,
                         "b1": 1, "a1": 1}}},
        {"config": {
            "contexts": {"c1": 1, "c2": 2, "c3": 3,
                         "b1": 1, "b2": 2, "a1": 1}}},
    )
    @ddt.unpack
    def test_validate_with_or(self, config):
        validator = validators.RequiredContextsValidator(
            contexts=[("a1", "a2"), "c1", ("b1", "b2"), "c2"])
        validator.validate(self.credentials, config, None, None)

    def test_validate_with_or_failed(self):
        validator = validators.RequiredContextsValidator(
            contexts=[("a1", "a2"), "c1", ("b1", "b2"), "c2"])
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, self.credentials,
            {"contexts": {"c1": 1, "c2": 2}}, None, None)
        self.assertEqual(
            "The following context(s) are required but missing "
            "from the input task file: 'a1 or a2', 'b1 or b2'", e.message)


@ddt.ddt
class RequiredParamOrContextValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredParamOrContextValidatorTestCase, self).setUp()
        self.validator = validators.RequiredParamOrContextValidator(
            "image", "custom_image")
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()], })

    @ddt.data(
        {"config": {"args": {"image": {"name": ""}},
                    "contexts": {"custom_image": {"name": "fake_image"}}}},
        {"config": {"contexts": {"custom_image": {"name": "fake_image"}}}},
        {"config": {"args": {"image": {"name": "fake_image"}},
                    "contexts": {"custom_image": ""}}},
        {"config": {"args": {"image": {"name": "fake_image"}}}},
        {"config": {"args": {"image": {"name": ""}},
                    "contexts": {"custom_image": {"name": ""}}}}
    )
    @ddt.unpack
    def test_validate(self, config):
        self.validator.validate(self.credentials, config, None, None)

    @ddt.data(
        {"config": {"args": {}, "contexts": {}},
         "err_msg": "You should specify either scenario argument image or "
                    "use context custom_image."},
        {"config": {},
         "err_msg": "You should specify either scenario argument image or "
                    "use context custom_image."}
    )
    @ddt.unpack
    def test_validate_failed(self, config, err_msg):
        e = self.assertRaises(
            validation.ValidationError,
            self.validator.validate, self.credentials, config, None, None)
        self.assertEqual(err_msg, e.message)


class FileExistsValidatorTestCase(test.TestCase):

    @mock.patch("rally.plugins.common.validators."
                "FileExistsValidator._file_access_ok")
    def test_file_exists(self, mock__file_access_ok):
        validator = validators.FileExistsValidator("p", required=False)
        validator.validate({}, {"args": {"p": "test_file"}}, None, None)
        mock__file_access_ok.assert_called_once_with(
            "test_file", os.R_OK, "p", False)


class MapKeysParameterValidatorTestCase(test.TestCase):
    def test_validate_required(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            required=["test1", "test2", "test3"]
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": "",
                                                           "test3": "",
                                                           "test4": ""}}},
                               None, None))
        msg = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": ""}}},
            None, None
        )
        self.assertEqual("Required keys is missing in 'testarg' parameter: "
                         "test2, test3", str(msg))

        msg = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {}, None, None
        )
        self.assertEqual("'testarg' parameter is not defined in "
                         "the task config file", str(msg))

    def test_validate_allowed(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            required=["test1", "test2"],
            allowed=["test1", "test2", "test3"]
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": "",
                                                           "test3": ""}}},
                               None, None)
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": ""}}},
                               None, None)
        )
        ex = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": "",
                                                            "test2": "",
                                                            "test3": "",
                                                            "test4": ""}}},
            None, None)
        self.assertEqual("Parameter 'testarg' contains unallowed keys: test4",
                         str(ex))

    def test_validate_additional(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            required=["test1", "test2"],
            additional=False
        )
        ex = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": "",
                                                            "test2": "",
                                                            "test3": "",
                                                            "test4": ""}}},
            None, None)
        self.assertEqual("Parameter 'testarg' contains unallowed keys: test3, "
                         "test4", str(ex))

    def test_validate_none_required(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            allowed=["test1", "test2"]
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": ""}}},
                               None, None)
        )
        ex = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": "",
                                                            "test2": "",
                                                            "test3": "",
                                                            "test4": ""}}},
            None, None)
        self.assertEqual("Parameter 'testarg' contains unallowed keys: test3, "
                         "test4", str(ex))
