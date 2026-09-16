# Copyright 2016: Mirantis Inc.
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

from __future__ import annotations

import inspect
import typing as t

from docutils.parsers import rst
import typer

from rally.cli import main

from . import utils


if t.TYPE_CHECKING:
    from docutils import nodes
    import typer.core

    TyperParameter = typer.core.TyperArgument | typer.core.TyperOption


DEFAULT_UUIDS_CMD = {
    "env": ["rally env create"],
    "task": ["rally task start"],
    "verification": ["rally verify start", "rally verify import"],
}

# Maps the "use"-command hint for each default-from-environment id.
USE_CMD = {
    "env": "rally env use",
    "task": "rally task use",
    "verification": "rally verify use",
}

# Maps a parameter's env var to a default-uuid id.
_ENVVAR_DEST = {
    "RALLY_ENV": "env",
    "RALLY_TASK": "task",
    "RALLY_VERIFICATION": "verification",
}

# Typer has no way to mark a whole command group as deprecated, so the notice
# is kept here.
DEPRECATED_CATEGORIES = {
    "deployment": (
        "These commands are deprecated. Use the ``env`` commands instead, "
        "they are described at the Environment Component page."
    ),
}


def compose_note_about_default_uuids(argument: str, dest: str) -> nodes.note:
    # TODO(andreykurilin): add references to commands
    return utils.note(
        "The default value for the ``%(arg)s`` argument is taken from "
        "the Rally environment. Usually, the default value is equal to"
        " the UUID of the last successful run of ``%(cmd)s``, if the "
        "``--no-use`` argument was not used."
        % {"arg": argument, "cmd": "``, ``".join(DEFAULT_UUIDS_CMD[dest])}
    )


def compose_use_cmd_hint_msg(cmd: str) -> nodes.hint:
    return utils.hint(
        f"You can set the default value by executing ``{cmd} <uuid>``"
        f" (ref__).\n\n __ #{cmd.replace(' ', '-')}"
    )


def _note_dest(cmd_name: str, param: TyperParameter) -> str | None:
    """Return the default-uuid note key for a parameter, or None.

    A parameter earns the note when it reads one of the ``RALLY_*`` env vars
    that ``rally <thing> use`` populates.  The ``use`` command sets these
    defaults itself, so it is excluded.
    """
    if cmd_name == "use" or not param.envvar:
        return None

    if isinstance(param.envvar, str):
        return _ENVVAR_DEST.get(param.envvar)

    return _ENVVAR_DEST.get(param.envvar[0])


# click type names are an implementation detail; these match the names of
# types in the plugin reference.
_TYPE_NAMES = {"text": "string", "float": "number", "boolean": "flag"}


def _choices(param: TyperParameter) -> t.Sequence[str] | None:
    return getattr(getattr(param, "type", None), "choices", None)


def _is_option(param: TyperParameter) -> bool:
    return bool(param.opts) and param.opts[0].startswith("-")


def _qualifiers(param: TyperParameter) -> list[str]:
    """Describe a parameter the way the plugin reference does.

    The result is rendered next to the name as ``--flag (string, required)``.
    """
    qualifiers = []
    if getattr(param, "is_flag", False):
        qualifiers.append("flag")
    elif not _choices(param):
        # the accepted values of a choice are spelled out in the description
        # instead, so the bare "choice" adds nothing here
        name = getattr(getattr(param, "type", None), "name", None)
        if name:
            qualifiers.append(_TYPE_NAMES.get(name, name))

    # an option given several times, or a positional argument that takes
    # all the remaining values
    if getattr(param, "multiple", False) or param.nargs == -1:
        qualifiers.append("repeatable")

    # a parameter that reads an env var is not really required: the variable
    # (or the value saved by a "use" command) supplies the value, and the
    # note above the description explains that
    if not param.envvar and getattr(param, "required", False):
        qualifiers.append("required")
    return qualifiers


def _display_names(param: TyperParameter) -> t.Sequence[str]:
    """Return the flag(s)/name shown for a parameter."""
    if _is_option(param):
        return param.opts
    # A positional argument: show its metavar (e.g. ``UUID``) rather than the
    # internal destination name, uppercased like a metavar when there is none.
    return [param.metavar or (param.name or "").upper()]


def _iter_params(
    command: typer.core.TyperGroup | typer.core.TyperCommand,
) -> t.Iterator[TyperParameter]:
    """Yield the documentable parameters of a command (skip ``--help``)."""
    for param in command.params:
        if param.opts and param.opts[0] in ("--help", "-h"):
            continue
        if param.name == "help":
            continue
        yield t.cast("TyperParameter", param)


