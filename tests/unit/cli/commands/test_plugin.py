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

import io
from unittest import mock

import ddt

from rally import exceptions
from rally.cli import cliutils
from rally.cli.commands import plugin as plugin_cmd
from rally.common import utils
from rally.common.plugin import plugin
from tests.unit import test


@ddt.ddt
class PluginCommandsTestCase(test.TestCase):

    def setUp(self):
        super(PluginCommandsTestCase, self).setUp()

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

    def test__print_plugins_list(self):
        out = io.StringIO()
        original_print_list = cliutils.print_list

        def print_list(*args, **kwargs):
            kwargs["out"] = out
            original_print_list(*args, **kwargs)

        with mock.patch.object(plugin_cmd.cliutils, "print_list",
                               new=print_list):
            plugin_cmd._print_plugins_list(
                [self.Plugin1, self.Plugin2])

        self.assertEqual(
            "+-------------+------+----------+-------+\n"
            "| Plugin base | Name | Platform | Title |\n"
            "+-------------+------+----------+-------+\n"
            "| Plugin      | p1   | p1_ns    | T1.   |\n"
            "| Plugin      | p2   | p2_ns    | T2.   |\n"
            "+-------------+------+----------+-------+\n", out.getvalue())

    def test_show(self):
        with utils.StdOutCapture() as out:
            plugin_cmd.show("p1", platform="p1_ns")
            output = out.getvalue()

            self.assertIn("NAME\n\tp1", output)
            self.assertIn("PLATFORM\n\tp1_ns", output)
            self.assertIn("cli.commands.test_plugin", output)
            self.assertIn("DESCRIPTION\n\tDescription of T1", output)
            self.assertIn("PARAMETERS", output)

    @ddt.data(
        {
            "name": "nonex",
            "platform": None,
            "text": "Plugin nonex not found at any platform\n"
        },
        {
            "name": "nonexplugin",
            "platform": "nonex",
            "text": "Plugin nonexplugin@nonex not found\n"
        }
    )
    @ddt.unpack
    def test_show_not_found(self, name, platform, text):
        with utils.StdOutCapture() as out:
            with self.assertExitCode(exceptions.PluginNotFound.error_code):
                plugin_cmd.show(name, platform=platform)
            self.assertEqual(out.getvalue(), text)

    @mock.patch("rally.cli.commands.plugin._print_plugins_list")
    def test_show_many(self, mock__print_plugins_list):
        with utils.StdOutCapture() as out:
            with mock.patch("rally.cli.commands.plugin.plugin.Plugin."
                            "get_all") as mock_plugin_get_all:
                mock_plugin_get_all.return_value = [self.Plugin2,
                                                    self.Plugin3]
                with self.assertExitCode(
                        exceptions.MultiplePluginsFound.error_code):
                    plugin_cmd.show("p", platform="p2_ns")
                self.assertEqual("Multiple plugins found:\n",
                                 out.getvalue())
                mock_plugin_get_all.assert_called_once_with(
                    platform="p2_ns")

        mock__print_plugins_list.assert_called_once_with([
            self.Plugin2, self.Plugin3])

    @ddt.data(
        {
            "name": None,
            "platform": "nonex",
            "text": "Platform nonex not found\n"
        },
        {
            "name": "p2",
            "platform": "p1_ns",
            "text": "Plugin p2 not found\n"
        }
    )
    @ddt.unpack
    def test_list_not_found(self, name, platform, text):

        with utils.StdOutCapture() as out:
            plugin_cmd.list_(name, platform=platform)
            self.assertEqual(text, out.getvalue())

    @mock.patch("rally.cli.commands.plugin._print_plugins_list")
    def test_list(self, mock__print_plugins_list):

        plugin_cmd.list_(None, platform="p1_ns")
        plugin_cmd.list_("p1", platform="p1_ns")
        plugin_cmd.list_("p2")

        mock__print_plugins_list.assert_has_calls([
            mock.call([self.Plugin1]),
            mock.call([self.Plugin1]),
            mock.call([self.Plugin2])
        ])
