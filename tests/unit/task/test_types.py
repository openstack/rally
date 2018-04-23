# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

from rally.common.plugin import plugin
from rally.task import scenario
from rally.task import types
from tests.unit import test


class ConvertTestCase(test.TestCase):

    # NOTE(stpierre): These cases test types.convert(),
    # types._get_preprocessor_loader(), and bits of
    # types.preprocess(). This may not look very elegant, but it's the
    # easiest way to test both convert() and
    # _get_preprocessor_loader() without getting so fine-grained that
    # the tests are basically tests that the computer is on.

    def setUp(self):
        super(ConvertTestCase, self).setUp()

        @types.convert(bar={"type": "test_bar"})
        @scenario.configure(name="FakeConvertPlugin.one_arg")
        class FakeConvertOneArgPlugin(scenario.Scenario):
            def run(self, bar):
                """Dummy docstring.

                :param bar: dummy parameter
                """
                pass

        self.addCleanup(FakeConvertOneArgPlugin.unregister)

        @types.convert(bar={"type": "test_bar"},
                       baz={"type": "test_baz"})
        @scenario.configure(name="FakeConvertPlugin.two_args")
        class FakeConvertTwoArgsPlugin(scenario.Scenario):

            def run(self, bar, baz):
                """Dummy docstring.

                :param bar: dummy parameter
                :param baz: dummy parameter
                """
                pass

        self.addCleanup(FakeConvertTwoArgsPlugin.unregister)

    @mock.patch("rally.task.types.ResourceType.get", create=True)
    def test_convert(self, mock_resource_type_get):
        ctx = mock.MagicMock()
        args = types.preprocess("FakeConvertPlugin.one_arg",
                                ctx,
                                {"bar": "bar_config"})
        mock_resource_type_get.assert_called_once_with("test_bar")
        resourcetype_cls = mock_resource_type_get.return_value
        resourcetype_cls.assert_called_once_with(ctx, {})
        resourcetype_obj = resourcetype_cls.return_value
        resourcetype_obj.pre_process.assert_called_once_with(
            resource_spec="bar_config", config={"type": "test_bar"})
        self.assertDictEqual(
            args, {"bar": resourcetype_obj.pre_process.return_value})

    @mock.patch("rally.task.types.ResourceType.get", create=True)
    def test_convert_multiple(self, mock_resource_type_get):
        resourcetype_classes = {"bar": mock.Mock(), "baz": mock.Mock()}

        def _get_resource_type(name):
            # cut "test_" prefix
            name = name[5:]
            if name in resourcetype_classes:
                return resourcetype_classes[name]
            self.fail("The unexpected resource class tried to be used.")

        mock_resource_type_get.side_effect = _get_resource_type

        ctx = mock.MagicMock()
        scenario_args = {"bar": "bar_config", "baz": "baz_config"}
        processed_args = types.preprocess(
            "FakeConvertPlugin.two_args", ctx, scenario_args)

        mock_resource_type_get.assert_has_calls([mock.call("test_bar"),
                                                 mock.call("test_baz")],
                                                any_order=True)

        expected_dict = {}
        for resourcetype_n, resourcetype_cls in resourcetype_classes.items():
            resourcetype_cls.assert_called_once_with(ctx, {})
            resourcetype_obj = resourcetype_cls.return_value
            resourcetype_obj.pre_process.assert_called_once_with(
                resource_spec=scenario_args[resourcetype_n],
                config={"type": "test_%s" % resourcetype_n})
            return_value = resourcetype_obj.pre_process.return_value
            expected_dict[resourcetype_n] = return_value

        self.assertDictEqual(expected_dict, processed_args)


class PreprocessTestCase(test.TestCase):

    @mock.patch("rally.task.types.scenario.Scenario.get")
    def test_preprocess(self, mock_scenario_get):

        name = "some_plugin"
        type_name = "%s_type" % self.id()

        context = {
            "a": 1,
            "b": 2,
        }
        args = {"a": 10, "b": 20}

        @plugin.configure(type_name)
        class SomeType(types.ResourceType):

            def pre_process(self, resource_spec, config):
                return resource_spec * 2

        mock_scenario_get.return_value._meta_get.return_value = {
            "a": {"type": type_name}
        }

        result = types.preprocess(name, context, args)
        mock_scenario_get.assert_called_once_with(name)
        mock_scenario_get.return_value._meta_get.assert_called_once_with(
            "preprocessors", default={})
        self.assertEqual({"a": 20, "b": 20}, result)


