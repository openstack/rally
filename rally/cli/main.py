# Copyright 2013: Mirantis Inc.
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

"""CLI interface for Rally."""

import inspect
import re
import sys
import typing as t

import jsonschema
import sqlalchemy.exc
import typer

from rally import api as rally_api
from rally import exceptions
from rally.cli import argutils
from rally.cli import cliutils
from rally.cli import envutils
from rally.cli.commands.db import db_app
from rally.cli.commands.deployment import deployment_app
from rally.cli.commands.env import env_app
from rally.cli.commands.plugin import plugin_app
from rally.cli.commands.task import task_app
from rally.cli.commands.verify import verify_app
from rally.common import cfg
from rally.common import logging


LOG = logging.getLogger(__name__)


if t.TYPE_CHECKING:
    import typer.core


# ``no_args_is_help=False`` -> a bare ``rally`` / ``rally task`` errors with
# "Missing command." (exit 2) instead of printing help.
app = typer.Typer(name="rally", help="Rally command-line interface.",
                  no_args_is_help=False, add_completion=True)

app.add_typer(db_app, name="db")
app.add_typer(deployment_app, name="deployment")
app.add_typer(env_app, name="env")
app.add_typer(plugin_app, name="plugin")
app.add_typer(task_app, name="task")
app.add_typer(verify_app, name="verify")


@app.command(name="version")
def print_version() -> None:
    """Print the Rally version."""
    from rally.common import version

    lines = ["Rally version: %s" % version.__version__]
    packages = version.plugins_versions()
    if packages:
        lines.append("\nInstalled Plugins:")
        lines.extend("\t%s: %s" % p for p in sorted(packages.items()))
    print("\n".join(lines))


def _version_callback(value: bool) -> None:
    if value:
        print_version()
        raise typer.Exit()


def _expand_signature(
    build_params: t.Callable[[], list[inspect.Parameter]]
) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
    """Replace a function's ``**kwargs`` with dynamically-generated parameters.

    typer reads the callback signature via :func:`inspect.signature`, so the
    fixed options can be written as an ordinary signature while the variable
    ``**kwargs`` tail is swapped for whatever ``build_params`` yields (here the
    ``oslo.log`` CLI options generated from oslo's own ``Opt`` objects, so
    ``--log-file`` etc. stay in sync).  The generated options arrive as keyword
    arguments -- i.e. in the real ``**kwargs`` at call time.
    """
    def decorator(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        signature = inspect.signature(func)
        fixed = [p for p in signature.parameters.values()
                 if p.kind is not inspect.Parameter.VAR_KEYWORD]
        func.__signature__ = signature.replace(  # type: ignore[attr-defined]
            parameters=fixed + list(build_params()))
        return func
    return decorator


@app.callback()
@_expand_signature(logging.build_cli_params)
def bootstrap(
    ctx: typer.Context,
    config_file: t.Annotated[
        list[str] | None,
        typer.Option(
            help="Path to a config file. Repeatable; later files take "
                 "precedence."
        )
    ] = None,
    config_dir: t.Annotated[
        list[str] | None,
        typer.Option(
            help="Path to a config directory. Repeatable."
        )
    ] = None,
    plugin_paths: t.Annotated[
        list[str] | None,
        typer.Option(
            envvar="RALLY_PLUGIN_PATHS",
            help="Additional custom plugin locations."
        )
    ] = None,
    version: t.Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Print the Rally version and exit."
        )
    ] = False,
    **kwargs: t.Any,
) -> None:
    """Build the API and expose it to the sub-commands."""
    if any(opt in sys.argv[1:] for opt in ctx.help_option_names):
        return
    envutils.load_globals()
    config_args: list[str] = []
    for path in config_file or []:
        config_args += ["--config-file", path]
    for path in config_dir or []:
        config_args += ["--config-dir", path]
    config_args += logging.to_oslo_argv(kwargs)

    paths = None
    if plugin_paths:
        paths = [p for item in plugin_paths
                 for p in item.split(",") if p]

    # do not run database check on commands that does not need that
    skip_db_check = ctx.invoked_subcommand in ("db", "plugin", "version")
    try:
        api = rally_api.API(config_args=config_args, plugin_paths=paths,
                            skip_db_check=skip_db_check)
    except exceptions.RallyException as e:
        print(e)
        raise typer.Exit(code=2)
    cliutils.set_api(api)


def _eat_all(param: "typer.core.TyperOption") -> None:
    """Make one multi-value option consume space-separated values.

    typer options are repeated-flag by default (``--tag a --tag b``); Rally
    historically accepted the space-separated ``--tag a b c`` (argparse
    ``nargs="+"``).  There is no per-parameter hook for this, so we override
    the option's parser to grab the following tokens up to the next flag.
    """
    original_add_to_parser = param.add_to_parser

    def add_to_parser(parser: t.Any, ctx: t.Any) -> None:
        original_add_to_parser(parser, ctx)
        for opt in param.opts:
            handler = parser._long_opt.get(opt) or parser._short_opt.get(opt)
            if handler is None:
                continue
            previous_process = handler.process

            def process(value: t.Any, state: t.Any,
                        _prev: t.Any = previous_process) -> None:
                values = [value]
                while state.rargs and not state.rargs[0].startswith("-"):
                    values.append(state.rargs.pop(0))
                for item in values:
                    _prev(item, state)
            handler.process = process
            break

    param.add_to_parser = add_to_parser  # type: ignore[method-assign]


def _install_multivalue(
        command: "typer.core.TyperGroup | typer.core.TyperCommand"
) -> None:
    """Apply :func:`_eat_all` to every multi-value option in the tree."""
    for _path, _leaf, params in cliutils.iter_commands(command):
        for param in params:
            if param.multiple and param.opts and param.opts[0].startswith("-"):
                _eat_all(param)


def main() -> None:
    cli: "typer.core.TyperGroup" = (
        typer.main.get_command(app)  # type: ignore[assignment]
    )
    _install_multivalue(cli)
    argutils.install(cli)
    try:
        cli()
    except (OSError, TypeError, ValueError, exceptions.RallyException,
            jsonschema.ValidationError) as e:
        if (logging.is_debug()
                and not isinstance(e, exceptions.InvalidTaskConfig)):
            LOG.exception("Unexpected exception in CLI")
        else:
            print(e)
        sys.exit(getattr(e, "error_code", 1))
    except sqlalchemy.exc.OperationalError as e:
        if logging.is_debug():
            LOG.exception("Something went wrong with the database")
        print(e)
        print("Looks like Rally can't connect to its DB.")
        print("Make sure the connection string in rally.conf is proper:")
        print(re.sub("//[^@]*@", "//**:**@", cfg.CONF.database.connection))
        sys.exit(1)
    except Exception:
        print("Command failed, please check log for more info")
        raise


if __name__ == "__main__":  # pragma: no cover
    main()
