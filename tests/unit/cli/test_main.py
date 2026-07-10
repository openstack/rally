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

import sys
from unittest import mock

import sqlalchemy.exc

from rally import exceptions
from rally.cli import cliutils
from rally.cli import main
from rally.common import logging
from tests.unit.cli import test as cli_test


class _Boom(exceptions.RallyException):
    error_code = 42
    msg_fmt = "boom"


class VersionTestCase(cli_test.CLITestCase):

    APPLY_DB_SCHEMA = False

    @mock.patch("rally.common.version.plugins_versions", return_value={})
    def test_print_version(self, mock_plugins_versions):
        result = self.invoke(["version"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Rally version:", result.output)
        self.assertNotIn("Installed Plugins", result.output)

    @mock.patch("rally.common.version.plugins_versions",
                return_value={"foo": "0.1"})
    def test_print_version_with_plugins(self, mock_plugins_versions):
        result = self.invoke(["version"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Installed Plugins:", result.output)
        self.assertIn("foo: 0.1", result.output)

    @mock.patch("rally.common.version.plugins_versions", return_value={})
    def test_version_flag(self, mock_plugins_versions):
        # the eager --version option prints the version and exits
        result = self.invoke(["--version"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Rally version:", result.output)


class BootstrapTestCase(cli_test.CLITestCase):

    APPLY_DB_SCHEMA = False

    @mock.patch("rally.cli.main.rally_api.API")
    def test_builds_and_stashes_api(self, mock_api):
        self.invoke(["--config-file", "c.conf", "--plugin-paths", "p1,p2",
                     "--plugin-paths", "p3", "plugin", "list"])
        mock_api.assert_called_once_with(
            config_args=["--config-file", "c.conf"],
            plugin_paths=["p1", "p2", "p3"], skip_db_check=True)
        # bootstrap stashed the built API via the real ``set_api``
        self.assertIs(mock_api.return_value, cliutils.get_api())

    @mock.patch("rally.cli.main.rally_api.API")
    def test_skip_db_check_per_group(self, mock_api):
        for subcommand, skip in (("db", True), ("plugin", True),
                                 ("version", True), ("task", False),
                                 ("verify", False), ("deployment", False)):
            with self.subTest(subcommand=subcommand):
                mock_api.reset_mock()
                self.invoke([subcommand])
                self.assertEqual(
                    skip, mock_api.call_args.kwargs["skip_db_check"])

    @mock.patch("rally.cli.main.rally_api.API")
    def test_help_returns_before_touching_config(self, mock_api):
        # bootstrap short-circuits on --help (detected via sys.argv) and never
        # builds the API
        with mock.patch.object(sys, "argv", ["rally", "task", "--help"]):
            result = self.invoke(["task", "--help"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertFalse(mock_api.called)
        self.assertIn("Usage", result.output)

    @mock.patch("rally.cli.main.rally_api.API",
                side_effect=exceptions.RallyException("boom"))
    def test_api_error_exits_2(self, mock_api):
        result = self.invoke(["task", "list"])
        self.assertEqual(2, result.exit_code)
        self.assertIn("boom", result.output)


class InstallMultivalueTestCase(cli_test.CLITestCase):

    @mock.patch("rally.api._Verification.list", return_value=[])
    def test_space_separated_multivalue(self, mock_list):
        # ``--tag a b c`` (space-separated) is collected into a list by the
        # real multi-value wiring installed on the CLI
        result = self.invoke(["verify", "list", "--tag", "a", "b", "c"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(["a", "b", "c"],
                         mock_list.call_args.kwargs["tags"])


class MainExceptionHandlingTestCase(cli_test.CLITestCase):
    """Drive the real ``main()`` path; only the external API is faked."""

    def _run(self, task_get):
        # ``task status`` calls the real ``api.task.get``; patch just that one
        # method to drive ``main()``'s error handling from a real API.
        kwargs = ({"side_effect": task_get}
                  if isinstance(task_get, BaseException)
                  else {"return_value": task_get})
        with mock.patch("rally.api._Task.get", **kwargs):
            return self.invoke(["task", "status", "the-uuid"])

    def test_success(self):
        result = self._run({"status": "finished"})
        self.assertEqual(0, result.exit_code)
        self.assertIn("finished", result.output)

    def test_rally_exception_uses_its_error_code(self):
        result = self._run(_Boom())
        self.assertEqual(42, result.exit_code)
        self.assertIn("boom", result.output)

    def test_plain_exception_defaults_to_1(self):
        result = self._run(ValueError("nope"))
        self.assertEqual(1, result.exit_code)
        self.assertIn("nope", result.output)

    @mock.patch("rally.cli.main.cfg")
    def test_operational_error_hints_at_db(self, mock_cfg):
        mock_cfg.CONF.database.connection = "mysql://user:secret@host/rally"
        result = self._run(
            sqlalchemy.exc.OperationalError("s", {}, Exception("refused")))
        self.assertEqual(1, result.exit_code)
        self.assertIn("can't connect to its DB", result.output)
        self.assertIn("//**:**@host/rally", result.output)  # password masked
        self.assertNotIn("secret", result.output)

    @mock.patch("rally.cli.main.logging.is_debug", return_value=True)
    def test_debug_logs_traceback_instead_of_printing(self, mock_is_debug):
        with logging.LogCatcher(main.LOG) as catcher:
            result = self._run(ValueError("nope"))
        self.assertEqual(1, result.exit_code)
        # the traceback is logged (to stderr), not printed to stdout
        self.assertNotIn("nope", result.stdout)
        catcher.assertInLogs("Unexpected exception in CLI")

    @mock.patch("rally.api._Task.get", side_effect=KeyError("x"))
    def test_unexpected_exception_is_reraised(self, mock_get):
        self.assertRaises(KeyError, self.invoke,
                          ["task", "status", "the-uuid"])
