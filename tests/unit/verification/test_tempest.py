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

import copy
import os
import subprocess

import ddt
import mock

from rally import exceptions
from rally.verification.tempest import tempest
from tests.unit import test


TEMPEST_PATH = "rally.verification.tempest"


class BaseTestCase(test.TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.base_repo_patcher = mock.patch.object(tempest.Tempest,
                                                   "base_repo", "foo-baserepo")
        self.base_repo_dir_patcher = mock.patch.object(tempest.Tempest,
                                                       "base_repo_dir",
                                                       "foo-baserepodir")
        self.verifier = tempest.Tempest("fake_deployment_id",
                                        verification=mock.MagicMock())

        self.verifier._path = "/tmp"
        self.verifier.config_file = "/tmp/tempest.conf"
        self.verifier.log_file_raw = "/tmp/subunit.stream"


class TempestUtilsTestCase(BaseTestCase):
    def test_path(self):
        self.assertEqual("/tmp", self.verifier.path())
        self.assertEqual("/tmp/foo", self.verifier.path("foo"))
        self.assertEqual("/tmp/foo/bar", self.verifier.path("foo", "bar"))

    @mock.patch("os.path.exists")
    def test_is_installed(self, mock_exists):
        # Check that `is_installed` depends on existence of path
        # os.path.exists == True => is_installed == True
        mock_exists.return_value = True
        self.assertTrue(self.verifier.is_installed())

        # os.path.exists == False => is_installed == False
        mock_exists.return_value = False
        self.assertFalse(self.verifier.is_installed())

        self.assertEqual([mock.call(self.verifier.path(".venv")),
                          mock.call(self.verifier.path(".testrepository")),
                          mock.call(self.verifier.path(".venv"))],
                         mock_exists.call_args_list)

    @mock.patch("os.environ")
    def test_env_missed(self, mock_environ):
        expected_env = {"PATH": "/some/path"}
        mock_environ.copy.return_value = copy.deepcopy(expected_env)
        expected_env.update({
            "TEMPEST_CONFIG": "tempest.conf",
            "TEMPEST_CONFIG_DIR": self.verifier.path(),
            "OS_TEST_PATH": self.verifier.path("tempest/test_discover")})
        self.assertIsNone(self.verifier._env)
        self.assertEqual(expected_env, self.verifier.env)
        self.assertTrue(mock_environ.copy.called)
        self.assertEqual(expected_env, self.verifier._env)

    @mock.patch("os.environ")
    def test_env_loaded(self, mock_environ):
        self.verifier._env = {"foo": "bar"}
        self.verifier.env
        self.assertFalse(mock_environ.copy.called)

    @mock.patch("os.path.isdir", return_value=True)
    @mock.patch(TEMPEST_PATH + ".tempest.check_output")
    def test__venv_install_when_venv_exists(self, mock_check_output,
                                            mock_isdir):
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(self.verifier.path(".venv"))
        self.assertFalse(mock_check_output.called)

    @mock.patch("%s.tempest.sys" % TEMPEST_PATH)
    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch("%s.tempest.check_output" % TEMPEST_PATH,
                return_value="some_output")
    def test__venv_install_when_venv_does_not_exist(self, mock_check_output,
                                                    mock_isdir, mock_sys):
        mock_sys.version_info = "not_py27_env"
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(self.verifier.path(".venv"))
        mock_check_output.assert_has_calls([
            mock.call(["virtualenv", "-p", mock_sys.executable, ".venv"],
                      cwd="/tmp"),
            mock.call(["/tmp/tools/with_venv.sh", "pip",
                       "install", "-e", "./"], cwd="/tmp")
        ])

    @mock.patch("%s.tempest.sys" % TEMPEST_PATH)
    @mock.patch("os.path.isdir", return_value=False)
    def test__venv_install_fails__when_py27_is_not_present(
            self, mock_isdir, mock_sys):
        mock_sys.version_info = "not_py27_env"
        mock_sys.executable = "fake_path"

        self.assertRaises(tempest.TempestSetupFailure,
                          self.verifier._install_venv)

        mock_isdir.assert_called_once_with(self.verifier.path(".venv"))

    @mock.patch("os.path.isdir", return_value=True)
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    def test__initialize_testr_when_testr_already_initialized(
            self, mock_subprocess, mock_isdir):
        self.verifier._initialize_testr()

        mock_isdir.assert_called_once_with(
            self.verifier.path(".testrepository"))
        self.assertFalse(mock_subprocess.called)

    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch(TEMPEST_PATH + ".tempest.check_output")
    def test__initialize_testr_when_testr_not_initialized(
            self, mock_check_output, mock_isdir):
        self.verifier._initialize_testr()

        mock_isdir.assert_called_once_with(
            self.verifier.path(".testrepository"))
        mock_check_output.assert_called_once_with(
            [self.verifier.venv_wrapper, "testr", "init"],
            cwd=self.verifier.path())

    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch(TEMPEST_PATH + ".tempest.check_output")
    def test__initialize_testr_when_initialisation_failed(
            self, mock_check_output, mock_isdir):
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")
        self.assertRaises(tempest.TempestSetupFailure,
                          self.verifier._initialize_testr)

        mock_check_output.side_effect = OSError()
        self.assertRaises(tempest.TempestSetupFailure,
                          self.verifier._initialize_testr)

    @mock.patch("%s.tempest.subunit_v2.parse_results_file" % TEMPEST_PATH)
    @mock.patch("os.path.isfile", return_value=False)
    def test__save_results_without_log_file(
            self, mock_isfile, mock_parse_results_file):

        self.verifier._save_results()
        mock_isfile.assert_called_once_with(self.verifier.log_file_raw)
        self.assertEqual(0, mock_parse_results_file.call_count)

    @mock.patch("%s.tempest.subunit_v2.parse_results_file" % TEMPEST_PATH)
    @mock.patch("os.path.isfile", return_value=True)
    def test__save_results_with_log_file(self, mock_isfile,
                                         mock_parse_results_file):
        results = mock.MagicMock(total="some", tests=["some_test_1"])
        mock_parse_results_file.return_value = results
        self.verifier.log_file_raw = os.path.join(
            os.path.dirname(__file__), "subunit.stream")
        self.verifier._save_results()
        mock_isfile.assert_called_once_with(self.verifier.log_file_raw)
        mock_parse_results_file.assert_called_once_with(
            self.verifier.log_file_raw, None)

        verification = self.verifier.verification
        verification.finish_verification.assert_called_once_with(
            total="some", test_cases=["some_test_1"])


class TempestInstallAndUninstallTestCase(BaseTestCase):

    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    def test__clone_successful(self, mock_check_call):
        with self.base_repo_patcher:
            self.verifier._clone()
            mock_check_call.assert_called_once_with(
                ["git", "clone", tempest.TEMPEST_SOURCE, "foo-baserepo"])

    def test__no_dir(self):
        with mock.patch("os.path.isdir", return_value=False):
            self.assertFalse(self.verifier._is_git_repo("fake_dir"))

    @mock.patch("subprocess.call", return_value=1)
    @mock.patch("os.path.isdir", return_value=True)
    def test__is_not_git_repo(self, mock_isdir, mock_call):
        self.assertFalse(self.verifier._is_git_repo("fake_dir"))

    @mock.patch("subprocess.call", return_value=0)
    @mock.patch("os.path.isdir", return_value=True)
    def test__is_git_repo(self, mock_isdir, mock_call):
        self.assertTrue(self.verifier._is_git_repo("fake_dir"))

    @mock.patch("%s.tempest.check_output" % TEMPEST_PATH,
                return_value="fake_url")
    def test__get_remote_origin(self, mock_check_output):
        self.assertEqual("fake_url",
                         self.verifier._get_remote_origin("fake_dir"))

    @mock.patch("shutil.rmtree")
    @mock.patch(TEMPEST_PATH + ".tempest.os.path.exists", return_value=True)
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    def test__clone_failed(self, mock_check_call, mock_exists, mock_rmtree):
        with self.base_repo_patcher:
            # Check that `subprocess.CalledProcessError` is not handled
            # by `_clone`
            mock_check_call.side_effect = subprocess.CalledProcessError(
                0, None)

            self.assertRaises(subprocess.CalledProcessError,
                              self.verifier._clone)
            mock_check_call.assert_called_once_with(
                ["git", "clone", tempest.TEMPEST_SOURCE, "foo-baserepo"])
            mock_rmtree.assert_called_once_with(self.verifier.base_repo)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.base_repo")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._initialize_testr")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._install_venv")
    @mock.patch(TEMPEST_PATH + ".tempest.check_output")
    @mock.patch("shutil.copytree")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._clone")
    @mock.patch("os.path.exists", return_value=False)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._is_git_repo",
                return_value=False)
    def test_install_successful(self, mock_tempest__is_git_repo, mock_exists,
                                mock_tempest__clone, mock_copytree,
                                mock_check_output, mock_tempest__install_venv,
                                mock_tempest__initialize_testr,
                                mock_tempest_base_repo):
        mock_tempest_base_repo.__get__ = mock.Mock(return_value="fake_dir")
        self.verifier.version = "3f4c8d44"
        self.verifier.install()

        mock_tempest__is_git_repo.assert_called_once_with(
            self.verifier.base_repo)
        mock_exists.assert_has_calls([mock.call(self.verifier.path(".venv")),
                                      mock.call(self.verifier.path())])
        mock_tempest__clone.assert_called_once_with()
        mock_copytree.assert_called_once_with(
            self.verifier.base_repo,
            self.verifier.path())
        cwd = self.verifier.path()
        expected = [mock.call(["git", "checkout", "3f4c8d44"], cwd=cwd)]
        self.assertEqual(expected, mock_check_output.mock_calls)
        mock_tempest__install_venv.assert_called_once_with()
        mock_tempest__initialize_testr.assert_called_once_with()

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.base_repo")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.uninstall")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._initialize_testr")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._install_venv")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    @mock.patch("shutil.copytree")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._clone")
    @mock.patch("os.path.exists", return_value=False)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._is_git_repo",
                return_value=False)
    def test_install_failed(self, mock_tempest__is_git_repo, mock_exists,
                            mock_tempest__clone,
                            mock_copytree, mock_check_call,
                            mock_tempest__install_venv,
                            mock_tempest__initialize_testr,
                            mock_tempest_uninstall,
                            mock_tempest_base_repo):
        mock_tempest_base_repo.__get__ = mock.Mock(return_value="fake_dir")
        mock_check_call.side_effect = subprocess.CalledProcessError(0, None)

        self.verifier.version = "3f4c8d44"
        self.assertRaises(tempest.TempestSetupFailure, self.verifier.install)

        mock_tempest__is_git_repo.assert_called_once_with(
            self.verifier.base_repo)
        mock_exists.assert_has_calls([mock.call(self.verifier.path(".venv")),
                                      mock.call(self.verifier.path())])
        mock_tempest__clone.assert_called_once_with()
        mock_copytree.assert_called_once_with(
            self.verifier.base_repo,
            self.verifier.path())
        self.assertFalse(mock_tempest__install_venv.called)
        self.assertFalse(mock_tempest__initialize_testr.called)
        mock_tempest_uninstall.assert_called_once_with()

    @mock.patch("shutil.rmtree")
    @mock.patch("os.path.exists", return_value=True)
    def test_uninstall(self, mock_exists, mock_rmtree):
        self.verifier.uninstall()
        mock_exists.assert_called_once_with(self.verifier.path())
        mock_rmtree.assert_called_once_with(self.verifier.path())

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._is_git_repo",
                return_value=True)
    @mock.patch("tempfile.mkdtemp", return_value="fake_tempest_dir")
    @mock.patch("os.listdir", return_value=["fake_dir"])
    @mock.patch("shutil.move")
    @mock.patch("os.path.exists", return_value=True)
    def test_upgrade_repo_tree(self, mock_exists, mock_move, mock_listdir,
                               mock_mkdtemp,
                               mock_tempest__is_git_repo):
        with self.base_repo_dir_patcher as foo_base:
            self.verifier._base_repo = "fake_base"
            self.verifier.base_repo
            directory = mock_mkdtemp.return_value
            mock_listdir.assert_called_once_with(foo_base)
            fake_dir = mock_listdir.return_value[0]
            source = os.path.join(self.base_repo_dir_patcher.new, fake_dir)
            dest = os.path.join(directory, fake_dir)
            mock_move.assert_called_once_with(source, dest)


