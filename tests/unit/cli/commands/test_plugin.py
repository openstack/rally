# Copyright 2015: Mirantis Inc.
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

from rally.cli.commands import plugin as plugin_cmd
from rally.common.plugin import plugin
from rally.common import utils
from tests.unit import test


@ddt.ddt
class PluginCommandsTestCase(test.TestCase):

    def setUp(self):
        super(PluginCommandsTestCase, self).setUp()
        self.plugin_cmd = plugin_cmd.PluginCommands()

        @plugin.configure("p1", "p1_ns")
        class Plugin1(plugin.Plugin):
            """T1.

            Description of T1

            :param x: x arg
            :param y: y arg
            """
            pass

        self.Plugin1 = Plugin1

        @plugin.configure("p2", "p2_ns")
        class Plugin2(plugin.Plugin):
            """T2."""
            pass

        self.Plugin2 = Plugin2

        @plugin.configure("p3", "p2_ns")
        class Plugin3(plugin.Plugin):
            """T3."""
            pass

        self.Plugin3 = Plugin3

    def tearDown(self):
        super(PluginCommandsTestCase, self).tearDown()
        self.Plugin1.unregister()
        self.Plugin2.unregister()
        self.Plugin3.unregister()

    @mock.patch("rally.cli.commands.plugin.utils.Struct")
    @mock.patch("rally.cli.commands.plugin.cliutils.print_list")
    def test__print_plugins_list(self, mock_print_list, mock_struct):
        mock1 = mock.MagicMock()
        mock2 = mock.MagicMock()
        mock_struct.side_effect = [mock1, mock2]

        plugin_cmd.PluginCommands._print_plugins_list(
            [self.Plugin1, self.Plugin2])

        mock_print_list.assert_called_once_with(
            [mock1, mock2], fields=["name", "namespace", "title"])

    def test_show(self):
        with utils.StdOutCapture() as out:
            plugin_cmd.PluginCommands().show("p1", "p1_ns")
            output = out.getvalue()

            self.assertIn("NAME\n\tp1", output)
            self.assertIn("NAMESPACE\n\tp1_ns", output)
            self.assertIn("cli.commands.test_plugin", output)
            self.assertIn("DESCRIPTION\n\tDescription of T1", output)
            self.assertIn("PARAMETERS", output)

    @ddt.data(
        {
            "name": "nonex",
            "namespace": None,
            "text": "There is no plugin: nonex\n"
        },
        {
            "name": "nonexplugin",
            "namespace": "nonex",
            "text": "There is no plugin: nonexplugin in nonex namespace\n"
        }
    )
    @ddt.unpack
    def test_show_not_found(self, name, namespace, text):
        with utils.StdOutCapture() as out:
            plugin_cmd.PluginCommands().show(name, namespace)
            self.assertEqual(out.getvalue(), text)

    @mock.patch("rally.cli.commands.plugin.PluginCommands._print_plugins_list")
    def test_show_many(self, mock_plugin_commands__print_plugins_list):
        with utils.StdOutCapture() as out:
            with mock.patch("rally.cli.commands.plugin.plugin.Plugin."
                            "get_all") as mock_plugin_get_all:
                mock_plugin_get_all.return_value = [self.Plugin2, self.Plugin3]
                plugin_cmd.PluginCommands().show("p", "p2_ns")
                self.assertEqual(out.getvalue(), "Multiple plugins found:\n")
                mock_plugin_get_all.assert_called_once_with(namespace="p2_ns")

        mock_plugin_commands__print_plugins_list.assert_called_once_with([
            self.Plugin2, self.Plugin3])

    @ddt.data(
        {
            "name": None,
            "namespace": "nonex",
            "text": "There is no plugin namespace: nonex\n"
        },
        {
            "name": "p2",
            "namespace": "p1_ns",
            "text": "There is no plugin: p2\n"
        }
    )
    @ddt.unpack
    def test_list_not_found(self, name, namespace, text):

        with utils.StdOutCapture() as out:
            plugin_cmd.PluginCommands().list(name, namespace)
            self.assertEqual(out.getvalue(), text)

    @mock.patch("rally.cli.commands.plugin.PluginCommands._print_plugins_list")
    def test_list(self, mock_plugin_commands__print_plugins_list):

        plugin_cmd.PluginCommands().list(None, "p1_ns")
        plugin_cmd.PluginCommands().list("p1", "p1_ns")
        plugin_cmd.PluginCommands().list("p2", None)

        mock_plugin_commands__print_plugins_list.assert_has_calls([
            mock.call([self.Plugin1]),
            mock.call([self.Plugin1]),
            mock.call([self.Plugin2])
        ])
