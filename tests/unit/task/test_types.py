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