@ddt.ddt
class TempestInstallPluginsTestCase(BaseTestCase):

    @mock.patch(TEMPEST_PATH + ".tempest.check_output")
    @ddt.data("https://github.com/fake-plugin.git", "/tmp/fake-plugin")
    def test_install_plugin(self, plugin_source, mock_tempest_check_output):
        self.verifier.plugin_source = plugin_source
        self.verifier.install_plugin()

        cmd = [self.verifier.venv_wrapper, "pip", "install",
               "--src", self.verifier.path("plugins"), "-e",
               "git+{0}@master#egg={1}".format(plugin_source, "fake-plugin")]
        mock_tempest_check_output.assert_called_with(cmd,
                                                     cwd=self.verifier.path())

    @mock.patch(TEMPEST_PATH + ".tempest.check_output")
    def test_list_plugins(self, mock_tempest_check_output):
        self.verifier.list_plugins()

        cmd = [self.verifier.venv_wrapper, "tempest", "list-plugins"]
        mock_tempest_check_output.assert_called_with(
            cmd, cwd=self.verifier.path(), debug=False)

    @mock.patch("shutil.rmtree")
    @mock.patch("os.path.exists")
    def test_uninstall_plugin(self, mock_exists, mock_rmtree):
        self.verifier.uninstall_plugin("fake-plugin")
        mock_rmtree.assert_called_once_with(
            self.verifier.path("plugins/fake-plugin"))