class DeprecatedBehaviourMixinTestCase(test.TestCase):
    def test_transform(self):
        call_args_list = []
        expected_return_value = mock.Mock()

        @types.plugin.configure(self.id())
        class OldResource(types.ResourceType,
                          types.DeprecatedBehaviourMixin):
            def pre_process(s, resource_spec, config):
                call_args_list.append((resource_spec, config))
                return expected_return_value

        clients = mock.Mock()
        resource_config = {"foo": "bar"}

        self.assertEqual(expected_return_value,
                         OldResource.transform(clients, resource_config))
        self.assertEqual(expected_return_value,
                         OldResource.transform(None, resource_config))
        self.assertEqual([(resource_config, {}),
                          (resource_config, {})], call_args_list)


class ResourceTypeCompatTestCase(test.TestCase):
    """Check how compatibility with an old interface works."""

    def test_applying_preprocess_method(self):

        setattr(types._pre_process_method, "key", self.id())

        @plugin.configure("1-%s" % self.id())
        class OldResourceType(types.ResourceType):
            @classmethod
            def transform(cls, clients, resource_config):
                pass

        self.assertEqual(
            self.id(),
            getattr(OldResourceType({}, {}).pre_process, "key", None))

        @plugin.configure("2-%s" % self.id())
        class ResourceTypeWithInnerCompatLayer(types.ResourceType):
            @classmethod
            def transform(cls, clients, resource_config):
                pass

            def pre_process(self, resource_spec, config):
                pass

        self.assertNotEqual(
            self.id(),
            getattr(ResourceTypeWithInnerCompatLayer.pre_process, "key", None))

        @plugin.configure("3-%s" % self.id())
        class CurrentResourceType(types.ResourceType):
            def pre_process(self, resource_spec, config):
                pass

        self.assertFalse(hasattr(CurrentResourceType, "transform"))
        self.assertNotEqual(
            self.id(),
            getattr(CurrentResourceType.pre_process, "key", None))

    def test__pre_process_method(self):
        cred1 = mock.Mock()
        cred2 = mock.Mock()

        self_obj = mock.Mock()
        self_obj.__class__ = mock.Mock()
        self_obj._context = {"admin": {"credential": cred1},
                             "users": [{"credential": cred2}]}

        # case #1: in case of None resource_spec, None should be returned
        self.assertIsNone(types._pre_process_method(self_obj, None, None))
        self.assertFalse(self_obj.__class__.transform.called)

        # case #2: admin creds should be used
        resource_spec = {"foo": "bar"}
        res = types._pre_process_method(self_obj, resource_spec, None)
        self.assertEqual(self_obj.__class__.transform.return_value, res)
        self.assertTrue(self_obj.__class__.transform.called)
        c_args, c_kwargs = self_obj.__class__.transform.call_args_list[0]
        self.assertFalse(c_args)
        self.assertEqual({"resource_config", "clients"}, set(c_kwargs.keys()))
        self.assertEqual(resource_spec, c_kwargs["resource_config"])
        self.assertEqual(cred1, c_kwargs["clients"].credential)

        # case #3: user creds should be used
        self_obj.__class__.transform.reset_mock()
        self_obj._context.pop("admin", None)
        res = types._pre_process_method(self_obj, resource_spec, None)
        self.assertEqual(self_obj.__class__.transform.return_value, res)
        self.assertTrue(self_obj.__class__.transform.called)
        c_args, c_kwargs = self_obj.__class__.transform.call_args_list[0]
        self.assertFalse(c_args)
        self.assertEqual({"resource_config", "clients"}, set(c_kwargs.keys()))
        self.assertEqual(resource_spec, c_kwargs["resource_config"])
        self.assertEqual(cred2, c_kwargs["clients"].credential)
