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
import os.path
import tempfile

import mock

from rally.cli.commands import verify
from rally import consts
from rally import exceptions
from tests.unit import test


class VerifyCommandsTestCase(test.TestCase):
    def setUp(self):
        super(VerifyCommandsTestCase, self).setUp()
        self.verify = verify.VerifyCommands()

        self.image1 = mock.Mock()
        self.image1.name = "cirros-1"
        self.image1.id = "fake_image_id_1"
        self.image2 = mock.Mock()
        self.image2.id = "fake_image_id_2"
        self.image2.name = "cirros-2"

        self.flavor1 = mock.Mock()
        self.flavor2 = mock.Mock()
        self.flavor1.id = "fake_flavor_id_1"
        self.flavor2.id = "fake_flavor_id_2"
        self.flavor1.ram = 128
        self.flavor2.ram = 64

    @mock.patch("rally.osclients.Clients")
    @mock.patch("rally.api.Verification.verify")
    def test_start(self, mock_verification_verify, mock_clients):
        deployment_id = "0fba91c6-82d5-4ce1-bd00-5d7c989552d9"
        mock_clients().glance().images.list.return_value = [
            self.image1, self.image2]
        mock_clients().nova().flavors.list.return_value = [
            self.flavor1, self.flavor2]

        self.verify.start(deployment=deployment_id, do_use=False)

        mock_verification_verify.assert_called_once_with(
            deployment_id, set_name="full", regex=None, tests_file=None,
            tests_file_to_skip=None, tempest_config=None,
            expected_failures=None, system_wide=False, concur=0, failing=False)

    @mock.patch("rally.osclients.Clients")
    @mock.patch("rally.api.Verification.verify")
    def test_start_with_user_specified_tempest_config(
            self, mock_verification_verify, mock_clients):
        deployment_id = "0fba91c6-82d5-4ce1-bd00-5d7c989552d9"
        mock_clients().glance().images.list.return_value = [
            self.image1, self.image2]
        mock_clients().nova().flavors.list.return_value = [
            self.flavor1, self.flavor2]
        tempest_config = tempfile.NamedTemporaryFile()
        self.verify.start(deployment=deployment_id,
                          tempest_config=tempest_config.name, do_use=False)

        mock_verification_verify.assert_called_once_with(
            deployment_id, set_name="full", regex=None, tests_file=None,
            tests_file_to_skip=None, tempest_config=tempest_config.name,
            expected_failures=None, system_wide=False, concur=0, failing=False)
        tempest_config.close()

    @mock.patch("rally.api.Verification.verify")
    @mock.patch("os.path.exists", return_value=True)
    def test_start_with_tests_file_specified(self, mock_exists,
                                             mock_verification_verify):
        deployment_id = "f05645f9-b3d1-4be4-ae63-ae6ea6d89f17"
        tests_file = "/path/to/tests/file"
        self.verify.start(deployment=deployment_id,
                          tests_file=tests_file, do_use=False)

        mock_verification_verify.assert_called_once_with(
            deployment_id, set_name="", regex=None, tests_file=tests_file,
            tests_file_to_skip=None, tempest_config=None,
            expected_failures=None, system_wide=False, concur=0, failing=False)

    @mock.patch("rally.api.Verification.verify")
    @mock.patch("six.moves.builtins.open",
                side_effect=mock.mock_open(read_data="test: reason of fail"))
    @mock.patch("os.path.exists", return_value=True)
    def test_start_with_xfails_file_specified(self, mock_exists, mock_open,
                                              mock_verification_verify):
        deployment_id = "eba53a0e-e2e6-451c-9a29-bdd2efc245e7"
        xfails_file = "/path/to/xfails/file"
        self.verify.start(deployment=deployment_id,
                          xfails_file=xfails_file, do_use=False)

        mock_verification_verify.assert_called_once_with(
            deployment_id, set_name="full", regex=None, tests_file=None,
            tests_file_to_skip=None, tempest_config=None,
            expected_failures={"test": "reason of fail"}, system_wide=False,
            concur=0, failing=False)

    @mock.patch("rally.api.Verification.verify")
    def test_start_with_wrong_set_name(self, mock_verification_verify):
        deployment_id = "f2009aae-6ef3-468e-96b2-3c987d584010"

        wrong_set_name = "unexpected_value"

        self.verify.start(deployment_id, set_name=wrong_set_name, do_use=False)

        self.assertNotIn(wrong_set_name, consts.TempestTestsSets,
                         consts.TempestTestsAPI)
        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.verify")
    def test_start_with_set_name_and_regex(self, mock_verification_verify):
        deployment_id = "2856e214-90d1-4d82-9402-dd13973ca0f6"

        set_name = "identity"
        regex = "tempest.api.compute"
        self.verify.start(set_name=set_name, regex=regex,
                          deployment=deployment_id, do_use=False)

        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.verify")
    def test_start_with_tests_file_and_tests_file_to_skip(
            self, mock_verification_verify):
        deployment_id = "3580e214-90d1-4d82-9402-dd13973ca0f6"

        tests_file = "/path/to/tests/file-1"
        tests_file_to_skip = "/path/to/tests/file-2"
        self.verify.start(tests_file=tests_file,
                          tests_file_to_skip=tests_file_to_skip,
                          deployment=deployment_id, do_use=False)

        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.verify")
    def test_start_with_failing_and_set_name(self, mock_verification_verify):
        deployment_id = "f2009aae-6ef3-468e-96b2-3c987d584010"

        set_name = "some_value"
        self.verify.start(set_name=set_name, deployment=deployment_id,
                          do_use=False, failing=True)

        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.verify")
    def test_start_with_failing_and_regex(self, mock_verification_verify):
        deployment_id = "25d19aec-f39e-459e-b3d5-24a718e92233"

        regex = "tempest.api.compute"
        self.verify.start(regex=regex, deployment=deployment_id, do_use=False,
                          failing=True)

        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.verify")
    @mock.patch("os.path.exists", return_value=True)
    def test_start_with_failing_and_test_files(self, mock_exists,
                                               mock_verification_verify):
        deployment_id = "f2009aae-6ef3-468e-96b2-3c987d584010"
        tests_file = "/path/to/tests/file"

        self.verify.start(tests_file=tests_file, deployment=deployment_id,
                          do_use=False, failing=True)

        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.verify")
    @mock.patch("os.path.exists", return_value=True)
    def test_start_with_failing_and_test_files_to_skip(
            self, mock_exists, mock_verification_verify):
        deployment_id = "7902051d-8286-4cfc-aec5-addde73b3a1f"

        tests_file = "/path/to/tests/file"
        self.verify.start(tests_file_to_skip=tests_file,
                          deployment=deployment_id, do_use=False, failing=True)

        self.assertFalse(mock_verification_verify.called)

    @mock.patch("rally.api.Verification.import_results")
    def test_import_results(self, mock_verification_import_results):
        deployment_id = "fake_deployment_uuid"
        fake_verification = {"uuid": "fake_verification_uuid"}
        mock_verification_import_results.return_value = (None,
                                                         fake_verification)
        self.verify.import_results(deployment=deployment_id, do_use=False)
        default_set_name = ""
        default_log_file = None

        mock_verification_import_results.assert_called_once_with(
            deployment_id, default_set_name, default_log_file)

    @mock.patch("rally.api.Verification.import_results")
    def test_import_results_without_defaults(self,
                                             mock_verification_import_results):
        deployment_id = "fake_uuid"
        set_name = "fake_set_name"
        log_file = "fake_log_file"
        fake_verification = {"uuid": "fake_verification_uuid"}
        mock_verification_import_results.return_value = (None,
                                                         fake_verification)
        self.verify.import_results(deployment=deployment_id, set_name=set_name,
                                   log_file=log_file, do_use=False)

        mock_verification_import_results.assert_called_once_with(
            deployment_id, set_name, log_file)

    @mock.patch("rally.cli.cliutils.print_list")
    @mock.patch("rally.api.Verification.list")
    def test_list(self, mock_verification_list, mock_print_list):
        fields = ["UUID", "Deployment UUID", "Set name", "Tests", "Failures",
                  "Created at", "Duration", "Status"]
        verifications = [{"created_at": dt.datetime.now(),
                          "updated_at": dt.datetime.now()}]
        mock_verification_list.return_value = verifications
        self.verify.list()

        for row in verifications:
            self.assertEqual(row["updated_at"] - row["created_at"],
                             row["duration"])

        mock_verification_list.assert_called_once_with()
        mock_print_list.assert_called_once_with(verifications, fields,
                                                normalize_field_names=True,
                                                sortby_index=fields.index(
                                                    "Created at"))

    @mock.patch("rally.cli.cliutils.print_list")
    @mock.patch("rally.common.utils.Struct")
    @mock.patch("rally.api.Verification")
    def test_show(self, mock_verification, mock_struct, mock_print_list):
        verification = mock_verification.get.return_value

        tests = {"test_cases": {"test_a": {"name": "test_a", "time": 20,
                                           "status": "success"},
                                "test_b": {"name": "test_b", "time": 20,
                                           "status": "skip"},
                                "test_c": {"name": "test_c", "time": 20,
                                           "status": "fail"}}}

        verification_id = "39121186-b9a4-421d-b094-6c6b270cf9e9"
        total_fields = ["UUID", "Deployment UUID", "Set name", "Tests",
                        "Failures", "Created at", "Status"]
        fields = ["name", "time", "status"]
        verification.get_results.return_value = tests
        values = [mock_struct(), mock_struct(), mock_struct()]

        self.verify.show(verification_id)

        self.assertEqual([mock.call([verification], fields=total_fields,
                                    normalize_field_names=True,),
                          mock.call(values, fields, sortby_index=0)],
                         mock_print_list.call_args_list)
        mock_verification.get.assert_called_once_with(verification_id)

    @mock.patch("rally.api.Verification")
    @mock.patch("json.dumps")
    def test_results(self, mock_json_dumps, mock_verification):
        mock_verification.get.return_value.get_results.return_value = {}
        verification_uuid = "a0231bdf-6a4e-4daf-8ab1-ae076f75f070"
        self.verify.results(verification_uuid, output_html=False,
                            output_json=True)

        mock_verification.get.assert_called_once_with(verification_uuid)
        mock_json_dumps.assert_called_once_with({}, sort_keys=True, indent=4)

    @mock.patch("rally.api.Verification.get")
    def test_results_verification_not_found(
            self, mock_verification_get):
        verification_uuid = "9044ced5-9c84-4666-8a8f-4b73a2b62acb"
        mock_verification_get.side_effect = (
            exceptions.NotFoundException()
        )
        self.assertEqual(self.verify.results(verification_uuid,
                                             output_html=False,
                                             output_json=True), 1)

        mock_verification_get.assert_called_once_with(verification_uuid)

    @mock.patch("rally.cli.commands.verify.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.api.Verification")
    def test_results_with_output_json_and_output_file(
            self, mock_verification, mock_open):
        mock_verification.get.return_value.get_results.return_value = {}
        mock_open.side_effect = mock.mock_open()
        verification_uuid = "94615cd4-ff45-4123-86bd-4b0741541d09"
        self.verify.results(verification_uuid, output_file="results",
                            output_html=False, output_json=True)

        mock_verification.get.assert_called_once_with(verification_uuid)
        mock_open.assert_called_once_with("results", "wb")
        mock_open.side_effect().write.assert_called_once_with("{}")

    @mock.patch("rally.cli.commands.verify.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.api.Verification")
    @mock.patch("rally.verification.tempest.json2html.generate_report")
    def test_results_with_output_html_and_output_file(
            self, mock_generate_report, mock_verification, mock_open):

        verification_uuid = "7140dd59-3a7b-41fd-a3ef-5e3e615d7dfa"
        self.verify.results(verification_uuid, output_html=True,
                            output_json=False, output_file="results")

        mock_verification.get.assert_called_once_with(verification_uuid)
        mock_generate_report.assert_called_once_with(
            mock_verification.get.return_value.get_results.return_value)
        mock_open.assert_called_once_with("results", "wb")
        mock_open.side_effect().write.assert_called_once_with(
            mock_generate_report.return_value)

    @mock.patch("rally.api.Verification")
    @mock.patch("json.dumps")
    def test_compare(self, mock_json_dumps, mock_verification):
        mock_verification.get.return_value.get_results.return_value = {
            "test_cases": {}}
        uuid1 = "8eda1b10-c8a4-4316-9603-8468ff1d1560"
        uuid2 = "f6ef0a98-1b18-452f-a6a7-922555c2e326"
        self.verify.compare(uuid1, uuid2, output_csv=False, output_html=False,
                            output_json=True)

        fake_data = []
        calls = [mock.call(uuid1),
                 mock.call(uuid2)]
        mock_verification.get.assert_has_calls(calls, True)
        mock_json_dumps.assert_called_once_with(fake_data, sort_keys=True,
                                                indent=4)

    @mock.patch("rally.api.Verification.get",
                side_effect=exceptions.NotFoundException())
    def test_compare_verification_not_found(self, mock_verification_get):
        uuid1 = "f7dc82da-31a6-4d40-bbf8-6d366d58960f"
        uuid2 = "2f8a05f3-d310-4f02-aabf-e1165aaa5f9c"

        self.assertEqual(self.verify.compare(uuid1, uuid2, output_csv=False,
                                             output_html=False,
                                             output_json=True), 1)

        mock_verification_get.assert_called_once_with(uuid1)

    @mock.patch("rally.cli.commands.verify.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.api.Verification")
    def test_compare_with_output_csv_and_output_file(
            self, mock_verification, mock_open):
        mock_verification.get.return_value.get_results.return_value = {
            "test_cases": {}}

        fake_string = "Type,Field,Value 1,Value 2,Test Name\r\n"
        uuid1 = "5e744557-4c3a-414f-9afb-7d3d8708028f"
        uuid2 = "efe1c74d-a632-476e-bb6a-55a9aa9cf76b"
        self.verify.compare(uuid1, uuid2, output_file="results",
                            output_csv=True, output_html=False,
                            output_json=False)

        calls = [mock.call(uuid1),
                 mock.call(uuid2)]
        mock_verification.get.assert_has_calls(calls, True)
        mock_open.assert_called_once_with("results", "wb")
        mock_open.side_effect().write.assert_called_once_with(fake_string)

    @mock.patch("rally.cli.commands.verify.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.api.Verification")
    def test_compare_with_output_json_and_output_file(
            self, mock_verification, mock_open):
        mock_verification.get.return_value.get_results.return_value = {
            "test_cases": {}}

        fake_json_string = "[]"
        uuid1 = "0505e33a-738d-4474-a611-9db21547d863"
        uuid2 = "b1908417-934e-481c-8d23-bc0badad39ed"
        self.verify.compare(uuid1, uuid2, output_file="results",
                            output_csv=False, output_html=False,
                            output_json=True)

        calls = [mock.call(uuid1),
                 mock.call(uuid2)]
        mock_verification.get.assert_has_calls(calls, True)
        mock_open.assert_called_once_with("results", "wb")
        mock_open.side_effect().write.assert_called_once_with(fake_json_string)

    @mock.patch("rally.cli.commands.verify.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.api.Verification")
    @mock.patch("rally.verification.tempest.compare2html.create_report",
                return_value="")
    def test_compare_with_output_html_and_output_file(
            self, mock_compare2html_create_report,
            mock_verification, mock_open):
        mock_verification.get.return_value.get_results.return_value = {
            "test_cases": {}}

        uuid1 = "cdf64228-77e9-414d-9d4b-f65e9d62c61f"
        uuid2 = "39393eec-1b45-4103-8ec1-631edac4b8f0"

        fake_data = []
        self.verify.compare(uuid1, uuid2,
                            output_file="results",
                            output_csv=False, output_html=True,
                            output_json=False)
        calls = [mock.call(uuid1),
                 mock.call(uuid2)]
        mock_verification.get.assert_has_calls(calls, True)
        mock_compare2html_create_report.assert_called_once_with(fake_data)

        mock_open.assert_called_once_with("results", "wb")
        mock_open.side_effect().write.assert_called_once_with("")

    @mock.patch("rally.common.fileutils._rewrite_env_file")
    @mock.patch("rally.api.Verification.get")
    def test_use(self, mock_verification_get, mock__rewrite_env_file):
        verification_id = "80422553-5774-44bd-98ac-38bd8c7a0feb"
        self.verify.use(verification_id)
        mock__rewrite_env_file.assert_called_once_with(
            os.path.expanduser("~/.rally/globals"),
            ["RALLY_VERIFICATION=%s\n" % verification_id])

    @mock.patch("rally.api.Verification.get")
    def test_use_not_found(self, mock_verification_get):
        verification_id = "ddc3f8ba-082a-496d-b18f-72cdf5c10a14"
        mock_verification_get.side_effect = exceptions.NotFoundException(
            uuid=verification_id)
        self.assertRaises(exceptions.NotFoundException, self.verify.use,
                          verification_id)

    @mock.patch("rally.api.Verification.configure_tempest")
    def test_genconfig(self, mock_verification_configure_tempest):
        deployment_id = "14377d10-ca77-4104-aba8-36edebcfc120"
        self.verify.genconfig(deployment_id)
        mock_verification_configure_tempest.assert_called_once_with(
            deployment_id, None, None, False)

    @mock.patch("rally.api.Verification.configure_tempest")
    def test_genconfig_with_config_specified(
            self, mock_verification_configure_tempest):
        deployment_id = "68b501af-a553-431c-83ac-30f93a112231"
        tempest_conf = "/tmp/tempest.conf"
        self.verify.genconfig(deployment_id, tempest_config=tempest_conf)
        mock_verification_configure_tempest.assert_called_once_with(
            deployment_id, tempest_conf, None, False)

    @mock.patch("rally.api.Verification.configure_tempest")
    @mock.patch("six.moves.configparser.ConfigParser")
    @mock.patch("os.path.exists", return_value=True)
    def test_genconfig_with_extra_conf_path_specified(
            self, mock_exists, mock_config_parser,
            mock_verification_configure_tempest):
        deployment_id = "68b501af-a553-431c-83ac-30f93a112231"
        extra_conf_path = "/tmp/extra.conf"
        self.verify.genconfig(deployment_id, extra_conf_path=extra_conf_path)
        mock_verification_configure_tempest.assert_called_once_with(
            deployment_id, None, mock_config_parser(), False)

    @mock.patch("rally.api.Verification.configure_tempest")
    def test_genconfig_override_config(
            self, mock_verification_configure_tempest):
        deployment_id = "cd5b64ad-c12f-4781-a89e-95535b145a11"
        self.verify.genconfig(deployment_id, override=True)
        mock_verification_configure_tempest.assert_called_once_with(
            deployment_id, None, None, True)

    @mock.patch("rally.api.Verification.configure_tempest")
    @mock.patch("six.moves.configparser.ConfigParser")
    @mock.patch("os.path.exists", return_value=True)
    def test_genconfig_with_all_args_specified(
            self, mock_exists, mock_config_parser,
            mock_verification_configure_tempest):
        deployment_id = "89982aba-efef-48cb-8d94-ca893b4e78a6"
        tempest_conf_path = "/tmp/tempest.conf"
        extra_conf_path = "/tmp/extra-tempest.conf"
        self.verify.genconfig(deployment_id, tempest_config=tempest_conf_path,
                              extra_conf_path=extra_conf_path, override=True)
        mock_verification_configure_tempest.assert_called_once_with(
            deployment_id, tempest_conf_path, mock_config_parser(), True)

    @mock.patch("rally.api.Verification.install_tempest")
    def test_install(self, mock_verification_install_tempest):
        deployment_uuid = "d26ebebc-3a5f-4d0d-9021-0c883bd560f5"
        self.verify.install(deployment_uuid)
        mock_verification_install_tempest.assert_called_once_with(
            deployment_uuid, None, None, False)

    @mock.patch("rally.api.Verification.install_tempest")
    def test_install_with_source_specified(
            self, mock_verification_install_tempest):
        deployment_uuid = "83514de2-a770-4e28-82dd-2826b725e733"
        source = "/tmp/tempest"
        self.verify.install(deployment_uuid, source)
        mock_verification_install_tempest.assert_called_once_with(
            deployment_uuid, source, None, False)

    @mock.patch("rally.api.Verification.install_tempest")
    def test_install_with_version_specified(
            self, mock_verification_install_tempest):
        deployment_uuid = "206118f8-fa8e-43a6-a3d5-a7d047c4091a"
        version = "206118f8"
        self.verify.install(deployment_uuid, version=version)
        mock_verification_install_tempest.assert_called_once_with(
            deployment_uuid, None, version, False)

    @mock.patch("rally.api.Verification.uninstall_tempest")
    def test_uninstall(self, mock_verification_uninstall_tempest):
        deployment_uuid = "f92e7cb2-9fc7-43d4-a86e-8c924b025404"
        self.verify.uninstall(deployment_uuid)
        mock_verification_uninstall_tempest.assert_called_once_with(
            deployment_uuid)

    @mock.patch("rally.api.Verification.reinstall_tempest")
    def test_reinstall(self, mock_verification_reinstall_tempest):
        deployment_uuid = "05e0879b-9150-4e42-b6a0-3c6e48197cc1"
        self.verify.reinstall(deployment_uuid)
        mock_verification_reinstall_tempest.assert_called_once_with(
            deployment_uuid, None, None, False)

    @mock.patch("rally.api.Verification.reinstall_tempest")
    def test_reinstall_with_source_specified(
            self, mock_verification_reinstall_tempest):
        deployment_uuid = "9de60506-8c7a-409f-9ea6-2900f674532d"
        source = "/tmp/tempest"
        self.verify.reinstall(deployment_uuid, source=source)
        mock_verification_reinstall_tempest.assert_called_once_with(
            deployment_uuid, source, None, False)

    @mock.patch("rally.api.Verification.reinstall_tempest")
    def test_reinstall_with_version_specified(
            self, mock_verification_reinstall_tempest):
        deployment_uuid = "c0202924-fba7-442e-93dd-90bcd7282188"
        version = "c0202924"
        self.verify.reinstall(deployment_uuid, version=version)
        mock_verification_reinstall_tempest.assert_called_once_with(
            deployment_uuid, None, version, False)

    @mock.patch("rally.api.Verification.install_tempest_plugin")
    def test_installplugin_from_url(
            self, mock_verification_install_tempest_plugin):
        deployment_uuid = "83514de2-a770-4e28-82dd-2826b725e733"
        url = "https://github.com/fake/plugin"
        self.verify.installplugin(deployment_uuid, url)
        mock_verification_install_tempest_plugin.assert_called_once_with(
            deployment_uuid, url, None, False)

    @mock.patch("rally.api.Verification.install_tempest_plugin")
    def test_installplugin_from_path(
            self, mock_verification_install_tempest_plugin):
        deployment_uuid = "83514de2-a770-4e28-82dd-2826b725e733"
        path = "/tmp/fake/plugin"
        self.verify.installplugin(deployment_uuid, path)
        mock_verification_install_tempest_plugin.assert_called_once_with(
            deployment_uuid, path, None, False)

    @mock.patch("rally.api.Verification.list_tempest_plugins")
    def test_listplugins(self, mock_verification_list_tempest_plugins):
        deployment_uuid = "83514de2-a770-4e28-82dd-2826b725e733"
        self.verify.listplugins(deployment_uuid)
        mock_verification_list_tempest_plugins.assert_called_once_with(
            deployment_uuid, False)

    @mock.patch("rally.api.Verification.uninstall_tempest_plugin")
    def test_uninstallplugin(
            self, mock_verification_uninstall_tempest_plugin):
        deployment_uuid = "83514de2-a770-4e28-82dd-2826b725e733"
        self.verify.uninstallplugin(deployment_uuid, "fake-plugin")
        mock_verification_uninstall_tempest_plugin.assert_called_once_with(
            deployment_uuid, "fake-plugin", False)

    @mock.patch("rally.api.Verification.discover_tests")
    def test_discover(self, mock_verification_discover_tests):
        deployment_uuid = "97725f22-1cd2-46a5-8c62-3cdc36ed6d2a"
        self.verify.discover(deployment_uuid, "some_pattern")
        mock_verification_discover_tests.assert_called_once_with(
            deployment_uuid, "some_pattern", False)

    @mock.patch("rally.api.Verification.show_config_info")
    def test_showconfig(self, mock_verification_show_config_info):
        deployment_uuid = "571368f4-20dd-443c-a188-4e931cd2abe6"
        self.verify.showconfig(deployment_uuid)
        mock_verification_show_config_info.assert_called_once_with(
            deployment_uuid)
