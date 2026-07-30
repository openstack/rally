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
    "deployment": ["rally deployment create"],
    "task": ["rally task start"],
    "verification": ["rally verify start", "rally verify import"],
}

# Maps the "use"-command hint for each default-from-environment id.
USE_CMD = {
    "deployment": "rally deployment use",
    "task": "rally task use",
    "verification": "rally verify use",
}

# Maps a parameter's env var to a default-uuid id.
_ENVVAR_DEST = {
    "RALLY_ENV": "deployment",
    "RALLY_DEPLOYMENT": "deployment",
    "RALLY_TASK": "task",
    "RALLY_VERIFICATION": "verification",
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


def _display_names(param: TyperParameter) -> t.Sequence[str]:
    """Return the flag(s)/name shown for a parameter."""
    if param.opts and param.opts[0].startswith("-"):
        return param.opts
    # A positional argument: show its metavar (e.g. ``UUID``) rather than the
    # internal destination name.
    if param.metavar:
        return [param.metavar]
    return param.opts or [param.name or ""]


def _iter_params(
    command: typer.core.TyperCommand,
) -> t.Iterator[TyperParameter]:
    """Yield the documentable parameters of a command (skip ``--help``)."""
    for param in command.params:
        if param.opts and param.opts[0] in ("--help", "-h", "--version"):
            continue
        if param.name == "help":
            continue
        yield t.cast("TyperParameter", param)


def make_arguments_section(
    category_name: str, cmd_name: str, command: typer.core.TyperCommand
) -> list:
    elements = [utils.paragraph("**Command arguments**:")]
    for param in _iter_params(command):
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

        if not getattr(param, "is_flag", False):
            type_name = getattr(getattr(param, "type", None), "name", None)
            if type_name:
                description.append("**Type**: %s" % type_name)

            default = getattr(param, "default", None)
            if note_dest is None and default is not None:
                description.append("**Default**: %s" % default)

        ref = "%s_%s_%s" % (
            category_name,
            cmd_name,
            flag.replace("-", "").replace(" ", ""),
        )
        elements.extend(
            utils.make_definition(", ".join(names), ref, description)
        )
    return elements


def make_command_section(
    category_name: str, name: str, command: typer.core.TyperCommand
) -> t.Any:
    section = utils.subcategory(f"rally {category_name} {name}")
    description = inspect.getdoc(command.callback) or command.help or ""
    section.extend(utils.parse_text(description))
    if any(True for _ in _iter_params(command)):
        section.extend(make_arguments_section(category_name, name, command))
    return section


def make_category_section(
    name: str, group: typer.core.TyperGroup | typer.core.TyperCommand
) -> t.Any:
    category_obj = utils.category("Category: %s" % name)
    description = group.help or ""
    # TODO(andreykurilin): write a decorator which will mark cli-class as
    #   deprecated without changing its docstring.
    if description.startswith("[Deprecated"):
        i = description.find("]")
        msg = description[1:i]
        description = description[i + 1 :].strip()
        category_obj.append(utils.warning(msg))
    category_obj.extend(utils.parse_text(description))

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
        # only command groups (skip top-level leaf commands like ``version``)
        categories = [
            c for c, g in groups.items() if getattr(g, "commands", None)
        ]
        if "group" in self.options:
            categories = [c for c in categories if c == self.options["group"]]

        content = []
        for cg in sorted(categories):
            content.append(make_category_section(cg, groups[cg]))
        return content


def setup(app: t.Any) -> None:
    app.add_directive("make_cli_reference", CLIReferenceDirective)
