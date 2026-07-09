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
import sys
import typing as t
from unittest import mock

import ddt
import sqlalchemy.exc
import typer

from rally import exceptions
from rally.cli import cliutils
from rally.cli import main
from rally.common import logging
from tests.unit import test


class _Boom(exceptions.RallyException):
    error_code = 42
    msg_fmt = "boom"


class VersionTestCase(test.TestCase):

    @mock.patch("rally.common.version.plugins_versions", return_value={})
    def test_print_version(self, mock_plugins_versions):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            main.print_version()
        self.assertIn("Rally version:", out.getvalue())
        self.assertNotIn("Installed Plugins", out.getvalue())

    @mock.patch("rally.common.version.plugins_versions",
                return_value={"foo": "0.1"})
    def test_print_version_with_plugins(self, mock_plugins_versions):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            main.print_version()
        self.assertIn("Installed Plugins:", out.getvalue())
        self.assertIn("foo: 0.1", out.getvalue())

    @mock.patch("rally.cli.main.print_version")
    def test_version_callback_set(self, mock_print_version):
        self.assertRaises(typer.Exit, main._version_callback, True)
        mock_print_version.assert_called_once_with()

    @mock.patch("rally.cli.main.print_version")
    def test_version_callback_unset(self, mock_print_version):
        self.assertIsNone(main._version_callback(False))
        self.assertFalse(mock_print_version.called)


@ddt.ddt
class BootstrapTestCase(test.TestCase):

    def _ctx(self, subcommand="task"):
        ctx = mock.Mock()
        ctx.invoked_subcommand = subcommand
        ctx.help_option_names = ["--help"]
        return ctx

    @mock.patch("rally.cli.main.rally_api.API")
    @mock.patch("rally.cli.main.envutils.load_globals")
    def test_builds_and_stashes_api(self, mock_load_globals, mock_api):
        with mock.patch.object(sys, "argv", ["rally", "task", "status"]):
            main.bootstrap(self._ctx("task"), config_file=["c.conf"],
                           plugin_paths=["p1,p2", "p3"])
        mock_load_globals.assert_called_once_with()
        mock_api.assert_called_once_with(
            config_args=["--config-file", "c.conf"],
            plugin_paths=["p1", "p2", "p3"], skip_db_check=False)
        # the real ``set_api`` was used, so the handle is now retrievable
        self.assertIs(mock_api.return_value, cliutils.get_api())

    @ddt.data(("db", True), ("plugin", True), ("version", True),
              ("task", False), ("verify", False), ("deployment", False))
    @ddt.unpack
    @mock.patch("rally.cli.main.rally_api.API")
    @mock.patch("rally.cli.main.envutils.load_globals")
    def test_skip_db_check_per_group(self, subcommand, skip,
                                     mock_load_globals, mock_api):
        with mock.patch.object(sys, "argv", ["rally", subcommand, "x"]):
            main.bootstrap(self._ctx(subcommand))
        self.assertEqual(skip, mock_api.call_args[1]["skip_db_check"])

    @mock.patch("rally.cli.main.rally_api.API")
    @mock.patch("rally.cli.main.envutils.load_globals")
    def test_help_returns_before_touching_config(self, mock_load_globals,
                                                 mock_api):
        argv = ["rally", "task", "status", "--help"]
        with mock.patch.object(sys, "argv", argv):
            self.assertIsNone(main.bootstrap(self._ctx("task")))
        self.assertFalse(mock_load_globals.called)
        self.assertFalse(mock_api.called)

    @mock.patch("rally.cli.main.rally_api.API",
                side_effect=exceptions.RallyException("boom"))
    @mock.patch("rally.cli.main.envutils.load_globals")
    def test_api_error_exits_2(self, mock_load_globals, mock_api):
        with mock.patch.object(sys, "argv", ["rally", "task", "status"]), \
                mock.patch("sys.stdout", io.StringIO()):
            exc = self.assertRaises(typer.Exit, main.bootstrap,
                                    self._ctx("task"))
        self.assertEqual(2, exc.exit_code)


class InstallMultivalueTestCase(test.TestCase):

    def test_space_separated_multivalue(self):
        app = typer.Typer(no_args_is_help=False)
        group = typer.Typer()
        app.add_typer(group, name="task")
        seen = {}

        @group.command()
        def go(
            tag: t.Annotated[list[str] | None, typer.Option("--tag")] = None
        ) -> None:
            seen["tag"] = tag

        cli = typer.main.get_command(app)
        main._install_multivalue(cli)
        cli(["task", "go", "--tag", "a", "b", "c"], standalone_mode=False)
        self.assertEqual(["a", "b", "c"], seen["tag"])


@ddt.ddt
class MainExceptionHandlingTestCase(test.TestCase):
    """Drive the real ``main()`` path; only the external API is faked."""

    def _run(self, task_get):
        fake_api = mock.Mock()
        if isinstance(task_get, BaseException):
            fake_api.task.get.side_effect = task_get
        else:
            fake_api.task.get.return_value = task_get
        out = io.StringIO()
        with mock.patch.object(sys, "argv",
                               ["rally", "task", "status", "the-uuid"]), \
                mock.patch("rally.cli.main.rally_api.API",
                           return_value=fake_api), \
                mock.patch("rally.cli.main.envutils.load_globals"), \
                mock.patch("sys.stdout", out), \
                mock.patch("sys.stderr", io.StringIO()):
            try:
                main.main()
                code = 0
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
        return code, out.getvalue()

    def test_success(self):
        code, out = self._run({"status": "finished"})
        self.assertEqual(0, code)
        self.assertIn("finished", out)

    def test_rally_exception_uses_its_error_code(self):
        code, out = self._run(_Boom())
        self.assertEqual(42, code)
        self.assertIn("boom", out)

    def test_plain_exception_defaults_to_1(self):
        code, out = self._run(ValueError("nope"))
        self.assertEqual(1, code)
        self.assertIn("nope", out)

    @mock.patch("rally.cli.main.cfg")
    def test_operational_error_hints_at_db(self, mock_cfg):
        mock_cfg.CONF.database.connection = "mysql://user:secret@host/rally"
        code, out = self._run(
            sqlalchemy.exc.OperationalError("s", {}, Exception("refused")))
        self.assertEqual(1, code)
        self.assertIn("can't connect to its DB", out)
        self.assertIn("//**:**@host/rally", out)   # password is masked
        self.assertNotIn("secret", out)

    @mock.patch("rally.cli.main.logging.is_debug", return_value=True)
    def test_debug_logs_traceback_instead_of_printing(self, mock_is_debug):
        with logging.LogCatcher(main.LOG) as catcher:
            code, out = self._run(ValueError("nope"))
        self.assertEqual(1, code)
        self.assertNotIn("nope", out)
        catcher.assertInLogs("Unexpected exception in CLI")

    def test_unexpected_exception_is_reraised(self):
        with mock.patch.object(sys, "argv",
                               ["rally", "task", "status", "the-uuid"]), \
                mock.patch("rally.cli.main.rally_api.API") as mock_api, \
                mock.patch("rally.cli.main.envutils.load_globals"), \
                mock.patch("sys.stdout", io.StringIO()):
            mock_api.return_value.task.get.side_effect = KeyError("x")
            self.assertRaises(KeyError, main.main)
