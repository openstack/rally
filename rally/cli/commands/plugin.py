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

import typing as t

import typer

from rally import exceptions
from rally import plugins
from rally.cli import argutils
from rally.cli import cliutils
from rally.common import utils
from rally.common.plugin import info as plugin_info
from rally.common.plugin import plugin


plugin_app = typer.Typer(
    name="plugin", no_args_is_help=False,
    help="Discover and inspect installed plugins.")


def _schema_type_label(prop: dict[str, t.Any]) -> str:
    """Short type label for an arg schema property (blank if not simple)."""
    if not prop:
        return ""
    if "enum" in prop:
        values = ", ".join(str(v) for v in prop["enum"])
        return f"Enum[{values}]"
    labels = plugin_info.JSON_SCHEMA_TYPE_LABELS
    json_type = prop.get("type")
    if isinstance(json_type, list):  # e.g. ["integer", "null"], ["int", "str"]
        parts = [labels.get(j, "") for j in json_type if j != "null"]
        return "/".join(p for p in parts if p)
    if not json_type:
        return ""
    return labels.get(json_type, "")


def _print_plugins_list(plugin_list: list) -> None:
    formatters = {
        "Name": lambda p: p.get_name(),
        "Platform": lambda p: p.get_platform(),
        "Title": lambda p: p.get_info()["title"],
        "Plugin base": lambda p: p._get_base().__name__
    }

    cliutils.print_list(plugin_list, formatters=formatters,
                        normalize_field_names=True,
                        fields=["Plugin base", "Name", "Platform", "Title"])


@plugin_app.command()
@plugins.ensure_plugins_are_loaded
def show(
    name: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--name",
            help="Plugin name."
        )
    ],
    platform: t.Annotated[
        str | None,
        typer.Option(
            help="Plugin platform."
        )
    ] = None,
) -> None:
    """Show detailed information about a Rally plugin."""
    name_lw = name.lower()
    all_plugins = plugin.Plugin.get_all(platform=platform)
    found = [p for p in all_plugins if name_lw in p.get_name().lower()]
    exact_match = [p for p in found if name_lw == p.get_name().lower()]

    if not found:
        if platform:
            print("Plugin %(name)s@%(platform)s not found"
                  % {"name": name, "platform": platform})
        else:
            print("Plugin %s not found at any platform" % name)
        raise typer.Exit(code=exceptions.PluginNotFound.error_code)

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
        schema = plugin_info["schema"]
        props = schema.get("properties") if isinstance(schema, dict) else None
        if props:
            # render the argument/config schema: name, type (Any when not
            # constrained to a simple type) and description.
            print("PARAMETERS")
            rows = []
            for name, prop in props.items():
                prop = prop if isinstance(prop, dict) else {}
                rows.append(utils.Struct(
                    name=name,
                    type=_schema_type_label(prop) or "Any",
                    description=prop.get("description", "")))
            cliutils.print_list(rows,
                                fields=["name", "type", "description"],
                                sortby_index=None)
        elif plugin_info["parameters"]:
            # no schema (e.g. an un-annotated scenario), so fall back to the
            # docstring parameters.
            print("PARAMETERS")
            rows = [utils.Struct(name=p["name"], description=p["doc"])
                    for p in plugin_info["parameters"]]
            cliutils.print_list(rows, fields=["name", "description"],
                                sortby_index=None)
    else:
        print("Multiple plugins found:")
        _print_plugins_list(found)
        raise typer.Exit(code=exceptions.MultiplePluginsFound.error_code)


@plugin_app.command(name="list")
@plugins.ensure_plugins_are_loaded
def list_(
    name: t.Annotated[
        str | None,
        typer.Argument(
            help="List only plugins that match the given name."
        )
    ] = None,
    platform: t.Annotated[
        str | None,
        typer.Option(
            help="List only plugins that are in the specified platform."
        )
    ] = None,
    base_cls: t.Annotated[
        str | None,
        typer.Option(
            "--plugin-base",
            help="Plugin base class."
        )
    ] = None,
) -> None:
    """List all Rally plugins that match name and platform."""
    all_plugins = plugin.Plugin.get_all(platform=platform)
    matched = all_plugins
    if name:
        name_lw = name.lower()
        matched = [p for p in all_plugins if name_lw in p.get_name().lower()]

    if base_cls:
        matched = [p for p in matched if p._get_base().__name__ == base_cls]

    if not all_plugins:
        print("Platform %s not found" % platform)
    elif not matched:
        print("Plugin %s not found" % name)
    else:
        _print_plugins_list(matched)