class TempestVerifyTestCase(BaseTestCase):
    def _get_fake_call(self, testr_args,
                       concur_args="--parallel --concurrency 0"):
        return (
            "%(venv)s testr run --subunit %(concur_args)s %(testr_args)s"
            " | tee %(log_file)s"
            " | %(venv)s subunit-trace -f -n" % {
                "venv": self.verifier.venv_wrapper,
                "concur_args": concur_args,
                "testr_args": testr_args,
                "log_file": self.verifier.path("subunit.stream")})

    @mock.patch(TEMPEST_PATH + ".config.TempestConfig")
    def test_verify_no_tempest_config_exists(self, mock_tempest_config):
        self.assertRaises(exceptions.NotFoundException, self.verifier.verify,
                          "compute", None, None, None, None, 0, False)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    def test_verify_tempest_config_exists(
            self, mock_isfile, mock_tempest_resources_context, mock_subprocess,
            mock_tempest_env, mock_tempest_parse_results):
        set_name = "identity"
        fake_call = self._get_fake_call("tempest.api.%s" % set_name)

        self.verifier.verify(set_name, None, None, None, None, 0, False)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    def test_verify_failed_and_tempest_config_exists(
            self, mock_isfile, mock_tempest_resources_context, mock_subprocess,
            mock_tempest_env, mock_tempest_parse_results):
        set_name = "identity"
        fake_call = self._get_fake_call("tempest.api.%s" % set_name)
        mock_subprocess.side_effect = subprocess.CalledProcessError

        self.verifier.verify(set_name, None, None, None, None, 0, False)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)
        self.verifier.verification.set_failed.assert_called_once_with()

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    def test_verify_tests_file_specified(
            self, mock_isfile, mock_tempest_resources_context,
            mock_subprocess, mock_tempest_env, mock_tempest_parse_results):
        tests_file = "/path/to/tests/file"
        fake_call = self._get_fake_call("--load-list %s" % tests_file)

        self.verifier.verify("", None, tests_file, None, None, 0, False)
        self.verifier.verification.start_verifying.assert_called_once_with("")

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch("tempfile.NamedTemporaryFile", return_value=mock.MagicMock())
    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    def test_verify_tests_file_to_skip_specified(
            self, mock_open, mock_named_temporary_file, mock_isfile,
            mock_tempest_resources_context, mock_subprocess, mock_tempest_env,
            mock_tempest_parse_results):
        mock_named_temporary_file.return_value.name = "some-file-name"
        fake_call = self._get_fake_call("--load-list some-file-name")

        tests_file_to_skip = "/path/to/tests/file"
        self.verifier.verify(
            "", None, None, tests_file_to_skip, None, 0, False)
        self.verifier.verification.start_verifying.assert_called_once_with("")

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    def test_verify_concurrency_equals_to_1(
            self, mock_isfile, mock_tempest_resources_context,
            mock_subprocess, mock_tempest_env, mock_tempest_parse_results):
        set_name = "identity"
        fake_call = self._get_fake_call(
            "tempest.api.%s" % set_name, "--concurrency 1")

        self.verifier.verify("identity", None, None, None, None, 1, False)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    def test_verify_concurrency_doesnt_equal_to_1(
            self, mock_isfile, mock_tempest_resources_context,
            mock_subprocess, mock_tempest_env, mock_tempest_parse_results):
        set_name = "identity"
        fake_call = self._get_fake_call("tempest.api.%s" % set_name)

        self.verifier.verify("identity", None, None, None, None, 0, False)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=None)
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestResourcesContext")
    @mock.patch("os.path.isfile", return_value=True)
    def test_verify_run_failed_tests_(self, mock_isfile,
                                      mock_tempest_resources_context,
                                      mock_subprocess, mock_tempest_env,
                                      mock_tempest_parse_results):
        fake_call = self._get_fake_call("--failing")
        self.verifier.verify("", None, None, None, None, 0, True)

        self.verifier.verification.start_verifying.assert_called_once_with(
            "re-run-failed")

        mock_subprocess.check_call.assert_called_once_with(
            fake_call, env=mock_tempest_env, cwd=self.verifier.path(),
            shell=True)
        mock_tempest_parse_results.assert_called_once_with(None, None)

    def test_import_results(self):
        set_name = "identity"
        log_file = "log_file"

        self.verifier._save_results = mock.Mock()
        self.verifier.import_results(set_name, log_file)
        mock_start_verifying = self.verifier.verification.start_verifying
        mock_start_verifying.assert_called_once_with(set_name)
        self.verifier._save_results.assert_called_once_with(log_file)
