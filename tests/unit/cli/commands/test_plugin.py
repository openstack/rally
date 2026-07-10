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

from rally import exceptions
from rally.common.plugin import plugin
from tests.unit.cli import test


@plugin.configure("p1", "p1_ns")
class Plugin1(plugin.Plugin):
    """T1.

    Description of T1

    :param x: x arg
    :param y: y arg
    """
    pass


@plugin.configure("p2", "p2_ns")
class Plugin2(plugin.Plugin):
    """T2."""
    pass


@plugin.configure("p3", "p2_ns")
class Plugin3(plugin.Plugin):
    """T3."""
    pass


class PluginCommandsTestCase(test.CLITestCase):

    # the plugin commands work off the in-process registry, never the DB
    APPLY_DB_SCHEMA = False

    def test__print_plugins_list(self):
        # listing a platform renders the shared plugins table
        result = self.invoke(["plugin", "list", "--platform", "p2_ns"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(
            "+-------------+------+----------+-------+\n"
            "| Plugin base | Name | Platform | Title |\n"
            "+-------------+------+----------+-------+\n"
            "| Plugin      | p2   | p2_ns    | T2.   |\n"
            "| Plugin      | p3   | p2_ns    | T3.   |\n"
            "+-------------+------+----------+-------+\n", result.output)

    def test_show(self):
        result = self.invoke(["plugin", "show", "p1", "--platform", "p1_ns"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("NAME\n\tp1", result.output)
        self.assertIn("PLATFORM\n\tp1_ns", result.output)
        self.assertIn("cli.commands.test_plugin", result.output)
        self.assertIn("DESCRIPTION\n\tDescription of T1", result.output)
        self.assertIn("PARAMETERS", result.output)

    def test_show_not_found(self):
        for args, text in (
            (["nonex"], "Plugin nonex not found at any platform"),
            (["nonexplugin", "--platform", "nonex"],
             "Plugin nonexplugin@nonex not found"),
        ):
            with self.subTest(args=args):
                result = self.invoke(["plugin", "show", *args])
                self.assertEqual(exceptions.PluginNotFound.error_code,
                                 result.exit_code)
                self.assertIn(text, result.output)

    def test_show_many(self):
        # "p" matches both p2 and p3 in p2_ns -> the ambiguous branch
        result = self.invoke(["plugin", "show", "p", "--platform", "p2_ns"])

        self.assertEqual(exceptions.MultiplePluginsFound.error_code,
                         result.exit_code)
        self.assertIn("Multiple plugins found:", result.output)
        self.assertIn("p2", result.output)
        self.assertIn("p3", result.output)

    def test_list_not_found(self):
        for args, text in (
            (["--platform", "nonex"], "Platform nonex not found"),
            (["p2", "--platform", "p1_ns"], "Plugin p2 not found"),
        ):
            with self.subTest(args=args):
                result = self.invoke(["plugin", "list", *args])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(text, result.output)

    def test_list(self):
        for args, present, absent in (
            (["--platform", "p1_ns"], "p1", "p2"),
            (["p1", "--platform", "p1_ns"], "p1", "p2"),
            (["p2"], "p2", "p1"),
        ):
            with self.subTest(args=args):
                result = self.invoke(["plugin", "list", *args])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(present, result.output)
                self.assertNotIn(absent, result.output)
