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

import io
import tempfile
from unittest import mock

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

        self.deployment_name = "Some Deploy"
        self.deployment_uuid = "some-deploy-uuid"
        self.verifier_name = "My Verifier"
        self.verifier_uuid = "my-verifier-uuid"
        self.verifier_type = "OldSchoolTestTool"
        self.verifier_platform = "OpenStack"
        self.verification_uuid = "uuuiiiiddd"

        self.verifier_data = {
            "uuid": self.verifier_uuid,
            "name": self.verifier_name,
            "type": self.verifier_type,
            "platform": self.verifier_platform,
            "description": "The best tool in the world",
            "created_at": "2016-01-01T17:00:03",
            "updated_at": "2016-01-01T17:01:05",
            "status": "installed",
            "source": "https://example.com",
            "version": "master",
            "system_wide": False,
            "extra_settings": {},
            "manager.repo_dir": "./verifiers/repo",
            "manager.venv_dir": "./verifiers/.venv"
        }

        self.verification_data = {
            "uuid": self.verification_uuid,
            "verifier_uuid": self.verifier_uuid,
            "deployment_uuid": self.deployment_uuid,
            "tags": ["bar", "foo"],
            "status": "success",
            "created_at": "2016-01-01T17:00:03",
            "updated_at": "2016-01-01T17:01:05",
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
                "concurrency": "3"},
            "tests": {
                "test_1": {
                    "name": "test_1",
                    "status": "success",
                    "duration": 2,
                    "tags": []},
                "test_2": {
                    "name": "test_2",
                    "status": "fail",
                    "duration": 2,
                    "traceback": "Some traceback"}
            },
            "test_2": {
                "name": "test_2",
                "status": "fail",
                "duration": 2,
                "traceback": "Some traceback"}
        }

        self.results_data = {
            "totals": {"tests_count": 2,
                       "tests_duration": 4,
                       "success": 1,
                       "skipped": 0,
                       "expected_failures": 0,
                       "unexpected_success": 0,
                       "failures": 1},
            "tests": {
                "test_1": {
                    "name": "test_1",
                    "status": "success",
                    "duration": 2,
                    "tags": []}
            },
            "test_2": {
                "name": "test_2",
                "status": "fail",
                "duration": 4,
                "tags": []}
        }

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    def test_list_plugins(self, mock_is_debug, mock_print_list):
        self.verify.list_plugins(self.fake_api, platform="some")
        self.fake_api.verifier.list_plugins.assert_called_once_with(
            platform="some")

    @mock.patch("rally.cli.commands.verify.envutils.update_globals_file")
    def test_create_verifier(self, mock_update_globals_file):
        self.fake_api.verifier.create.return_value = self.verifier_uuid
        self.fake_api.verifier.get.return_value = self.verifier_data

        self.verify.create_verifier(self.fake_api, "a", vtype="b",
                                    platform="c", source="d", version="e",
                                    system_wide=True, extra={})
        self.fake_api.verifier.create.assert_called_once_with(
            name="a", vtype="b", platform="c", source="d", version="e",
            system_wide=True, extra_settings={})

        self.fake_api.verifier.get.assert_called_once_with(
            verifier_id=self.verifier_uuid)
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFIER, self.verifier_uuid)

    @mock.patch("rally.cli.commands.verify.envutils.update_globals_file")
    def test_use_verifier(self, mock_update_globals_file):
        self.fake_api.verifier.get.return_value = self.verifier_data
        self.verify.use_verifier(self.fake_api, self.verifier_uuid)
        self.fake_api.verifier.get.assert_called_once_with(
            verifier_id=self.verifier_uuid)
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFIER, self.verifier_uuid)

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    def test_list_verifiers_empty_verifiers(self, mock_print_list):
        self.fake_api.verifier.list.return_value = []
        self.verify.list_verifiers(self.fake_api)

        self.verify.list_verifiers(self.fake_api, "foo")
        self.verify.list_verifiers(self.fake_api)

        self.fake_api.verifier.list.assert_has_calls(
            [mock.call(status=None), mock.call(status="foo")])

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    def test_list_verifiers(self, mock_print_list):
        self.fake_api.verifier.list.return_value = [self.verifier_data]

        additional_fields = ["UUID", "Name", "Type", "Platform", "Created at",
                             "Updated at", "Status", "Version", "System-wide",
                             "Active"]
        additional_keys = ["normalize_field_names", "sortby_index",
                           "formatters"]
        self.verify.list_verifiers(self.fake_api)
        # astarove: should be replaced on mock_print_list.assert_called_once()
        self.assertEqual(1, mock_print_list.call_count)
        self.assertEqual(([self.verifier_data], additional_fields),
                         mock_print_list.call_args[0])
        self.assertEqual(additional_keys.sort(),
                         list(mock_print_list.call_args[1].keys()).sort())

    @mock.patch("rally.cli.commands.verify.envutils.get_global")
    def test_show_verifier(self, mock_get_global):
        self.fake_api.verifier.get.return_value = self.verifier_data
        self.verify._base_dir = mock.Mock(return_value="./verifiers/")

        # It is a hard task to mock default value of function argument, so we
        # need to apply this workaround
        original_print_dict = cliutils.print_dict
        print_dict_calls = []

        def print_dict(*args, **kwargs):
            print_dict_calls.append(io.StringIO())
            kwargs["out"] = print_dict_calls[-1]
            original_print_dict(*args, **kwargs)

        with mock.patch.object(verify.cliutils, "print_dict",
                               new=print_dict):
            self.verify.show_verifier(self.fake_api, self.verifier_uuid)

        self.assertEqual(1, len(print_dict_calls))

        self.assertEqual(
            "+---------------------------------------------+\n"
            "|                  Verifier                   |\n"
            "+----------------+----------------------------+\n"
            "| UUID           | my-verifier-uuid           |\n"
            "| Status         | installed                  |\n"
            "| Created at     | 2016-01-01 17:00:03        |\n"
            "| Updated at     | 2016-01-01 17:01:05        |\n"
            "| Active         | -                          |\n"
            "| Name           | My Verifier                |\n"
            "| Description    | The best tool in the world |\n"
            "| Type           | OldSchoolTestTool          |\n"
            "| Platform       | OpenStack                  |\n"
            "| Source         | https://example.com        |\n"
            "| Version        | master                     |\n"
            "| System-wide    | False                      |\n"
            "| Extra settings | -                          |\n"
            "| Location       | ./verifiers/repo           |\n"
            "| Venv location  | ./verifiers/.venv          |\n"
            "+----------------+----------------------------+\n",
            print_dict_calls[0].getvalue())

        self.fake_api.verifier.get.assert_called_once_with(
            verifier_id=self.verifier_uuid)

    def test_delete_verifier(self):
        self.verify.delete_verifier(self.fake_api, "v_id", "d_id", force=True)
        self.fake_api.verifier.delete.assert_called_once_with(
            verifier_id="v_id", deployment_id="d_id", force=True)

    def test_update_verifier(self):
        self.verify.update_verifier(self.fake_api, self.verifier_uuid)
        self.assertFalse(self.fake_api.verifier.update.called)

        self.verify.update_verifier(self.fake_api, self.verification_uuid,
                                    update_venv=True,
                                    system_wide=True)
        self.assertFalse(self.fake_api.verifier.update.called)

        self.verify.update_verifier(self.fake_api, self.verification_uuid,
                                    system_wide=True,
                                    no_system_wide=True)
        self.assertFalse(self.fake_api.verifier.update.called)

        self.verify.update_verifier(self.fake_api, self.verification_uuid,
                                    version="a",
                                    system_wide=True)
        self.fake_api.verifier.update.assert_called_once_with(
            verifier_id=self.verification_uuid, system_wide=True,
            version="a", update_venv=None)

    @mock.patch("rally.cli.commands.verify.open", create=True)
    @mock.patch("rally.cli.commands.verify.os.path.exists")
    def test_configure_verifier(self, mock_exists, mock_open):
        self.verify.configure_verifier(self.fake_api, self.verifier_uuid,
                                       self.deployment_uuid,
                                       new_configuration="/p/a/t/h",
                                       reconfigure=True,
                                       show=True)
        self.assertFalse(self.fake_api.verifier.configure.called)

        mock_exists.return_value = False
        self.verify.configure_verifier(self.fake_api, self.verifier_uuid,
                                       self.deployment_uuid,
                                       new_configuration="/p/a/t/h",
                                       show=True)
        self.assertFalse(self.fake_api.verifier.override_configuration.called)

        mock_exists.return_value = True
        mock_open.return_value = mock.mock_open(read_data="data").return_value
        self.verify.configure_verifier(self.fake_api, self.verifier_uuid,
                                       self.deployment_uuid,
                                       new_configuration="/p/a/t/h",
                                       show=True)
        mock_open.assert_called_once_with("/p/a/t/h")
        self.fake_api.verifier.override_configuration(self.verifier_uuid,
                                                      self.deployment_uuid,
                                                      "data")

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("[DEFAULT]\nopt = val\n[foo]\nopt = val")
        self.verify.configure_verifier(self.fake_api, self.verifier_uuid,
                                       self.deployment_uuid,
                                       extra_options=tf.name)
        expected_options = {"foo": {"opt": "val"},
                            "DEFAULT": {"opt": "val"}}
        self.fake_api.verifier.configure.assert_called_once_with(
            verifier=self.verifier_uuid, deployment_id=self.deployment_uuid,
            extra_options=expected_options, reconfigure=False)

        self.verify.configure_verifier(self.fake_api, self.verifier_uuid,
                                       self.deployment_uuid,
                                       extra_options="{foo: {opt: val}, "
                                                     "DEFAULT: {opt: val}}")
        self.fake_api.verifier.configure.assert_called_with(
            verifier=self.verifier_uuid, deployment_id=self.deployment_uuid,
            extra_options=expected_options, reconfigure=False)

    def test_list_verifier_tests(self):
        self.fake_api.verifier.list_tests.return_value = ["test_1", "test_2"]
        self.verify.list_verifier_tests(self.fake_api, self.verifier_uuid, "p")

        self.fake_api.verifier.list_tests.return_value = []
        self.verify.list_verifier_tests(self.fake_api, self.verifier_uuid, "p")

        self.fake_api.verifier.list_tests.assert_has_calls(
            [mock.call(verifier_id=self.verifier_uuid, pattern="p"),
             mock.call(verifier_id=self.verifier_uuid, pattern="p")])

    def test_add_verifier_ext(self):
        self.verify.add_verifier_ext(self.fake_api, self.verifier_uuid,
                                     "a", "b", "c")
        self.fake_api.verifier.add_extension.assert_called_once_with(
            verifier_id=self.verifier_uuid,
            source="a", version="b", extra_settings="c")

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    def test_list_verifier_exts_empty_list(self,
                                           mock_is_debug, mock_print_list):
        self.fake_api.verifier.list_extensions.return_value = []
        self.verify.list_verifier_exts(self.fake_api, self.verifier_uuid)

        self.verify.list_verifier_exts(self.fake_api, self.verifier_uuid)

        self.fake_api.verifier.list_extensions.assert_has_calls(
            [mock.call(verifier_id=self.verifier_uuid),
             mock.call(verifier_id=self.verifier_uuid)])

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=False)
    def test_list_verifier_exts(self, mock_is_debug, mock_print_list):
        ver_exts = self.fake_api.verifier.list_extensions
        ver_exts.return_value = [mock.MagicMock()]
        fields = ["Name", "Entry point"]
        self.verify.list_verifier_exts(self.fake_api, self.verifier_uuid)

        self.verify.list_verifier_exts(self.fake_api, self.verifier_uuid)

        self.fake_api.verifier.list_extensions.assert_has_calls(
            [mock.call(verifier_id=self.verifier_uuid),
             mock.call(verifier_id=self.verifier_uuid)])

        mock_print_list.assert_called_with(ver_exts.return_value,
                                           fields,
                                           normalize_field_names=True)

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    def test_list_verifier_exts_with_logging(self,
                                             mock_is_debug, mock_print_list):
        ver_exts = self.fake_api.verifier.list_extensions
        ver_exts.return_value = [mock.MagicMock()]
        fields = ["Name", "Entry point", "Location"]
        self.verify.list_verifier_exts(self.fake_api, self.verifier_uuid)

        self.verify.list_verifier_exts(self.fake_api, self.verifier_uuid)

        self.fake_api.verifier.list_extensions.assert_has_calls(
            [mock.call(verifier_id=self.verifier_uuid),
             mock.call(verifier_id=self.verifier_uuid)])

        mock_print_list.assert_called_with(ver_exts.return_value,
                                           fields,
                                           normalize_field_names=True)

    def test_delete_verifier_ext(self):
        self.verify.delete_verifier_ext(self.fake_api, self.verifier_uuid,
                                        "ext_name")
        self.fake_api.verifier.delete_extension.assert_called_once_with(
            verifier_id=self.verifier_uuid, name="ext_name")

    @mock.patch("rally.cli.commands.verify.envutils.update_globals_file")
    @mock.patch("rally.cli.commands.verify.os.path.exists")
    def test_start(self, mock_exists, mock_update_globals_file):
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, pattern="pattern",
                          load_list="load-list")
        self.assertFalse(self.fake_api.verification.start.called)

        verification = self.verification_data
        self.fake_api.verification.start.return_value = {
            "verification": verification,
            "totals": self.results_data["totals"],
            "tests": self.results_data["tests"]}
        self.fake_api.verification.get.return_value = verification

        mock_exists.return_value = False
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, load_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        mock_exists.return_value = True
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1\ntest_2")
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, tags=["foo"],
                          load_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            verifier_id=self.verifier_uuid,
            deployment_id=self.deployment_uuid,
            tags=["foo"], load_list=["test_1", "test_2"])

        mock_exists.return_value = False
        self.fake_api.verification.start.reset_mock()

        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.verifier_uuid, skip_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1:\ntest_2: Reason\n")
        mock_exists.return_value = True
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, skip_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            verifier_id=self.verifier_uuid,
            deployment_id=self.deployment_uuid,
            tags=None,
            skip_list={"test_1": None, "test_2": "Reason"})

        mock_exists.return_value = False
        self.fake_api.verification.start.reset_mock()
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, xfail_list="/p/a/t/h")
        self.assertFalse(self.fake_api.verification.start.called)

        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, "w") as f:
            f.write("test_1:\ntest_2: Reason\n")
        mock_exists.return_value = True
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, xfail_list=tf.name)
        self.fake_api.verification.start.assert_called_once_with(
            verifier_id=self.verifier_uuid,
            deployment_id=self.deployment_uuid, tags=None,
            xfail_list={"test_1": None, "test_2": "Reason"})

        self.fake_api.verification.get.assert_called_with(
            verification_uuid=self.verification_uuid)
        mock_update_globals_file.assert_called_with(
            envutils.ENV_VERIFICATION, self.verification_uuid)

        self.fake_api.verification.get.reset_mock()
        mock_update_globals_file.reset_mock()
        self.verify.start(self.fake_api, self.verifier_uuid,
                          self.deployment_uuid, detailed=True,
                          do_use=False)
        self.assertFalse(self.fake_api.verification.get.called)
        self.assertFalse(mock_update_globals_file.called)

    @mock.patch("rally.cli.commands.verify.os.path.exists")
    @mock.patch("rally.cli.commands.verify.envutils.update_globals_file")
    def test_start_on_unfinished_deployment(self, mock_update_globals_file,
                                            mock_exists):
        deployment_id = self.deployment_uuid
        deployment_name = self.deployment_name
        exc = exceptions.DeploymentNotFinishedStatus(
            name=deployment_name,
            uuid=deployment_id,
            status=consts.DeployStatus.DEPLOY_INIT)
        self.fake_api.verification.start.side_effect = exc
        self.assertEqual(
            1, self.verify.start(self.fake_api,
                                 self.deployment_uuid, deployment_id))

    @mock.patch("rally.cli.commands.verify.envutils.update_globals_file")
    def test_use(self, mock_update_globals_file):
        self.fake_api.verification.get.return_value = self.verification_data
        self.verify.use(self.fake_api, self.verification_uuid)
        self.fake_api.verification.get.assert_called_once_with(
            verification_uuid=self.verification_uuid)
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFICATION, self.verification_uuid)

    @mock.patch("rally.cli.commands.verify.envutils.update_globals_file")
    def test_rerun(self, mock_update_globals_file):
        self.fake_api.verification.rerun.return_value = {
            "verification": self.verification_data,
            "totals": self.results_data["totals"],
            "tests": self.results_data["tests"]}
        self.fake_api.verification.get.return_value = self.verification_data

        self.verify.rerun(self.fake_api, self.verification_uuid,
                          self.deployment_uuid, failed=True)
        self.fake_api.verification.rerun.assert_called_once_with(
            verification_uuid=self.verification_uuid,
            concurrency=None,
            deployment_id="some-deploy-uuid",
            failed=True, tags=None)
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_VERIFICATION, self.verification_uuid)

    def test_show(self):

        verification = self.verification_data
        self.fake_api.verifier.get.return_value = self.verifier_data
        self.fake_api.verification.get.return_value = verification
        self.fake_api.deployment.get.return_value = {
            "name": self.deployment_name, "uuid": self.deployment_uuid}

        # It is a hard task to mock default value of function argument, so we
        # need to apply this workaround
        original_print_dict = cliutils.print_dict
        print_dict_calls = []

        def print_dict(*args, **kwargs):
            print_dict_calls.append(io.StringIO())
            kwargs["out"] = print_dict_calls[-1]
            original_print_dict(*args, **kwargs)

        with mock.patch.object(verify.cliutils, "print_dict",
                               new=print_dict):
            self.verify.show(self.fake_api, self.verifier_uuid, detailed=True)

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
            "| Verifier type       | OldSchoolTestTool (platform: OpenStack)  "
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

        self.fake_api.verification.get.assert_called_once_with(
            verification_uuid=self.verifier_uuid)

        with mock.patch.object(verify.cliutils, "print_dict",
                               new=print_dict):
            self.verify.show(self.fake_api, self.verifier_uuid, detailed=False)
        self.assertEqual(2, len(print_dict_calls))

        self.assertEqual(
            print_dict_calls[1].getvalue(),
            "+---------------------------------------------------"
            "--------------------------------------+\n"
            "|                                      Verification "
            "                                      |\n"
            "+---------------------+-----------------------------"
            "--------------------------------------+\n"
            "| UUID                | uuuiiiiddd                  "
            "                                      |\n"
            "| Status              | success                     "
            "                                      |\n"
            "| Started at          | 2016-01-01 17:00:03         "
            "                                      |\n"
            "| Finished at         | 2016-01-01 17:01:05         "
            "                                      |\n"
            "| Duration            | 0:01:02                     "
            "                                      |\n"
            "| Run arguments       | concurrency: 3              "
            "                                      |\n"
            "|                     | load_list: (value is too lon"
            "g, use 'detailed' flag to display it) |\n"
            "|                     | skip_list: (value is too lon"
            "g, use 'detailed' flag to display it) |\n"
            "| Tags                | bar, foo                    "
            "                                      |\n"
            "| Verifier name       | My Verifier (UUID: my-verifi"
            "er-uuid)                              |\n"
            "| Verifier type       | OldSchoolTestTool (platform:"
            " OpenStack)                           |\n"
            "| Deployment name     | Some Deploy (UUID: some-depl"
            "oy-uuid)                              |\n"
            "| Tests count         | 2                           "
            "                                      |\n"
            "| Tests duration, sec | 4                           "
            "                                      |\n"
            "| Success             | 1                           "
            "                                      |\n"
            "| Skipped             | 0                           "
            "                                      |\n"
            "| Expected failures   | 0                           "
            "                                      |\n"
            "| Unexpected success  | 0                           "
            "                                      |\n"
            "| Failures            | 1                           "
            "                                      |\n"
            "+---------------------+-----------------------------"
            "--------------------------------------+\n",
        )

        self.fake_api.verification.get.assert_called_with(
            verification_uuid=self.verifier_uuid)

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    def test_list_empty_verifications(self, mock_print_list):
        self.fake_api.verification.list.return_value = []
        self.verify.list(self.fake_api, self.verifier_uuid,
                         self.deployment_uuid)

        self.verify.list(self.fake_api, self.verifier_uuid,
                         self.deployment_uuid, "foo", "bar")
        self.verify.list(self.fake_api)

        self.fake_api.verification.list.assert_has_calls(
            [mock.call(verifier_id=self.verifier_uuid,
                       deployment_id=self.deployment_uuid,
                       tags=None, status=None),
             mock.call(verifier_id=self.verifier_uuid,
                       deployment_id=self.deployment_uuid,
                       tags="foo", status="bar"),
             mock.call(verifier_id=None, deployment_id=None,
                       tags=None, status=None)])

    @mock.patch("rally.cli.commands.verify.cliutils.print_list")
    def test_list(self, mock_print_list):
        self.fake_api.verification.list.return_value = [self.verification_data]
        self.verify.list(self.fake_api, self.verifier_uuid,
                         self.deployment_uuid)

        additional_fields = ["UUID", "Tags", "Verifier name",
                             "Deployment name", "Started at", "Finished at",
                             "Duration", "Status"]
        additional_keys = ["normalize_field_names", "sortby_index",
                           "formatters"]
        # astarove: Should be replaced on mock_print_list.assert_called_once())
        self.assertEqual(1, mock_print_list.call_count)
        self.assertEqual(([self.verification_data], additional_fields),
                         mock_print_list.call_args[0])
        self.assertEqual(additional_keys.sort(),
                         list(mock_print_list.call_args[1].keys()).sort())

    def test_delete(self):
        self.verify.delete(self.fake_api, "v_uuid")
        self.fake_api.verification.delete.assert_called_once_with(
            verification_uuid="v_uuid")

        self.verify.delete(self.fake_api, ["v1_uuid", "v2_uuid"])
        self.fake_api.verification.delete.assert_has_calls(
            [mock.call(verification_uuid="v1_uuid"),
             mock.call(verification_uuid="v2_uuid")])

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

        self.verify.report(self.fake_api,
                           verification_uuid=self.verifier_uuid,
                           output_type=output_type,
                           output_dest=output_dest, open_it=True)
        self.fake_api.verification.report.assert_called_once_with(
            uuids=[self.verifier_uuid], output_type=output_type,
            output_dest=output_dest)
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

        self.verify.report(self.fake_api, self.verifier_uuid,
                           output_type=output_type,
                           output_dest=output_dest)

        self.assertFalse(mock_open_new_tab.called)
        self.assertFalse(mock_os.makedirs.called)

    @mock.patch("rally.cli.commands.verify.VerifyCommands.use")
    @mock.patch("rally.cli.commands.verify.open", create=True)
    @mock.patch("rally.cli.commands.verify.os.path.exists")
    def test_import_results(self, mock_exists, mock_open, mock_use):
        mock_exists.return_value = False
        self.verify.import_results(self.fake_api, self.verifier_uuid,
                                   self.deployment_uuid)
        self.assertFalse(self.fake_api.verification.import_results.called)

        verification = self.verification_data
        results = self.results_data
        self.fake_api.verification.import_results.return_value = (
            verification, results)

        mock_exists.return_value = True
        mock_open.return_value = mock.mock_open(read_data="data").return_value
        self.verify.import_results(self.fake_api,
                                   verifier_id=self.verifier_uuid,
                                   deployment=self.deployment_uuid,
                                   file_to_parse="/p/a/t/h")
        mock_open.assert_called_once_with("/p/a/t/h", "r")
        self.fake_api.verification.import_results.assert_called_once_with(
            verifier_id=self.verifier_uuid,
            deployment_id=self.deployment_uuid,
            data="data")

        mock_use.assert_called_with(self.fake_api, self.verification_uuid)

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
