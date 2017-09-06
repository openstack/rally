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
import os
import shutil
import tempfile

import rally
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
            self.assertFalse(result[0].is_valid)
            self.assertIn(err_msg, result[0].msg)

        DummyPlugin.unregister()


@ddt.ddt
class RequiredParameterValidatorTestCase(test.TestCase):

    @ddt.data(({"args": {"a": 10, "b": 20}}, "a", None, None),
              ({"args": {"a": 10, "b": 20}}, "c", None,
               "'c' parameter(s) are not defined in the input task file"),
              ({"args": {"a": 10, "b": {"c": 20}}}, [("b", "c")],
               None, None),
              ({"args": {"a": 10, "c": 20}}, [("b", "c")],
               None, None),
              ({"args": {"a": 10}}, [("b", "c")], None,
               "'b'/'c' (at least one parameter should be specified) "
               "parameter(s) are not defined in the input task file"))
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


class EnumValidatorTestCase(test.TestCase):

    @staticmethod
    def get_validator(values, missed=False, case_insensitive=False):
        validator_cls = validation.Validator.get("enum")
        return validator_cls("foo", values=values, missed=missed,
                             case_insensitive=case_insensitive)

    def test_param_defined(self):
        validator = self.get_validator(values=["a", "b"])
        result = validator.validate({}, {"args": {}}, None, None)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)
        self.assertEqual("foo parameter is not defined in the task "
                         "config file", "%s" % result)

    def test_right_value(self):
        validator = self.get_validator(values=["a", "b"])
        result = validator.validate({}, {"args": {validator.param_name: "c"}},
                                    None, None)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)
        self.assertEqual("foo is c which is not a valid value from ['a', 'b']",
                         "%s" % result)

    def test_case_insensitive(self):
        validator = self.get_validator(values=["A", "B"],
                                       case_insensitive=True)

        good_result = validator.validate(
            {}, {"args": {validator.param_name: "a"}}, None, None
        )
        bad_result = validator.validate(
            {}, {"args": {validator.param_name: "C"}}, None, None
        )

        self.assertIsNone(good_result)

        self.assertIsNotNone(bad_result)
        self.assertFalse(bad_result.is_valid)
        self.assertEqual("foo is c which is not a valid value from ['a', 'b']",
                         "%s" % bad_result)


@ddt.ddt
class RestrictedParametersValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RestrictedParametersValidatorTestCase, self).setUp()
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()]})

    @ddt.unpack
    @ddt.data(
        {"context": {"args": {}}},
        {"context": {"args": {"param_name": "value"}},
         "err_msg": "You can't specify parameters 'param_name' in 'args'"},
        {"context": {"args": {"subdict": {}}}, "subdict": "subdict"},
        {"context": {"args": {"subdict": {"param_name": "value"}}},
         "subdict": "subdict",
         "err_msg": "You can't specify parameters 'param_name' in 'subdict'"}
    )
    def test_validate(self, context, subdict=None, err_msg=None):
        validator = validators.RestrictedParametersValidator(
            ["param_name"], subdict)
        result = validator.validate(context, self.credentials, None, None)

        if err_msg:
            self.assertIsNotNone(result)
            self.assertEqual(err_msg, result.msg)
        else:
            self.assertIsNone(result)

    def test_restricted_parameters_string_param_names(self):
        validator = validators.RestrictedParametersValidator("param_name")
        result = validator.validate({"args": {}}, self.credentials, None, None)
        self.assertIsNone(result)


