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
from rally import exceptions
from tests.unit import test


class ValidationHelpersTestCase(test.TestCase):

    def test_validation_add_validator_to_validator(self):
        exc = self.assertRaises(
            exceptions.RallyException,
            validation.add("dummy_validator"), DummyValidator)
        self.assertEqual("Only RequiredPlatformValidator can be added "
                         "to other validators as a validator", str(exc))

    def test_validation_add_validator_to_platform_validator(self):
        exc = self.assertRaises(
            exceptions.RallyException,
            validation.add("required_platform"),
            validation.RequiredPlatformValidator)
        self.assertEqual("Cannot add a validator to RequiredPlatformValidator",
                         str(exc))


@validation.add(name="required_platform", platform="foo", admin=True)
@plugin.configure(name="dummy_validator")
class DummyValidator(validation.Validator):

    def __init__(self, foo):
        """Dummy validator

        :param foo: additional parameter for Dummy validator
        """
        super(DummyValidator, self).__init__()
        self.foo = foo

    def validate(self, context, config, plugin_cls, plugin_cfg):
        if self.foo not in config:
            raise Exception("foo")


class ValidatorTestCase(test.TestCase):

    def test_dummy_validators(self):
        @plugin.base()
        class DummyPluginBase(plugin.Plugin,
                              validation.ValidatablePluginMixin):
            pass

        @validation.add(name="dummy_validator", foo="bar")
        @validation.add(name="required_platform", platform="foo", users=True)
        @plugin.configure(name="dummy_plugin")
        class DummyPlugin(DummyPluginBase):
            pass

        ctx = {"platforms": {
            "foo": {"admin": "fake_admin", "users": ["fake_user"]}}}
        result = DummyPluginBase.validate(
            name="dummy_plugin", context=ctx,
            config={"bar": 1}, plugin_cfg={})
        self.assertEqual(0, len(result), result)

        result = DummyPluginBase.validate(
            name="dummy_plugin", context=ctx, config={}, plugin_cfg={})
        self.assertEqual(1, len(result))
        self.assertIn("raise Exception(\"foo\")", result[0])

        DummyPlugin.unregister()

    def test_failures(self):
        @plugin.base()
        class DummyPluginBase(plugin.Plugin,
                              validation.ValidatablePluginMixin):
            pass

        result = DummyPluginBase.validate("dummy_plugin", None, None, None)
        self.assertEqual(1, len(result))
        self.assertIn("There is no DummyPluginBase plugin "
                      "with name: 'dummy_plugin'", result[0])


@ddt.ddt
class RequiredPlatformValidatorTestCase(test.TestCase):

    @ddt.data(
        {"kwargs": {"platform": "foo", "admin": True},
         "context": {"platforms": {"foo": {"admin": "fake_admin"}}}},
        {"kwargs": {"platform": "foo", "admin": True, "users": True},
         "context": {"platforms": {"foo": {"admin": "fake_admin"}}}},
        {"kwargs": {"platform": "foo", "admin": True, "users": True},
         "context": {"platforms": {"foo": {"admin": "fake_admin",
                                           "users": ["fake_user"]}}}}
    )
    @ddt.unpack
    def test_validator(self, kwargs, context):
        validator = validation.RequiredPlatformValidator(**kwargs)
        validator.validate(context, None, None, None)

    @ddt.data(
        {"kwargs": {"platform": "foo"},
         "context": {},
         "error_msg": "You should specify admin=True or users=True or both."},
        {"kwargs": {"platform": "foo", "admin": True},
         "context": {"platforms": {}},
         "error_msg": "No admin credential for foo"},
        {"kwargs": {"platform": "foo", "admin": True, "users": True},
         "context": {"platforms": {"foo": {"users": ["fake_user"]}}},
         "error_msg": "No admin credential for foo"},
        {"kwargs": {"platform": "foo", "users": True},
         "context": {"platforms": {"foo": {}}},
         "error_msg": "No user credentials for foo"}
    )
    @ddt.unpack
    def test_validator_failed(self, kwargs, context, error_msg=False):
        validator = validation.RequiredPlatformValidator(**kwargs)
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, context, None, None, None)
        self.assertEqual(error_msg, e.message)
