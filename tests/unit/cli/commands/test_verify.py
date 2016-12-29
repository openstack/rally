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

        self.fake_api.verifier.list.assert_has_calls([mock.call(None),
                                                      mock.call("foo")])

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
                                       replace="/p/a/t/h", recreate=True)
        self.assertFalse(self.fake_api.verifier.configure.called)

        mock_exists.return_value = False
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       replace="/p/a/t/h")
        self.assertFalse(self.fake_api.verifier.override_configuration.called)

        mock_exists.return_value = True
        mock_open.return_value = mock.mock_open(read_data="data").return_value
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       replace="/p/a/t/h")
        mock_open.assert_called_once_with("/p/a/t/h", "r")
        self.fake_api.verifier.override_configuration("v_id", "d_id", "data")

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("[DEFAULT]\nopt = val\n[foo]\nopt = val")
        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       extra_options=tf.name)
        expected_options = {"foo": {"opt": "val"},
                            "DEFAULT": {"opt": "val"}}
        self.fake_api.verifier.configure.assert_called_once_with(
            "v_id", "d_id", extra_options=expected_options, recreate=False)

        self.verify.configure_verifier(self.fake_api, "v_id", "d_id",
                                       extra_options="{foo: {opt: val}, "
                                                     "DEFAULT: {opt: val}}")
        self.fake_api.verifier.configure.assert_called_with(
            "v_id", "d_id", extra_options=expected_options, recreate=False)

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
                          failed=True)
        self.assertFalse(self.fake_api.verification.start.called)

        mock_exists.return_value = False
        self.verify.start(self.fake_api, "v_id", "d_id", load_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        verification = mock.Mock(uuid="v_uuid")
        results = mock.Mock(totals={"tests_count": 2,
                                    "tests_duration": 4,
                                    "success": 2,
                                    "skipped": 0,
                                    "expected_failures": 0,
                                    "unexpected_success": 0,
                                    "failures": 0})
        self.fake_api.verification.start.return_value = (verification, results)
        self.fake_api.verification.get.return_value = verification

        mock_exists.return_value = True
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1\ntest_2")
        self.verify.start(self.fake_api, "v_id", "d_id", load_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            "v_id", "d_id", load_list=["test_1", "test_2"])

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
            "v_id", "d_id", skip_list={"test_1": None, "test_2": "Reason"})

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
            "v_id", "d_id", xfail_list={"test_1": None, "test_2": "Reason"})

        self.fake_api.verification.get.assert_called_with("v_uuid")
        mock_update_globals_file.assert_called_with(
            envutils.ENV_VERIFICATION, "v_uuid")

        self.fake_api.verification.get.reset_mock()
        mock_update_globals_file.reset_mock()
        self.verify.start(self.fake_api, "v_id", "d_id", do_use=False)
        self.assertFalse(self.fake_api.verification.get.called)
        self.assertFalse(mock_update_globals_file.called)

    @mock.patch("rally.cli.commands.verify.fileutils.update_globals_file")
    def test_use(self, mock_update_globals_file):
        self.fake_api.verification.get.return_value = mock.Mock(uuid="v_uuid")
        self.verify.use(self.fake_api, "v_uuid")
        self.fake_api.verification.get.assert_called_once_with("v_uuid")
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFICATION, "v_uuid")

    def test_show(self):
        deployment_name = "Some Deploy"
        verifier_name = "My Verifier"
        verifier_type = "OldSchoolTestTool"
        verifier_namespace = "OpenStack"
        verifier = mock.Mock(type=verifier_type, namespace=verifier_namespace)
        verifier.name = verifier_name
        verification = {
            "uuid": "uuuiiiiddd",
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
        self.fake_api.deployment.get.return_value = {"name": deployment_name}

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
            "| Verifier name       | My Verifier                              "
            "                    |\n"
            "| Verifier type       | OldSchoolTestTool (namespace: OpenStack) "
            "                    |\n"
            "| Deployment name     | Some Deploy                              "
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
            "| Status              | success                                  "
            "                    |\n"
            "+---------------------+------------------------------------------"
            "--------------------+\n", print_dict_calls[0].getvalue())

        self.fake_api.verification.get.assert_called_once_with("v_uuid")

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    def test_list(self, mock_print_list):
        self.verify.list(self.fake_api, "v_id", "d_id")

        self.fake_api.verification.list.return_value = []
        self.verify.list(self.fake_api, "v_id", "d_id", "foo")

        self.fake_api.verification.list.assert_has_calls(
            [mock.call("v_id", "d_id", None), mock.call("v_id", "d_id", "foo")]
        )

    def test_delete(self):
        self.verify.delete(self.fake_api, "v_uuid")
        self.fake_api.verification.delete.assert_called_once_with("v_uuid")

        self.verify.delete(self.fake_api, ["v1_uuid", "v2_uuid"])
        self.fake_api.verification.delete.assert_has_calls(
            [mock.call("v1_uuid"), mock.call("v2_uuid")])

    @mock.patch("rally.cli.commands.verify.webbrowser.open_new_tab")
    @mock.patch("rally.cli.commands.verify.open", create=True)
    def test_report(self, mock_open, mock_open_new_tab):
        self.verify.report(self.fake_api, "v_uuid", html=True,
                           output_file="/p/a/t/h", open_it=True)
        self.fake_api.verification.report.assert_called_once_with(
            ["v_uuid"], True)
        mock_open.assert_called_once_with("/p/a/t/h", "w")
        mock_open_new_tab.assert_called_once_with("file:///p/a/t/h")

        mock_open.reset_mock()
        mock_open_new_tab.reset_mock()
        self.verify.report(self.fake_api, "v_uuid")
        self.assertFalse(mock_open.called)
        self.assertFalse(mock_open_new_tab.called)

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