@ddt.ddt
class RequiredContextsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredContextsValidatorTestCase, self).setUp()
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()], })

    @ddt.unpack
    @ddt.data(
        {"config": {"context": {"a": 1}},
         "err_msg": "The following context(s) are required but missing from "
                    "the input task file: c1, c2, c3"},
        {"config": {"context": {"c1": 1, "c2": 2, "c3": 3}}},
        {"config": {"context": {"c1": 1, "c2": 2, "c3": 3, "a": 1}}}
    )
    def test_validate(self, config, err_msg=False):
        validator = validators.RequiredContextsValidator(
            contexts=("c1", "c2", "c3"))
        result = validator.validate(config, self.credentials, None, None)
        if err_msg:
            self.assertIsNotNone(result)
            self.assertEqual(err_msg, result.msg)
        else:
            self.assertIsNone(result)

    @ddt.unpack
    @ddt.data(
        {"config": {"context": {"c1": 1, "c2": 2}},
         "err_msg": "The following context(s) are required but missing "
                    "from the input task file: 'a1 or a2', 'b1 or b2'"},
        {"config": {"context": {"c1": 1, "c2": 2, "c3": 3, "b1": 1, "a1": 1}}},
        {"config": {"context": {"c1": 1, "c2": 2, "c3": 3,
                                "b1": 1, "b2": 2, "a1": 1}}},
    )
    def test_validate_with_or(self, config, err_msg=None):
        validator = validators.RequiredContextsValidator(
            contexts=[("a1", "a2"), "c1", ("b1", "b2"), "c2"])
        result = validator.validate(config, self.credentials, None, None)

        if err_msg:
            self.assertIsNotNone(result)
            self.assertEqual(err_msg, result.msg)
        else:
            self.assertIsNone(result)


@ddt.ddt
class RequiredParamOrContextValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredParamOrContextValidatorTestCase, self).setUp()
        self.validator = validators.RequiredParamOrContextValidator(
            "image", "custom_image")
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()], })

    @ddt.unpack
    @ddt.data(
        {"config": {"args": {"image": {"name": ""}},
                    "context": {"custom_image": {"name": "fake_image"}}}},
        {"config": {"context": {"custom_image": {"name": "fake_image"}}}},
        {"config": {"args": {"image": {"name": "fake_image"}},
                    "context": {"custom_image": ""}}},
        {"config": {"args": {"image": {"name": "fake_image"}}}},
        {"config": {"args": {"image": {"name": ""}},
                    "context": {"custom_image": {"name": ""}}}},
        {"config": {"args": {}, "context": {}},
         "err_msg": "You should specify either scenario argument image or "
                    "use context custom_image."},
        {"config": {},
         "err_msg": "You should specify either scenario argument image or "
                    "use context custom_image."}
    )
    def test_validate(self, config, err_msg=False):
        result = self.validator.validate(config, self.credentials, None, None)

        if err_msg:
            self.assertIsNotNone(result)
            self.assertEqual(err_msg, result.msg)
        else:
            self.assertIsNone(result)


class FileExistsValidatorTestCase(test.TestCase):
    rally_jobs_path = os.path.join(
        os.path.dirname(rally.__file__), "..", "rally-jobs")

    def setUp(self):
        super(FileExistsValidatorTestCase, self).setUp()
        self.validator = validators.FileExistsValidator(param_name="p",
                                                        required=False)
        self.credentials = dict(openstack={"admin": mock.MagicMock(),
                                           "users": [mock.MagicMock()], })
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp_dir, ".rally"))
        shutil.copytree(os.path.join(self.rally_jobs_path, "extra"),
                        os.path.join(self.tmp_dir, ".rally", "extra"))

        self.original_home = os.environ["HOME"]
        os.environ["HOME"] = self.tmp_dir

        def return_home():
            os.environ["HOME"] = self.original_home
        self.addCleanup(shutil.rmtree, self.tmp_dir)

        self.addCleanup(return_home)

    @mock.patch("rally.plugins.common.validators."
                "ValidatorUtils._file_access_ok")
    def test_file_exists(self, mock__file_access_ok):
        mock__file_access_ok.return_value = "foobar"
        result = self.validator.validate({"args": {"p": "test_file"}},
                                         self.credentials, None, None)
        self.assertEqual("foobar", result)
        mock__file_access_ok.assert_called_once_with(
            "test_file", os.R_OK, "p", False)
