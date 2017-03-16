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

import datetime as dt
import tempfile

import mock
import six

from rally.cli import cliutils
from rally.cli.commands import verify
from rally.cli import envutils
from rally import consts
from rally import exceptions
from rally import plugins
from rally.verification import reporter
from tests.unit import fakes
from tests.unit import test


class VerifyCommandsTestCase(test.TestCase):

    def setUp(self):
        super(VerifyCommandsTestCase, self).setUp()

        self.verify = verify.VerifyCommands()
        self.fake_api = fakes.FakeAPI()

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    def test_list_plugins(self, mock_is_debug, mock_print_list):
        self.verify.list_plugins(self.fake_api, namespace="some")
        self.fake_api.verifier.list_plugins.assert_called_once_with("some")

    @mock.patch("rally.cli.commands.verify.fileutils.update_globals_file")
    def test_create_verifier(self, mock_update_globals_file):
        self.fake_api.verifier.create.return_value = "v_uuid"
        self.fake_api.verifier.get.return_value = mock.Mock(uuid="v_uuid")

        self.verify.create_verifier(self.fake_api, "a", vtype="b",
                                    namespace="c", source="d", version="e",
                                    system_wide=True, extra={})
        self.fake_api.verifier.create.assert_called_once_with(
            "a", vtype="b", namespace="c", source="d", version="e",
            system_wide=True, extra_settings={})

        self.fake_api.verifier.get.assert_called_once_with("v_uuid")
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFIER, "v_uuid")

    @mock.patch("rally.cli.commands.verify.fileutils.update_globals_file")
    def test_use_verifier(self, mock_update_globals_file):
        self.fake_api.verifier.get.return_value = mock.Mock(uuid="v_uuid")
        self.verify.use_verifier(self.fake_api, "v_uuid")
        self.fake_api.verifier.get.assert_called_once_with("v_uuid")
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFIER, "v_uuid")

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    def test_list_verifiers(self, mock_is_debug, mock_print_list):
        self.verify.list_verifiers(self.fake_api)

        self.fake_api.verifier.list.return_value = []
        self.verify.list_verifiers(self.fake_api, "foo")
        self.verify.list_verifiers(self.fake_api)

        self.fake_api.verifier.list.assert_has_calls([mock.call(None),
                                                      mock.call("foo")])

    @mock.patch("rally.cli.commands.verify.envutils.get_global")
    def test_show_verifier(self, mock_get_global):
        fake_verifier = self.fake_api.verifier.get.return_value
        fake_verifier.uuid = "v_uuid"
        fake_verifier.name = "Verifier!"
        fake_verifier.type = "CoolTool"
        fake_verifier.namespace = "ExampleNamespace"
        fake_verifier.description = "The best tool in the world"
        fake_verifier.created_at = dt.datetime(2016, 1, 1, 17, 0, 3, 66)
        fake_verifier.updated_at = dt.datetime(2016, 1, 1, 17, 1, 5, 77)
        fake_verifier.status = "installed"
        fake_verifier.source = "https://example.com"
        fake_verifier.version = "master"
        fake_verifier.system_wide = False
        fake_verifier.extra_settings = {}
        fake_verifier.manager.repo_dir = "./verifiers/repo"
        fake_verifier.manager.venv_dir = "./verifiers/.venv"

        # It is a hard task to mock default value of function argument, so we
        # need to apply this workaround
        original_print_dict = cliutils.print_dict
        print_dict_calls = []

        def print_dict(*args, **kwargs):
            print_dict_calls.append(six.StringIO())
            kwargs["out"] = print_dict_calls[-1]
            original_print_dict(*args, **kwargs)

        with mock.patch.object(verify.cliutils, "print_dict",
                               new=print_dict):
            self.verify.show_verifier(self.fake_api, "v_uuid")

        self.assertEqual(1, len(print_dict_calls))

        self.assertEqual(
            "+---------------------------------------------+\n"
            "|                  Verifier                   |\n"
            "+----------------+----------------------------+\n"
            "| UUID           | v_uuid                     |\n"
            "| Status         | installed                  |\n"
            "| Created at     | 2016-01-01 17:00:03        |\n"
            "| Updated at     | 2016-01-01 17:01:05        |\n"
            "| Active         | -                          |\n"
            "| Name           | Verifier!                  |\n"
            "| Description    | The best tool in the world |\n"
            "| Type           | CoolTool                   |\n"
            "| Namespace      | ExampleNamespace           |\n"
            "| Source         | https://example.com        |\n"
            "| Version        | master                     |\n"
            "| System-wide    | False                      |\n"
            "| Extra settings | -                          |\n"
            "| Location       | ./verifiers/repo           |\n"
            "| Venv location  | ./verifiers/.venv          |\n"
            "+----------------+----------------------------+\n",
            print_dict_calls[0].getvalue())

        self.fake_api.verifier.get.assert_called_once_with("v_uuid")

    def test_delete_verifier(self):
        self.verify.delete_verifier(self.fake_api, "v_id", "d_id", force=True)
        self.fake_api.verifier.delete.assert_called_once_with(
            "v_id", "d_id", True)

    def test_update_verifier(self):
        self.verify.update_verifier(self.fake_api, "v_id")
        self.assertFalse(self.fake_api.verifier.update.called)

        self.verify.update_verifier(self.fake_api, "v_id", update_venv=True,
                                    system_wide=True)
        self.assertFalse(self.fake_api.verifier.update.called)

        self.verify.update_verifier(self.fake_api, "v_id", system_wide=True,
                                    no_system_wide=True)
        self.assertFalse(self.fake_api.verifier.update.called)

        self.verify.update_verifier(self.fake_api, "v_id", version="a",
                                    system_wide=True)
        self.fake_api.verifier.update.assert_called_once_with(
            "v_id", system_wide=True, version="a", update_venv=None)

    @mock.patch("rally.cli.commands.verify.open", create=True)
    @mock.patch("rally.cli.commands.verify.os.path.exists")
    def test_configure_verifier(self, mock_exists, mock_open):
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       new_configuration="/p/a/t/h",
                                       reconfigure=True,
                                       show=True)
        self.assertFalse(self.fake_api.verifier.configure.called)

        mock_exists.return_value = False
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       new_configuration="/p/a/t/h",
                                       show=True)
        self.assertFalse(self.fake_api.verifier.override_configuration.called)

        mock_exists.return_value = True
        mock_open.return_value = mock.mock_open(read_data="data").return_value
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       new_configuration="/p/a/t/h",
                                       show=True)
        mock_open.assert_called_once_with("/p/a/t/h")
        self.fake_api.verifier.override_configuration("v_id", "d_id", "data")

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("[DEFAULT]\nopt = val\n[foo]\nopt = val")
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       extra_options=tf.name)
        expected_options = {"foo": {"opt": "val"},
                            "DEFAULT": {"opt": "val"}}
        self.fake_api.verifier.configure.assert_called_once_with(
            "v_id", "d_id", extra_options=expected_options, reconfigure=False)

        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       extra_options="{foo: {opt: val}, "
                                                     "DEFAULT: {opt: val}}")
        self.fake_api.verifier.configure.assert_called_with(
            "v_id", "d_id", extra_options=expected_options, reconfigure=False)

    def test_list_verifier_tests(self):
        self.fake_api.verifier.list_tests.return_value = ["test_1", "test_2"]
        self.verify.list_verifier_tests(self.fake_api, "v_id", "p")

        self.fake_api.verifier.list_tests.return_value = []
        self.verify.list_verifier_tests(self.fake_api, "v_id", "p")

        self.fake_api.verifier.list_tests.assert_has_calls(
            [mock.call("v_id", "p"), mock.call("v_id", "p")])

    def test_add_verifier_ext(self):
        self.verify.add_verifier_ext(self.fake_api, "v_id", "a", "b", "c")
        self.fake_api.verifier.add_extension.assert_called_once_with(
            "v_id", source="a", version="b", extra_settings="c")

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    def test_list_verifier_exts(self, mock_is_debug, mock_print_list):
        self.verify.list_verifier_exts(self.fake_api, "v_id")

        self.fake_api.verifier.list_extensions.return_value = []
        self.verify.list_verifier_exts(self.fake_api, "v_id")

        self.fake_api.verifier.list_extensions.assert_has_calls(
            [mock.call("v_id"), mock.call("v_id")])

    def test_delete_verifier_ext(self):
        self.verify.delete_verifier_ext(self.fake_api, "v_id", "ext_name")
        self.fake_api.verifier.delete_extension.assert_called_once_with(
            "v_id", "ext_name")

    @mock.patch("rally.cli.commands.verify.fileutils.update_globals_file")
    @mock.patch("rally.cli.commands.verify.os.path.exists")
    def test_start(self, mock_exists, mock_update_globals_file):
        self.verify.start(self.fake_api, "v_id", "d_id", pattern="pattern",
                          load_list="load-list")
        self.assertFalse(self.fake_api.verification.start.called)

        verification = mock.Mock(uuid="v_uuid")
        failed_test = {
            "test_2": {
                "name": "test_2",
                "status": "fail",
                "duration": 2,
                "traceback": "Some traceback"
            }
        }
        test_results = {
            "tests": {
                "test_1": {
                    "name": "test_1",
                    "status": "success",
                    "duration": 2,
                    "tags": []
                }
            },
            "totals": {
                "tests_count": 2,
                "tests_duration": 4,
                "success": 2,
                "skipped": 0,
                "expected_failures": 0,
                "unexpected_success": 0,
                "failures": 0
            }
        }
        test_results["tests"].update(failed_test)
        results = mock.Mock(**test_results)
        results.filter_tests.return_value = failed_test
        self.fake_api.verification.start.return_value = (verification, results)
        self.fake_api.verification.get.return_value = verification

        mock_exists.return_value = False
        self.verify.start(self.fake_api, "v_id", "d_id", load_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        mock_exists.return_value = True
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1\ntest_2")
        self.verify.start(self.fake_api, "v_id", "d_id", tags=["foo"],
                          load_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            "v_id", "d_id", tags=["foo"], load_list=["test_1", "test_2"])

        mock_exists.return_value = False
        self.fake_api.verification.start.reset_mock()
        self.verify.start(self.fake_api, "v_id", "d_id", skip_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1:\ntest_2: Reason\n")
        mock_exists.return_value = True
        self.verify.start(self.fake_api, "v_id", "d_id", skip_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            "v_id", "d_id", tags=None, skip_list={"test_1": None,
                                                  "test_2": "Reason"})

        mock_exists.return_value = False
        self.fake_api.verification.start.reset_mock()
        self.verify.start(self.fake_api, "v_id", "d_id", xfail_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1:\ntest_2: Reason\n")
        mock_exists.return_value = True
        self.verify.start(self.fake_api, "v_id", "d_id", xfail_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            "v_id", "d_id", tags=None, xfail_list={"test_1": None,
                                                   "test_2": "Reason"})

        self.fake_api.verification.get.assert_called_with("v_uuid")
        mock_update_globals_file.assert_called_with(
            envutils.ENV_VERIFICATION, "v_uuid")

        self.fake_api.verification.get.reset_mock()
        mock_update_globals_file.reset_mock()
        self.verify.start(self.fake_api, "v_id", "d_id", detailed=True,
                          do_use=False)
        self.assertFalse(self.fake_api.verification.get.called)
        self.assertFalse(mock_update_globals_file.called)

    @mock.patch("rally.cli.commands.verify.os.path.exists")
    @mock.patch("rally.cli.commands.verify.fileutils.update_globals_file")
    def test_start_on_unfinished_deployment(self, mock_update_globals_file,
                                            mock_exists):
        deployment_id = "d_id"
        deployment_name = "xxx_name"
        exc = exceptions.DeploymentNotFinishedStatus(
            name=deployment_name,
            uuid=deployment_id,
            status=consts.DeployStatus.DEPLOY_INIT)
        self.fake_api.verification.start.side_effect = exc
        self.assertEqual(
            1, self.verify.start(self.fake_api, "v_id", deployment_id))

    @mock.patch("rally.cli.commands.verify.fileutils.update_globals_file")
    def test_use(self, mock_update_globals_file):
        self.fake_api.verification.get.return_value = mock.Mock(uuid="v_uuid")
        self.verify.use(self.fake_api, "v_uuid")
        self.fake_api.verification.get.assert_called_once_with("v_uuid")
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFICATION, "v_uuid")

    def test_rerun(self):
        verification = mock.Mock(uuid="v_uuid")
        results = mock.Mock(totals={"tests_count": 2,
                                    "tests_duration": 4,
                                    "success": 2,
                                    "skipped": 0,
                                    "expected_failures": 0,
                                    "unexpected_success": 0,
                                    "failures": 0})
        self.fake_api.verification.rerun.return_value = (verification, results)

        self.verify.rerun(self.fake_api, "v_uuid", "d_id", failed=True,)
        self.fake_api.verification.rerun.assert_called_once_with(
            "v_uuid", deployment="d_id", failed=True, tags=None, concur=None)

    def test_show(self):
        deployment_name = "Some Deploy"
        deployment_uuid = "some-deploy-uuid"
        verifier_name = "My Verifier"
        verifier_uuid = "my-verifier-uuid"
        verifier_type = "OldSchoolTestTool"
        verifier_namespace = "OpenStack"
        verifier = mock.Mock(type=verifier_type, namespace=verifier_namespace)
        verifier.name = verifier_name
        verifier.uuid = verifier_uuid
        verification = {
            "uuid": "uuuiiiiddd",
            "tags": ["bar", "foo"],
            "status": "success",
            "created_at": dt.datetime(2016, 1, 1, 17, 0, 3, 66),
            "updated_at": dt.datetime(2016, 1, 1, 17, 1, 5, 77),
            "tests_count": 2,
            "tests_duration": 4,
            "success": 1,
            "skipped": 0,
            "expected_failures": 0,
            "unexpected_success": 0,
            "failures": 1,
            "run_args": {
                "load_list": ["test_1", "test_2"],
                "skip_list": ["test_3"],
                "concurrency": "3"
            },
            "tests": {
                "test_1": {
                    "name": "test_1",
                    "status": "success",
                    "duration": 2,
                    "tags": []
                },
                "test_2": {
                    "name": "test_2",
                    "status": "fail",
                    "duration": 2,
                    "traceback": "Some traceback"
                }
            }
        }
        self.fake_api.verifier.get.return_value = verifier
        self.fake_api.verification.get.return_value = mock.Mock(**verification)
        self.fake_api.deployment.get.return_value = {"name": deployment_name,
                                                     "uuid": deployment_uuid}

        # It is a hard task to mock default value of function argument, so we
        # need to apply this workaround
        original_print_dict = cliutils.print_dict
        print_dict_calls = []

        def print_dict(*args, **kwargs):
            print_dict_calls.append(six.StringIO())
            kwargs["out"] = print_dict_calls[-1]
            original_print_dict(*args, **kwargs)

        with mock.patch.object(verify.cliutils, "print_dict",
                               new=print_dict):
            self.verify.show(self.fake_api, "v_uuid", detailed=True)

        self.assertEqual(1, len(print_dict_calls))

        self.assertEqual(
            "+----------------------------------------------------------------"
            "--------------------+\n"
            "|                                    Verification                "
            "                    |\n"
            "+---------------------+------------------------------------------"
            "--------------------+\n"
            "| UUID                | uuuiiiiddd                               "
            "                    |\n"
            "| Status              | success                                  "
            "                    |\n"
            "| Started at          | 2016-01-01 17:00:03                      "
            "                    |\n"
            "| Finished at         | 2016-01-01 17:01:05                      "
            "                    |\n"
            "| Duration            | 0:01:02                                  "
            "                    |\n"
            "| Run arguments       | concurrency: 3                           "
            "                    |\n"
            "|                     | load_list: (value is too long, will be di"
            "splayed separately) |\n"
            "|                     | skip_list: (value is too long, will be di"
            "splayed separately) |\n"
            "| Tags                | bar, foo                                 "
            "                    |\n"
            "| Verifier name       | My Verifier (UUID: my-verifier-uuid)     "
            "                    |\n"
            "| Verifier type       | OldSchoolTestTool (namespace: OpenStack) "
            "                    |\n"
            "| Deployment name     | Some Deploy (UUID: some-deploy-uuid)     "
            "                    |\n"
            "| Tests count         | 2                                        "
            "                    |\n"
            "| Tests duration, sec | 4                                        "
            "                    |\n"
            "| Success             | 1                                        "
            "                    |\n"
            "| Skipped             | 0                                        "
            "                    |\n"
            "| Expected failures   | 0                                        "
            "                    |\n"
            "| Unexpected success  | 0                                        "
            "                    |\n"
            "| Failures            | 1                                        "
            "                    |\n"
            "+---------------------+------------------------------------------"
            "--------------------+\n", print_dict_calls[0].getvalue())

        self.fake_api.verification.get.assert_called_once_with("v_uuid")

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    def test_list(self, mock_print_list):
        self.verify.list(self.fake_api, "v_id", "d_id")

        self.fake_api.verification.list.return_value = []
        self.verify.list(self.fake_api, "v_id", "d_id", "foo", "bar")
        self.verify.list(self.fake_api)

        self.fake_api.verification.list.assert_has_calls(
            [mock.call("v_id", "d_id", None, None),
             mock.call("v_id", "d_id", "foo", "bar"),
             mock.call(None, None, None, None)])

    def test_delete(self):
        self.verify.delete(self.fake_api, "v_uuid")
        self.fake_api.verification.delete.assert_called_once_with("v_uuid")

        self.verify.delete(self.fake_api, ["v1_uuid", "v2_uuid"])
        self.fake_api.verification.delete.assert_has_calls(
            [mock.call("v1_uuid"), mock.call("v2_uuid")])

    @mock.patch("rally.cli.commands.verify.os")
    @mock.patch("rally.cli.commands.verify.webbrowser.open_new_tab")
    @mock.patch("rally.cli.commands.verify.open", create=True)
    def test_report(self, mock_open, mock_open_new_tab, mock_os):
        output_dest = "/p/a/t/h"
        output_type = "type"
        content = "content"
        self.fake_api.verification.report.return_value = {
            "files": {output_dest: content}, "open": output_dest}
        mock_os.path.exists.return_value = False

        self.verify.report(self.fake_api, "v_uuid", output_type=output_type,
                           output_dest=output_dest, open_it=True)
        self.fake_api.verification.report.assert_called_once_with(
            ["v_uuid"], output_type, output_dest)
        mock_open.assert_called_once_with(mock_os.path.abspath.return_value,
                                          "w")
        mock_os.makedirs.assert_called_once_with(
            mock_os.path.dirname.return_value)

        mock_open.reset_mock()
        mock_open_new_tab.reset_mock()
        mock_os.makedirs.reset_mock()

        mock_os.path.exists.return_value = True
        self.fake_api.verification.report.return_value = {
            "files": {output_dest: content}, "print": "foo"}

        self.verify.report(self.fake_api, "v_uuid", output_type=output_type,
                           output_dest=output_dest)

        self.assertFalse(mock_open_new_tab.called)
        self.assertFalse(mock_os.makedirs.called)

    @mock.patch("rally.cli.commands.verify.VerifyCommands.use")
    @mock.patch("rally.cli.commands.verify.open", create=True)
    @mock.patch("rally.cli.commands.verify.os.path.exists")
    def test_import_results(self, mock_exists, mock_open, mock_use):
        mock_exists.return_value = False
        self.verify.import_results(self.fake_api, "v_id", "d_id")
        self.assertFalse(self.fake_api.verification.import_results.called)

        verification = mock.Mock(uuid="verification_uuid")
        results = mock.Mock(totals={"tests_count": 2,
                                    "tests_duration": 4,
                                    "success": 2,
                                    "skipped": 0,
                                    "expected_failures": 0,
                                    "unexpected_success": 0,
                                    "failures": 0})
        self.fake_api.verification.import_results.return_value = (
            verification, results)

        mock_exists.return_value = True
        mock_open.return_value = mock.mock_open(read_data="data").return_value
        self.verify.import_results(self.fake_api, "v_id", "d_id",
                                   file_to_parse="/p/a/t/h")
        mock_open.assert_called_once_with("/p/a/t/h", "r")
        self.fake_api.verification.import_results.assert_called_once_with(
            "v_id", "d_id", "data")

        mock_use.assert_called_with("verification_uuid")

        mock_use.reset_mock()
        self.verify.import_results(self.fake_api, "v_id", "d_id", do_use=False)
        self.assertFalse(mock_use.called)

    @plugins.ensure_plugins_are_loaded
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
