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

from rally.task import scenario
from rally.task import types
from tests.unit import test


class TestConvertPlugin(scenario.Scenario):
    @types.convert(bar={"type": "test_bar"})
    @scenario.configure()
    def one_arg(self, bar):
        """Dummy docstring.

        :param bar: dummy parameter
        """
        pass

    @types.convert(bar={"type": "test_bar"},
                   baz={"type": "test_baz"})
    @scenario.configure()
    def two_args(self, bar, baz):
        """Dummy docstring.

        :param bar: dummy parameter
        :param baz: dummy parameter
        """
        pass


class ConvertTestCase(test.TestCase):
    # NOTE(stpierre): These cases test types.convert(),
    # types._get_preprocessor_loader(), and bits of
    # types.preprocess(). This may not look very elegant, but it's the
    # easiest way to test both convert() and
    # _get_preprocessor_loader() without getting so fine-grained that
    # the tests are basically tests that the computer is on.

    @mock.patch("rally.task.types.ResourceType.get", create=True)
    def test_convert(self, mock_resource_type_get):
        mock_transform = mock_resource_type_get.return_value.transform
        args = types.preprocess("TestConvertPlugin.one_arg",
                                mock.MagicMock(),
                                {"bar": "bar_config"})
        mock_resource_type_get.assert_called_once_with("test_bar")
        mock_transform.assert_called_once_with(clients=mock.ANY,
                                               resource_config="bar_config")
        self.assertDictEqual(args, {"bar": mock_transform.return_value})

    @mock.patch("rally.task.types.ResourceType.get", create=True)
    def test_convert_multiple(self, mock_resource_type_get):
        loaders = {"test_bar": mock.Mock(), "test_baz": mock.Mock()}
        mock_resource_type_get.side_effect = lambda p: loaders[p]

        args = types.preprocess("TestConvertPlugin.two_args",
                                mock.MagicMock(),
                                {"bar": "bar_config",
                                 "baz": "baz_config"})
        mock_resource_type_get.assert_has_calls([mock.call("test_bar"),
                                                 mock.call("test_baz")],
                                                any_order=True)
        loaders["test_bar"].transform.assert_called_once_with(
            clients=mock.ANY, resource_config="bar_config")
        loaders["test_baz"].transform.assert_called_once_with(
            clients=mock.ANY, resource_config="baz_config")
        self.assertDictEqual(
            args,
            {"bar": loaders["test_bar"].transform.return_value,
             "baz": loaders["test_baz"].transform.return_value})


class PreprocessTestCase(test.TestCase):

    @mock.patch("rally.task.types.scenario.Scenario.get")
    @mock.patch("rally.task.types.osclients")
    def test_preprocess(self, mock_osclients, mock_scenario_get):

        name = "some_plugin"

        context = {
            "a": 1,
            "b": 2,
            "admin": {"credential": mock.MagicMock()}
        }
        args = {"a": 10, "b": 20}

        class Preprocessor(types.ResourceType):

            @classmethod
            def transform(cls, clients, resource_config):
                return resource_config * 2

        mock_scenario_get.return_value._meta_get.return_value = {
            "a": Preprocessor
        }

        result = types.preprocess(name, context, args)
        mock_scenario_get.assert_called_once_with(name)
        mock_scenario_get.return_value._meta_get.assert_called_once_with(
            "preprocessors", default={})
        mock_osclients.Clients.assert_called_once_with(
            context["admin"]["credential"])
        self.assertEqual({"a": 20, "b": 20}, result)
