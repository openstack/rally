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

import contextlib
import io
import os
import typing as t
from unittest import mock

import ddt
import typer

from rally.cli import argutils
from tests.unit import test


def _build(define: t.Callable) -> t.Any:
    """Build a two-level app, wire the parser, return the click command."""
    app = typer.Typer(no_args_is_help=False)
    group = typer.Typer()
    app.add_typer(group, name="task")
    define(group)
    cli = typer.main.get_command(app)
    argutils.install(cli)
    return cli


def _scalar_cli():
    def define(group):
        @group.command()
        def go(
            uuid: t.Annotated[
                str,
                argutils.ArgumentOrKeyword("--uuid", envvar="RALLY_TASK")
            ]
        ) -> None:
            print("UUID=%s" % uuid)
    return _build(define)


def _list_cli():
    def define(group):
        @group.command()
        def go(
            uuids: t.Annotated[
                list[str],
                argutils.ArgumentOrKeyword("--uuid")
            ]
        ) -> None:
            print("UUIDS=%s" % ",".join(uuids))
    return _build(define)


@ddt.ddt
class ArgumentOrKeywordTestCase(test.TestCase):
    """Exercise the actual click parser wiring, not the command functions."""

    def _invoke(self, cli, args, env=None):
        out = io.StringIO()
        code = 0
        with mock.patch.dict(os.environ, env or {}), \
                contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            try:
                cli(args, prog_name="rally", standalone_mode=True)
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
        return code, out.getvalue()

    @ddt.data(
        # positional, --flag, env-var default, and --flag winning over the env
        {"args": ["task", "go", "POS"], "env": "", "expected": "POS"},
        {"args": ["task", "go", "--uuid", "FLG"], "env": "",
         "expected": "FLG"},
        {"args": ["task", "go"], "env": "ENV", "expected": "ENV"},
        {"args": ["task", "go", "--uuid", "FLG"], "env": "ENV",
         "expected": "FLG"},
    )
    @ddt.unpack
    def test_scalar_resolves(self, args, env, expected):
        code, out = self._invoke(_scalar_cli(), args, env={"RALLY_TASK": env})
        self.assertEqual(0, code)
        self.assertIn("UUID=%s" % expected, out)

    @ddt.data(
        ["task", "go"],             # required: nothing given, no env
        ["task", "go", "--bogus"],  # ``--uuid`` is real, so a typo is rejected
        ["task", "go", "A", "B"],   # extra positional argument
    )
    def test_scalar_rejects(self, args):
        code, _ = self._invoke(_scalar_cli(), args, env={"RALLY_TASK": ""})
        self.assertEqual(2, code)

    @ddt.data(
        {"args": ["task", "go", "a", "b"], "expected": "a,b"},
        {"args": ["task", "go", "--uuid", "x", "--uuid", "y"],
         "expected": "x,y"},
    )
    @ddt.unpack
    def test_list_resolves(self, args, expected):
        code, out = self._invoke(_list_cli(), args)
        self.assertEqual(0, code)
        self.assertIn("UUIDS=%s" % expected, out)