def make_arguments_section(
    category_name: str,
    cmd_name: str,
    command: typer.core.TyperGroup | typer.core.TyperCommand,
    options_title: str = "**Options**:",
) -> list:
    params = list(_iter_params(command))
    positional = [p for p in params if not _is_option(p)]
    options = [p for p in params if _is_option(p)]
    elements = []
    for title, group in (
        ("**Positional arguments**:", positional),
        (options_title, options),
    ):
        if group:
            elements.append(utils.paragraph(title))
            elements.extend(
                _make_parameter_definitions(category_name, cmd_name, group)
            )
    return elements


def _make_parameter_definitions(
    category_name: str,
    cmd_name: str,
    params: t.Sequence[TyperParameter],
) -> list:
    elements = []
    for param in params:
        names = _display_names(param)
        flag = names[0]

        description: list = []
        note_dest = _note_dest(cmd_name, param)
        if note_dest is not None:
            description.append(
                compose_note_about_default_uuids(flag, note_dest)
            )
            description.append(compose_use_cmd_hint_msg(USE_CMD[note_dest]))

        description.append(getattr(param, "help", None))

        # values are shown as they are typed in a shell, unlike the plugin
        # reference, which shows them as they are written in a task file
        choices = _choices(param)
        if choices:
            values = [f"``{c}``" for c in choices]
            if len(values) == 1:
                description.append(f"Expected value: {values[0]}.")
            else:
                description.append(
                    f"Set of expected values: {', '.join(values)}."
                )

        if not getattr(param, "is_flag", False):
            default = getattr(param, "default", None)
            if note_dest is None and default is not None:
                # an empty inline literal is not valid markup
                shown = default if default != "" else '""'
                description.append(f"Defaults to ``{shown}``.")

        if param.envvar:
            envvar = (
                param.envvar
                if isinstance(param.envvar, str)
                else param.envvar[0]
            )
            description.append(f"**Environment variable**: ``{envvar}``")

        anchor = flag.replace("-", "").replace(" ", "")
        ref = f"{category_name}_{cmd_name}_{anchor}"
        elements.extend(
            utils.make_definition(
                ", ".join(names),
                ref,
                description,
                qualifiers=_qualifiers(param),
            )
        )
    return elements


def make_command_section(
    category_name: str, name: str, command: typer.core.TyperCommand
) -> t.Any:
    title = " ".join(part for part in ("rally", category_name, name) if part)
    section = utils.subcategory(title)
    description = inspect.getdoc(command.callback) or command.help or ""
    section.extend(utils.parse_text(description, source=f"<{title}>"))
    if any(True for _ in _iter_params(command)):
        section.extend(make_arguments_section(category_name, name, command))
    return section


def make_general_section(
    cli: t.Any,
    leaf_commands: dict[str, typer.core.TyperCommand],
) -> t.Any:
    """Render the options and commands that belong to no category."""
    section = utils.category("General")
    section.extend(
        utils.parse_text(
            "These options are accepted by every command and have to be "
            "placed before the category name, i.e. ``rally --debug task "
            "start ...`` and not ``rally task start --debug ...``."
        )
    )
    section.extend(
        make_arguments_section(
            "global", "options", cli, options_title="**Global options**:"
        )
    )
    for name in sorted(leaf_commands):
        section.append(make_command_section("", name, leaf_commands[name]))
    return section


def make_category_section(
    name: str, group: typer.core.TyperGroup | typer.core.TyperCommand
) -> t.Any:
    category_obj = utils.category(f"Category: {name}")
    description = group.help or ""
    # TODO(andreykurilin): write a decorator which will mark cli-class as
    #   deprecated without changing its docstring.
    if description.startswith("[Deprecated"):
        i = description.find("]")
        msg = description[1:i]
        description = description[i + 1 :].strip()
        category_obj.append(utils.warning(msg))
    elif name in DEPRECATED_CATEGORIES:
        category_obj.append(utils.warning(DEPRECATED_CATEGORIES[name]))
    category_obj.extend(
        utils.parse_text(description, source=f"<rally {name}>")
    )

    commands: dict[str, typer.core.TyperCommand] = getattr(
        group, "commands", {}
    )
    for command in sorted(commands):
        category_obj.append(
            make_command_section(name, command, commands[command])
        )
    return category_obj


class CLIReferenceDirective(rst.Directive):
    optional_arguments = 1
    option_spec = {"group": str}

    def run(self) -> list:
        cli = typer.main.get_command(main.app)
        groups = getattr(cli, "commands", {})
        categories = [
            c for c, g in groups.items() if getattr(g, "commands", None)
        ]
        content = []
        if "group" in self.options:
            # a single category is embedded into a component page; the global
            # options stay on the full reference only
            categories = [c for c in categories if c == self.options["group"]]
        else:
            leaves = dict(
                (c, g)
                for c, g in groups.items()
                if not getattr(g, "commands", None)
            )
            content.append(make_general_section(cli, leaves))

        for cg in sorted(categories):
            content.append(make_category_section(cg, groups[cg]))
        return content


def setup(app: t.Any) -> None:
    app.add_directive("make_cli_reference", CLIReferenceDirective)
