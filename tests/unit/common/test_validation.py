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

    def __init__(self, foo, exc=False):
        """Dummy validator

        :param foo: additional parameter for Dummy validator
        :param exc: whether to raise expected on unexpected error
        """
        super(DummyValidator, self).__init__()
        self.foo = foo
        self.exc = exc

    def validate(self, context, config, plugin_cls, plugin_cfg):
        if self.foo not in config:
            if self.exc:
                raise Exception("foo")
            self.fail("oops")


@plugin.base()
class DummyPluginBase(plugin.Plugin,
                      validation.ValidatablePluginMixin):
    pass


class ValidatorTestCase(test.TestCase):

    def test_dummy_validators(self):
        @plugin.base()
        class DummyPluginBase(plugin.Plugin,
                              validation.ValidatablePluginMixin):
            pass

        @validation.add(name="dummy_validator", foo="bar", exc=True)
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

    def test_simple_failure(self):

        result = DummyPluginBase.validate("dummy_plugin", None, None, None)
        self.assertEqual(1, len(result))
        self.assertIn("There is no DummyPluginBase plugin `dummy_plugin`",
                      result[0])

    def test_failure_includes_detailed_info(self):

        @validation.add("dummy_validator", foo="bar")
        @plugin.configure(name=self.id())
        class Foo(DummyPluginBase):
            pass

        result = DummyPluginBase.validate(self.id(), {}, {}, None,
                                          vtype="semantic")
        self.assertEqual(1, len(result))
        self.assertEqual(
            "DummyPluginBase plugin '%s' doesn't pass dummy_validator@default "
            "validation. Details: oops" % self.id(),
            result[0])


@ddt.ddt
class RequiredPlatformValidatorTestCase(test.TestCase):

    @ddt.data(
        {"kwargs": {"platform": "foo"},
         "context": {"platforms": {"foo": {}}}},
        {"kwargs": {"platform": "openstack", "admin": True},
         "context": {"platforms": {"openstack": {"admin": "fake_admin"}}}},
        {"kwargs": {"platform": "openstack", "admin": True, "users": True},
         "context": {"platforms": {"openstack": {"admin": "fake_admin"}}}},
        {"kwargs": {"platform": "openstack", "admin": True, "users": True},
         "context": {"platforms": {"openstack": {"admin": "fake_admin",
                                                 "users": ["fake_user"]}}}}
    )
    @ddt.unpack
    def test_validator(self, kwargs, context):
        validator = validation.RequiredPlatformValidator(**kwargs)
        validator.validate(context, None, None, None)

    @ddt.data(
        {"kwargs": {"platform": "openstack", "admin": True},
         "context": {"platforms": {"openstack": {}}},
         "error_msg": "No admin credential for openstack"},
        {"kwargs": {"platform": "openstack", "users": True},
         "context": {"platforms": {"openstack": {}}},
         "error_msg": "No user credentials for openstack"},
        {"kwargs": {"platform": "openstack"},
         "context": {"platforms": {"openstack": {}}},
         "error_msg": "You should specify admin=True or users=True or both "
                      "for validating openstack platform."},
        {"kwargs": {"platform": "foo"},
         "context": {"platforms": {}},
         "error_msg": "There is no specification for foo platform in "
                      "selected environment."}
    )
    @ddt.unpack
    def test_validator_failed(self, kwargs, context, error_msg):
        validator = validation.RequiredPlatformValidator(**kwargs)
        e = self.assertRaises(
            validation.ValidationError,
            validator.validate, context, None, None, None)
        self.assertEqual(error_msg, e.message)
