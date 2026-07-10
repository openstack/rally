# Copyright 2014: Mirantis Inc.
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

import datetime as dt
import os
import tempfile
from unittest import mock

from rally import consts
from rally import exceptions
from rally.cli.commands import verify
from rally.common import db
from rally.common import objects
from rally.env import env_mgr
from rally.verification import manager
from rally.verification import reporter
from tests.unit.cli import test


@manager.configure("fake-verifier-tool", platform="tests")
class FakeVerifierManager(manager.VerifierManager):
    """A verifier plugin whose external steps are no-ops, for CLI tests."""

    def run(self, context):
        pass

    def list_tests(self, pattern=""):
        return []


# results returned by a verification run, shared by start/rerun/import tests
RESULTS = {
    "totals": {"tests_count": 2, "tests_duration": "4", "success": 2,
               "skipped": 0, "expected_failures": 0, "unexpected_success": 0,
               "failures": 0},
    "tests": {
        "test_1": {"name": "test_1", "status": "success", "duration": 2,
                   "tags": []},
        "test_2": {"name": "test_2", "status": "success", "duration": 2,
                   "tags": []},
    },
}


class VerifyCommandsTestCase(test.CLITestCase):

    def _create_verifier(self, name="My Verifier",
                         vtype="fake-verifier-tool", platform="tests",
                         system_wide=False, **kwargs):
        """Insert a real verifier row and return the object."""
        return objects.Verifier.create(
            name=name, vtype=vtype, platform=platform, source=None,
            version=None, system_wide=system_wide, **kwargs)

    def _create_env(self, name="Some Deploy"):
        """Insert a real environment (deployment) row and return its dict."""
        from rally.common import db
        db.env_create(name=name, status=env_mgr.STATUS.READY,
                      description="", extras={}, config={}, spec={},
                      platforms=[])
        return db.env_get(name)

    def _create_verification(self, tags=None, run_args=None):
        """Insert a real verifier + env + verification; return all three."""
        from rally.common import db
        verifier = self._create_verifier()
        env = self._create_env()
        verification = db.verification_create(
            verifier_id=verifier.uuid, env=env["uuid"], tags=tags,
            run_args=run_args)
        return verifier, env, verification

    def test_list_plugins(self):
        # the fake plugin is registered, so a real listing includes it; the
        # no-platform branch and the debug-only Location column are covered too
        for args, debug in (([], False), (["--platform", "TESTS"], True)):
            with self.subTest(args=args, debug=debug):
                with mock.patch("rally.cli.commands.verify.logging.is_debug",
                                return_value=debug):
                    result = self.invoke(["verify", "list-plugins", *args])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn("fake-verifier-tool", result.output)

    @mock.patch("rally.verification.manager.VerifierManager.install")
    def test_create_verifier(self, mock_verifier_manager_install):
        # install clones/builds the repo -- stub that one external step
        result = self.invoke([
            "verify", "create-verifier", "--name", "My Verifier",
            "--type", "fake-verifier-tool", "--platform", "tests",
            "--source", "https://example.com/repo"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Using verifier", result.output)
        self.assertEqual("My Verifier",
                         objects.Verifier.get("My Verifier").name)

        # --no-use creates the verifier without making it the default
        result = self.invoke([
            "verify", "create-verifier", "--name", "Other",
            "--type", "fake-verifier-tool", "--platform", "tests",
            "--source", "https://example.com/repo", "--no-use"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("Using verifier", result.output)
        self.assertEqual("Other", objects.Verifier.get("Other").name)

    def test_use_verifier(self):
        verifier = self._create_verifier()

        result = self.invoke(["verify", "use-verifier", verifier.uuid])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(verifier.uuid, result.output)
        self.assertIn("as the default verifier", result.output)

    def test_list_verifiers_empty_verifiers(self):
        for args, expected in (
            ([], "There are no verifiers."),
            (["--status", "foo"],
             "There are no verifiers with status 'foo'."),
        ):
            with self.subTest(args=args):
                result = self.invoke(["verify", "list-verifiers", *args])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(expected, result.output)

    def test_list_verifiers(self):
        verifier = self._create_verifier()

        result = self.invoke(["verify", "list-verifiers"])

        self.assertEqual(0, result.exit_code, result.output)
        # the table width depends on values, so assert on the stable columns
        for expected in (verifier.uuid, "My Verifier", "fake-verifier-tool",
                         "tests"):
            self.assertIn(expected, result.output)

    def test_show_verifier(self):
        verifier = self._create_verifier(name="My Verifier")
        # pin the volatile fields so the whole table is reproducible
        db.verifier_update(
            verifier.uuid, status="installed", source="https://example.com",
            version="master", description="The best tool in the world",
            created_at=dt.datetime(2016, 1, 1, 17, 0, 3),
            updated_at=dt.datetime(2016, 1, 1, 17, 1, 5))

        with mock.patch("rally.cli.commands.verify._base_dir",
                        return_value="./verifiers"):
            result = self.invoke(["verify", "show-verifier", verifier.uuid])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(
            "+-------------------------------------------------------+\n"
            "|                       Verifier                        |\n"
            "+----------------+--------------------------------------+\n"
            "| UUID           | %s |\n"
            "| Status         | installed                            |\n"
            "| Created at     | 2016-01-01 17:00:03                  |\n"
            "| Updated at     | 2016-01-01 17:01:05                  |\n"
            "| Active         | -                                    |\n"
            "| Name           | My Verifier                          |\n"
            "| Description    | The best tool in the world           |\n"
            "| Type           | fake-verifier-tool                   |\n"
            "| Platform       | tests                                |\n"
            "| Source         | https://example.com                  |\n"
            "| Version        | master                               |\n"
            "| System-wide    | False                                |\n"
            "| Extra settings | -                                    |\n"
            "| Location       | ./verifiers/repo                     |\n"
            "| Venv location  | ./verifiers/.venv                    |\n"
            "+----------------+--------------------------------------+\n"
            "Attention! All you do in the verifier repository or verifier "
            "virtual environment, you do it at your own risk!\n"
            % verifier.uuid, result.output)

    def test_delete_verifier(self):
        verifier = self._create_verifier()

        result = self.invoke(["verify", "delete-verifier", verifier.uuid])
        self.assertEqual(0, result.exit_code, result.output)

        # the row is really gone from the DB
        after = self.invoke(["verify", "list-verifiers"])
        self.assertIn("There are no verifiers.", after.output)

    @mock.patch("rally.api._Verifier.update")
    def test_update_verifier(self, mock_update):
        verifier = self._create_verifier()

        # the mutually-exclusive / empty argument combinations exit with 1
        # before touching the API
        for args in ([],
                     ["--update-venv", "--system-wide"],
                     ["--system-wide", "--no-system-wide"]):
            with self.subTest(args=args):
                result = self.invoke(
                    ["verify", "update-verifier", verifier.uuid, *args])
                self.assertEqual(1, result.exit_code, result.output)
                self.assertFalse(mock_update.called)

        # a valid combination reaches the API with translated arguments
        result = self.invoke([
            "verify", "update-verifier", verifier.uuid,
            "--version", "a", "--system-wide"])
        self.assertEqual(0, result.exit_code, result.output)
        mock_update.assert_called_once_with(
            verifier_id=verifier.uuid, system_wide=True, version="a",
            update_venv=False)

    @mock.patch("rally.api._Verifier.override_configuration")
    @mock.patch("rally.api._Verifier.configure")
    def test_configure_verifier(self, mock_configure,
                                mock_override_configuration):
        verifier = self._create_verifier()
        env = self._create_env()
        mock_configure.return_value = "config-body"

        # --override cannot be combined with --reconfigure/--extend
        result = self.invoke([
            "verify", "configure-verifier", verifier.uuid,
            "--deployment-id", env["uuid"], "--override", "/p/a/t/h",
            "--reconfigure", "--show"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertFalse(mock_configure.called)

        # a missing --override file is reported and exits 1
        result = self.invoke([
            "verify", "configure-verifier", verifier.uuid,
            "--deployment-id", env["uuid"], "--override", "/p/a/t/h",
            "--show"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("not found", result.output)

        # a real --override file replaces the whole configuration
        with tempfile.NamedTemporaryFile("w") as tf:
            tf.write("new-config")
            tf.flush()
            result = self.invoke([
                "verify", "configure-verifier", verifier.uuid,
                "--deployment-id", env["uuid"], "--override", tf.name])
        self.assertEqual(0, result.exit_code, result.output)
        mock_override_configuration.assert_called_once_with(
            verifier_id=verifier.uuid, deployment_id=env["uuid"],
            new_configuration="new-config")

        # an ini config file is parsed into the options dict passed to the API
        with tempfile.NamedTemporaryFile("w", suffix=".conf") as tf:
            tf.write("[DEFAULT]\nopt = val\n[foo]\nopt = val")
            tf.flush()
            result = self.invoke([
                "verify", "configure-verifier", verifier.uuid,
                "--deployment-id", env["uuid"], "--extend", tf.name])
        self.assertEqual(0, result.exit_code, result.output)
        mock_configure.assert_called_once_with(
            verifier=verifier.uuid, deployment_id=env["uuid"],
            extra_options={"foo": {"opt": "val"}, "DEFAULT": {"opt": "val"}},
            reconfigure=False)

        # a raw json/yaml value is parsed, and --show prints the config
        result = self.invoke([
            "verify", "configure-verifier", verifier.uuid,
            "--deployment-id", env["uuid"], "--extend", "{foo: {opt: val}}",
            "--show"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("config-body", result.output)
        self.assertEqual({"foo": {"opt": "val"}},
                         mock_configure.call_args.kwargs["extra_options"])

    def test_list_verifier_tests(self):
        verifier = self._create_verifier()
        verifier.update_status(consts.VerifierStatus.INSTALLED)

        # the fake verifier has no tests -> real "nothing found" path
        result = self.invoke([
            "verify", "list-verifier-tests", verifier.uuid, "--pattern", "p"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("No tests found.", result.output)

        with mock.patch("rally.api._Verifier.list_tests",
                        return_value=["test_1", "test_2"]):
            result = self.invoke([
                "verify", "list-verifier-tests", verifier.uuid])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("test_1", result.output)
        self.assertIn("test_2", result.output)

    @mock.patch("rally.api._Verifier.add_extension")
    def test_add_verifier_ext(self, mock_add_extension):
        verifier = self._create_verifier()

        result = self.invoke([
            "verify", "add-verifier-ext", verifier.uuid,
            "--source", "a", "--version", "b", "--extra-settings", "c"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_add_extension.assert_called_once_with(
            verifier_id=verifier.uuid, source="a", version="b",
            extra_settings="c")

    def test_list_verifier_exts(self):
        verifier = self._create_verifier()
        ext = {"name": "ext_1", "entry_point": "foo.bar", "location": "/loc"}

        # empty list -> the "no extensions" hint
        with mock.patch("rally.api._Verifier.list_extensions",
                        return_value=[]):
            result = self.invoke([
                "verify", "list-verifier-exts", verifier.uuid])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("There are no verifier extensions.", result.output)

        # populated -> a table with the extension name (Location column only
        # shown in debug mode)
        for debug in (False, True):
            with self.subTest(debug=debug):
                with mock.patch("rally.api._Verifier.list_extensions",
                                return_value=[ext]), \
                        mock.patch("rally.cli.commands.verify.logging."
                                   "is_debug", return_value=debug):
                    result = self.invoke([
                        "verify", "list-verifier-exts", verifier.uuid])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn("ext_1", result.output)
                self.assertEqual(debug, "/loc" in result.output)

    @mock.patch("rally.api._Verifier.delete_extension")
    def test_delete_verifier_ext(self, mock_delete_extension):
        verifier = self._create_verifier()

        result = self.invoke([
            "verify", "delete-verifier-ext", verifier.uuid,
            "--name", "ext_name"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_delete_extension.assert_called_once_with(
            verifier_id=verifier.uuid, name="ext_name")

    @mock.patch("rally.api._Verification.start")
    def test_start(self, mock_start):
        verifier, env, verification = self._create_verification()
        mock_start.return_value = {
            "verification": verification,
            "totals": RESULTS["totals"], "tests": RESULTS["tests"]}

        # --pattern and --load-list are mutually exclusive
        result = self.invoke([
            "verify", "start", verifier.uuid, "--deployment-id", env["uuid"],
            "--pattern", "p", "--load-list", "/p/a/t/h"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertFalse(mock_start.called)

        # a missing list file is reported and exits 1
        result = self.invoke([
            "verify", "start", verifier.uuid, "--deployment-id", env["uuid"],
            "--load-list", "/p/a/t/h"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertFalse(mock_start.called)

        # a real list file is parsed and forwarded to the API
        with tempfile.NamedTemporaryFile("w") as tf:
            tf.write("test_1\ntest_2")
            tf.flush()
            result = self.invoke([
                "verify", "start", verifier.uuid, "--deployment-id",
                env["uuid"], "--tag", "foo", "--load-list", tf.name])
        self.assertEqual(0, result.exit_code, result.output)
        mock_start.assert_called_once_with(
            verifier_id=verifier.uuid, deployment_id=env["uuid"],
            tags=["foo"], load_list=["test_1", "test_2"])

        # --skip-list / --xfail-list: a missing file exits 1, a real file is
        # parsed into a {test: reason} dict and forwarded
        for opt, key in (("--skip-list", "skip_list"),
                         ("--xfail-list", "xfail_list")):
            with self.subTest(opt=opt):
                mock_start.reset_mock()
                result = self.invoke([
                    "verify", "start", verifier.uuid, "--deployment-id",
                    env["uuid"], opt, "/p/a/t/h"])
                self.assertEqual(1, result.exit_code, result.output)
                self.assertFalse(mock_start.called)

                with tempfile.NamedTemporaryFile("w") as tf:
                    tf.write("test_1:\ntest_2: Reason\n")
                    tf.flush()
                    result = self.invoke([
                        "verify", "start", verifier.uuid, "--deployment-id",
                        env["uuid"], opt, tf.name])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertEqual({"test_1": None, "test_2": "Reason"},
                                 mock_start.call_args.kwargs[key])

        # --detailed prints failing tests, --no-use prints the UUID, and a
        # failed run exits 3
        mock_start.return_value = {
            "verification": verification,
            "totals": {**RESULTS["totals"], "failures": 1},
            "tests": {"t": {"name": "t", "status": "fail",
                            "traceback": "boom-trace"}}}
        result = self.invoke([
            "verify", "start", verifier.uuid, "--deployment-id", env["uuid"],
            "--detailed", "--no-use"])
        self.assertEqual(3, result.exit_code, result.output)
        self.assertIn("boom-trace", result.output)
        self.assertIn("Verification UUID", result.output)

        # an unexpected success exits 2
        mock_start.return_value = {
            "verification": verification,
            "totals": {**RESULTS["totals"], "unexpected_success": 1},
            "tests": RESULTS["tests"]}
        result = self.invoke([
            "verify", "start", verifier.uuid, "--deployment-id", env["uuid"]])
        self.assertEqual(2, result.exit_code, result.output)

    @mock.patch("rally.api._Verification.start")
    def test_start_on_unfinished_deployment(self, mock_start):
        verifier, env, _verification = self._create_verification()
        mock_start.side_effect = exceptions.DeploymentNotFinishedStatus(
            name="Some Deploy", uuid=env["uuid"],
            status=consts.DeployStatus.DEPLOY_INIT)

        result = self.invoke([
            "verify", "start", verifier.uuid, "--deployment-id", env["uuid"]])

        self.assertEqual(1, result.exit_code, result.output)

    def test_use(self):
        _verifier, _env, verification = self._create_verification()

        result = self.invoke(["verify", "use", verification["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(verification["uuid"], result.output)
        self.assertIn("as the default verification", result.output)

    @mock.patch("rally.api._Verification.rerun")
    def test_rerun(self, mock_rerun):
        verifier, env, verification = self._create_verification()
        mock_rerun.return_value = {
            "verification": verification,
            "totals": RESULTS["totals"], "tests": RESULTS["tests"]}

        result = self.invoke([
            "verify", "rerun", verification["uuid"], "--deployment-id",
            env["uuid"], "--failed"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_rerun.assert_called_once_with(
            verification_uuid=verification["uuid"], concurrency=None,
            deployment_id=env["uuid"], failed=True, tags=None)

        # --detailed prints failing tests; --no-use prints the UUID
        mock_rerun.return_value = {
            "verification": verification,
            "totals": {**RESULTS["totals"], "failures": 1},
            "tests": {"t": {"name": "t", "status": "fail",
                            "traceback": "boom-trace"}}}
        result = self.invoke([
            "verify", "rerun", verification["uuid"], "--deployment-id",
            env["uuid"], "--detailed", "--no-use"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("boom-trace", result.output)
        self.assertIn("Verification UUID", result.output)

    @mock.patch("rally.api._Verification.get")
    def test_show(self, mock_get):
        verifier, env, verification = self._create_verification()
        # a failing test with a traceback and long run-args cannot be seeded
        # through the DB, so feed them via the one getter the command reads.
        mock_get.return_value = {
            "uuid": verification["uuid"], "verifier_uuid": verifier.uuid,
            "deployment_uuid": env["uuid"], "status": "finished",
            "created_at": "2026-01-01T17:00:03",
            "updated_at": "2026-01-01T17:01:05",
            "tests_count": 1, "tests_duration": 1, "success": 0, "skipped": 0,
            "expected_failures": 0, "unexpected_success": 0, "failures": 1,
            "tags": ["foo"],
            "run_args": {"load_list": ["t1", "t2"], "concurrency": "3"},
            "tests": {"t": {"name": "t", "status": "fail", "duration": 1,
                            "traceback": "boom-trace"}}}

        # plain view summarises the long run-args
        result = self.invoke(["verify", "show", verification["uuid"]])
        self.assertEqual(0, result.exit_code, result.output)
        # mask the random UUIDs to fixed-width (36-char) sentinels so the whole
        # table can be compared, layout intact.
        out = result.output
        for real, fake in ((verification["uuid"], "U" * 36),
                           (verifier.uuid, "R" * 36), (env["uuid"], "E" * 36)):
            out = out.replace(real, fake)
        self.assertEqual(
            "+----------------------------------------------------------------"
            "-------------------------+\n"
            "|                                      Verification              "
            "                         |\n"
            "+---------------------+------------------------------------------"
            "-------------------------+\n"
            "| UUID                | UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU     "
            "                         |\n"
            "| Status              | finished                                 "
            "                         |\n"
            "| Started at          | 2026-01-01 17:00:03                      "
            "                         |\n"
            "| Finished at         | 2026-01-01 17:01:05                      "
            "                         |\n"
            "| Duration            | 0:01:02                                  "
            "                         |\n"
            "| Run arguments       | concurrency: 3                           "
            "                         |\n"
            "|                     | load_list: (value is too long, use 'detai"
            "led' flag to display it) |\n"
            "| Tags                | foo                                      "
            "                         |\n"
            "| Verifier name       | My Verifier (UUID: RRRRRRRRRRRRRRRRRRRRRR"
            "RRRRRRRRRRRRRR)          |\n"
            "| Verifier type       | fake-verifier-tool (platform: tests)     "
            "                         |\n"
            "| Deployment name     | Some Deploy (UUID: EEEEEEEEEEEEEEEEEEEEEE"
            "EEEEEEEEEEEEEE)          |\n"
            "| Tests count         | 1                                        "
            "                         |\n"
            "| Tests duration, sec | 1                                        "
            "                         |\n"
            "| Success             | 0                                        "
            "                         |\n"
            "| Skipped             | 0                                        "
            "                         |\n"
            "| Expected failures   | 0                                        "
            "                         |\n"
            "| Unexpected success  | 0                                        "
            "                         |\n"
            "| Failures            | 1                                        "
            "                         |\n"
            "+---------------------+------------------------------------------"
            "-------------------------+\n"
            "+-------------------------------+\n"
            "|             Tests             |\n"
            "+------+---------------+--------+\n"
            "| Name | Duration, sec | Status |\n"
            "+------+---------------+--------+\n"
            "| t    | 1             | fail   |\n"
            "+------+---------------+--------+\n",
            out)

        # detailed view prints the full run-args JSON and the failure traceback
        result = self.invoke([
            "verify", "show", verification["uuid"], "--detailed"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("boom-trace", result.output)
        self.assertIn("load_list", result.output)

    def test_list_empty_verifications(self):
        verifier = self._create_verifier()
        env = self._create_env()

        for args, expected in (
            ([], "There are no verifications."),
            (["--id", verifier.uuid, "--deployment-id", env["uuid"],
              "--status", "bar"],
             "There are no verifications that meet specified criteria."),
        ):
            with self.subTest(args=args):
                result = self.invoke(["verify", "list", *args])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(expected, result.output)

    def test_list(self):
        verifier, env, verification = self._create_verification()

        result = self.invoke(["verify", "list"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(verification["uuid"], result.output)
        self.assertIn("My Verifier", result.output)

    def test_delete(self):
        _verifier, _env, verification = self._create_verification()

        result = self.invoke(["verify", "delete", verification["uuid"]])
        self.assertEqual(0, result.exit_code, result.output)

        # the verification is really gone
        after = self.invoke(["verify", "list"])
        self.assertIn("There are no verifications.", after.output)

    @mock.patch("rally.cli.commands.verify.webbrowser.open_new_tab")
    @mock.patch("rally.api._Verification.report")
    def test_report(self, mock_report, mock_open_new_tab):
        _verifier, _env, verification = self._create_verification()

        # a "print" report is echoed to the console
        mock_report.return_value = {"print": "the report body"}
        result = self.invoke([
            "verify", "report", verification["uuid"], "--type", "json"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("the report body", result.output)
        mock_report.assert_called_once_with(
            uuids=[verification["uuid"]], output_type="json", output_dest=None)

        # a file report is written to disk (creating parents) and opened
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "sub", "report.html")
            mock_report.return_value = {"files": {dest: "<html/>"},
                                        "open": dest}
            result = self.invoke([
                "verify", "report", verification["uuid"], "--type", "html",
                "--to", dest, "--open"])
            self.assertEqual(0, result.exit_code, result.output)
            with open(dest) as f:
                self.assertEqual("<html/>", f.read())
        mock_open_new_tab.assert_called_once()

    @mock.patch("rally.api._Verification.import_results")
    def test_import_results(self, mock_import_results):
        verifier, env, verification = self._create_verification()
        mock_import_results.return_value = (verification, RESULTS)

        # a missing input file is reported and exits 1
        result = self.invoke([
            "verify", "import", verifier.uuid, "--deployment-id", env["uuid"],
            "--file", "/p/a/t/h"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertFalse(mock_import_results.called)

        # a real file is read and forwarded to the API
        with tempfile.NamedTemporaryFile("w") as tf:
            tf.write("data")
            tf.flush()
            result = self.invoke([
                "verify", "import", verifier.uuid, "--deployment-id",
                env["uuid"], "--file", tf.name])
        self.assertEqual(0, result.exit_code, result.output)
        mock_import_results.assert_called_once_with(
            verifier_id=verifier.uuid, deployment_id=env["uuid"], data="data")

        # --no-use imports without setting the default verification
        with tempfile.NamedTemporaryFile("w") as tf:
            tf.write("data")
            tf.flush()
            result = self.invoke([
                "verify", "import", verifier.uuid, "--deployment-id",
                env["uuid"], "--file", tf.name, "--no-use"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Verification UUID", result.output)

    def test_default_reporters(self):
        available_reporters = {
            cls.get_name().lower()
            for cls in reporter.VerificationReporter.get_all()
            # ignore possible external plugins
            if cls.__module__.startswith("rally")}
        listed_in_cli = {name.lower() for name in verify.DEFAULT_REPORT_TYPES}
        not_listed = available_reporters - listed_in_cli

        if not_listed:
            self.fail("All default reporters should be listed in "
                      "%s.DEFAULTS_REPORTERS (case of letters doesn't matter)."
                      " Missed reporters: %s" % (verify.__name__,
                                                 ", ".join(not_listed)))
