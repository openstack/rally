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

from __future__ import print_function

from rally.cli import cliutils
from rally.common.plugin import plugin
from rally.common import utils
from rally import plugins


class PluginCommands(object):
    """Set of commands that allow you to manage Rally plugins."""

    @staticmethod
    def _print_plugins_list(plugin_list):
        formatters = {
            "Name": lambda p: p.get_name(),
            "Platform": lambda p: p.get_platform(),
            "Title": lambda p: p.get_info()["title"],
            "Plugin base": lambda p: p._get_base().__name__
        }

        cliutils.print_list(plugin_list, formatters=formatters,
                            normalize_field_names=True,
                            fields=["Plugin base", "Name", "Platform",
                                    "Title"])

    @cliutils.args("--name", dest="name", type=str,
                   help="Plugin name.")
    @cliutils.args("--platform", dest="platform", type=str,
                   help="Plugin platform.")
    @cliutils.deprecated_args("--namespace", dest="platform",
                              release="0.10.0", alternative="--platform")
    @plugins.ensure_plugins_are_loaded
    def show(self, api, name, platform=None):
        """Show detailed information about a Rally plugin."""
        name_lw = name.lower()
        all_plugins = plugin.Plugin.get_all(platform=platform)
        found = [p for p in all_plugins if name_lw in p.get_name().lower()]
        exact_match = [p for p in found if name_lw == p.get_name().lower()]

        if not found:
            if platform:
                print(
                    "Plugin %(name)s@%(platform)s not found"
                    % {"name": name, "platform": platform}
                )
            else:
                print("Plugin %s not found at any platform" % name)

        elif len(found) == 1 or exact_match:
            plugin_ = found[0] if len(found) == 1 else exact_match[0]
            plugin_info = plugin_.get_info()
            print(cliutils.make_header(plugin_info["title"]))
            print("NAME\n\t%s" % plugin_info["name"])
            print("PLATFORM\n\t%s" % plugin_info["platform"])
            print("MODULE\n\t%s" % plugin_info["module"])
            if plugin_info["description"]:
                print("DESCRIPTION\n\t", end="")
                print("\n\t".join(plugin_info["description"].split("\n")))
            if plugin_info["parameters"]:
                print("PARAMETERS")
                rows = [utils.Struct(name=p["name"],
                                     description=p["doc"])
                        for p in plugin_info["parameters"]]
                cliutils.print_list(rows, fields=["name", "description"],
                                    sortby_index=None)
        else:
            print("Multiple plugins found:")
            self._print_plugins_list(found)

    @cliutils.args(
        "--name", dest="name", type=str,
        help="List only plugins that match the given name.")
    @cliutils.args(
        "--platform", dest="platform", type=str,
        help="List only plugins that are in the specified platform.")
    @cliutils.deprecated_args("--namespace", dest="platform",
                              release="0.10.0", alternative="--platform")
    @cliutils.args(
        "--plugin-base", dest="base_cls", type=str,
        help="Plugin base class.")
    @plugins.ensure_plugins_are_loaded
    def list(self, api, name=None, platform=None, base_cls=None):
        """List all Rally plugins that match name and platform."""
        all_plugins = plugin.Plugin.get_all(platform=platform)
        matched = all_plugins
        if name:
            name_lw = name.lower()
            matched = [p for p in all_plugins
                       if name_lw in p.get_name().lower()]

        if base_cls:
            matched = [p for p in matched
                       if p._get_base().__name__ == base_cls]

        if not all_plugins:
            print("Platform %s not found" % platform)
        elif not matched:
            print("Plugin %s not found" % name)
        else:
            self._print_plugins_list(matched)
