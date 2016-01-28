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
        rows = [utils.Struct(name=f.get_name(),
                             namespace=f.get_namespace(),
                             title=f.get_info()["title"])
                for f in plugin_list]

        cliutils.print_list(rows, fields=["name", "namespace", "title"])

    @cliutils.args("--name", dest="name", type=str,
                   help="Plugin name.")
    @cliutils.args("--namespace", dest="namespace", type=str,
                   help="Plugin namespace.")
    @plugins.ensure_plugins_are_loaded
    def show(self, name, namespace=None):
        """Show detailed information about a Rally plugin."""
        name_lw = name.lower()
        all_plugins = plugin.Plugin.get_all(namespace=namespace)
        found = [p for p in all_plugins if name_lw in p.get_name().lower()]
        exact_match = [p for p in found if name_lw == p.get_name().lower()]

        if not found:
            if namespace:
                print(
                    "There is no plugin: %(name)s in %(namespace)s namespace"
                    % {"name": name, "namespace": namespace}
                )
            else:
                print("There is no plugin: %s" % name)

        elif len(found) == 1 or exact_match:
            plugin_ = found[0] if len(found) == 1 else exact_match[0]
            plugin_info = plugin_.get_info()
            print(cliutils.make_header(plugin_info["title"]))
            print("NAME\n\t%s" % plugin_info["name"])
            print("NAMESPACE\n\t%s" % plugin_info["namespace"])
            print("MODULE\n\t%s" % plugin_info["module"])
            if plugin_info["description"]:
                print("DESCRIPTION\n\t", end="")
                print("\n\t".join(plugin_info["description"].split("\n")))
            if plugin_info["parameters"]:
                print("PARAMETERS")
                rows = [utils.Struct(name=p["name"],
                                     description="%s\n" % p["doc"])
                        for p in plugin_info["parameters"]]
                cliutils.print_list(rows, fields=["name", "description"])
        else:
            print("Multiple plugins found:")
            self._print_plugins_list(found)

    @cliutils.args("--name", dest="name", type=str,
                   help="List only plugins that match the given name.")
    @cliutils.args(
        "--namespace", dest="namespace", type=str,
        help="List only plugins that are in the specified namespace.")
    @plugins.ensure_plugins_are_loaded
    def list(self, name=None, namespace=None):
        """List all Rally plugins that match name and namespace."""
        all_plugins = plugin.Plugin.get_all(namespace=namespace)
        matched = all_plugins
        if name:
            name_lw = name.lower()
            matched = [p for p in all_plugins
                       if name_lw in p.get_name().lower()]

        if not all_plugins:
            print("There is no plugin namespace: %s" % namespace)
        elif not matched:
            print("There is no plugin: %s" % name)
        else:
            self._print_plugins_list(matched)
