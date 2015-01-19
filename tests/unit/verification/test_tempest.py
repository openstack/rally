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
import sys

import mock
from oslo_serialization import jsonutils
import testtools

from rally import exceptions
from rally.verification.tempest import subunit2json
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
                          mock.call(self.verifier.path(".venv"))],
                         mock_exists.call_args_list)

    @mock.patch("os.environ")
    def test_env_missed(self, mock_env):
        expected_env = {"PATH": "/some/path"}
        mock_env.copy.return_value = copy.deepcopy(expected_env)
        expected_env.update({
            "TEMPEST_CONFIG": "tempest.conf",
            "TEMPEST_CONFIG_DIR": self.verifier.path(),
            "OS_TEST_PATH": self.verifier.path("tempest/test_discover")})
        self.assertIsNone(self.verifier._env)
        self.assertEqual(expected_env, self.verifier.env)
        self.assertTrue(mock_env.copy.called)
        self.assertEqual(expected_env, self.verifier._env)

    @mock.patch("os.environ")
    def test_env_loaded(self, mock_env):
        self.verifier._env = {"foo": "bar"}
        self.verifier.env
        self.assertFalse(mock_env.copy.called)

    @mock.patch("os.path.isdir", return_value=True)
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @testtools.skipIf(sys.version_info < (2, 7), "Incompatible Python Version")
    def test__venv_install_when_venv_exists(self, mock_sp, mock_isdir):
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(self.verifier.path(".venv"))
        self.assertFalse(mock_sp.check_output.called)

    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch("%s.tempest.subprocess.check_output" % TEMPEST_PATH,
                return_value="some_output")
    @testtools.skipIf(sys.version_info < (2, 7), "Incompatible Python Version")
    def test__venv_install_when_venv_not_exist(self, mock_sp, mock_isdir):
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(self.verifier.path(".venv"))
        mock_sp.assert_has_calls([
            mock.call("python ./tools/install_venv.py", shell=True,
                      cwd=self.verifier.path(), stderr=subprocess.STDOUT),
            mock.call("%s python setup.py install" %
                      self.verifier.venv_wrapper, shell=True,
                      cwd=self.verifier.path(), stderr=subprocess.STDOUT)])

    @mock.patch("os.path.isdir", return_value=False)
    @testtools.skipIf(sys.version_info >= (2, 7),
                      "Incompatible Python Version")
    def test__venv_install_for_py26_fails(self, mock_isdir):
        self.assertRaises(exceptions.IncompatiblePythonVersion,
                          self.verifier._install_venv)

        mock_isdir.assert_called_once_with(self.verifier.path(".venv"))

    @mock.patch("os.path.isdir", return_value=True)
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    def test__initialize_testr_when_testr_already_initialized(
            self, mock_sp, mock_isdir):
        self.verifier._initialize_testr()

        mock_isdir.assert_called_once_with(
            self.verifier.path(".testrepository"))
        self.assertFalse(mock_sp.called)

    @testtools.skipIf(sys.version_info < (2, 7), "Incompatible Python Version")
    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_output")
    def test__initialize_testr_when_testr_not_initialized(
            self, mock_sp, mock_isdir):
        self.verifier._initialize_testr()

        mock_isdir.assert_called_once_with(
            self.verifier.path(".testrepository"))
        mock_sp.assert_called_once_with(
            "%s testr init" % self.verifier.venv_wrapper, shell=True,
            cwd=self.verifier.path(), stderr=subprocess.STDOUT)

    @mock.patch.object(subunit2json, "main")
    @mock.patch("os.path.isfile", return_value=False)
    def test__save_results_without_log_file(self, mock_isfile, mock_parse):

        self.verifier._save_results()
        mock_isfile.assert_called_once_with(self.verifier.log_file_raw)
        self.assertEqual(0, mock_parse.call_count)

    @mock.patch("os.path.isfile", return_value=True)
    def test__save_results_with_log_file(self, mock_isfile):
        with mock.patch.object(subunit2json, "main") as mock_main:
            data = {"total": True, "test_cases": True}
            mock_main.return_value = jsonutils.dumps(data)
            self.verifier.log_file_raw = os.path.join(
                os.path.dirname(__file__), "subunit.stream")
            self.verifier._save_results()
            mock_isfile.assert_called_once_with(self.verifier.log_file_raw)
            mock_main.assert_called_once_with(
                self.verifier.log_file_raw)

            verification = self.verifier.verification
            verification.finish_verification.assert_called_once_with(**data)


class TempestInstallAndUninstallTestCase(BaseTestCase):

    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    def test__clone_successful(self, mock_sp):
        with self.base_repo_patcher:
            self.verifier._clone()
            mock_sp.assert_called_once_with(
                ["git", "clone", "https://github.com/openstack/tempest",
                 "foo-baserepo"])

    def test__no_dir(self):
        with mock.patch("os.path.isdir", return_value=False):
            self.assertFalse(self.verifier._is_git_repo("fake_dir"))

    @mock.patch("subprocess.call", return_value=1)
    @mock.patch("os.path.isdir", return_value=True)
    def test__is_not_git_repo(self, mock_isdir, mock_git_status):
        self.assertFalse(self.verifier._is_git_repo("fake_dir"))

    @mock.patch("subprocess.call", return_value=0)
    @mock.patch("os.path.isdir", return_value=True)
    def test__is_git_repo(self, mock_isdir, mock_git_status):
        self.assertTrue(self.verifier._is_git_repo("fake_dir"))

    @testtools.skipIf(sys.version_info < (2, 7), "Incompatible Python Version")
    @mock.patch("subprocess.check_output", return_value="fake_url")
    def test__get_remote_origin(self, mock_sp):
        with mock_sp:
            self.assertEqual("fake_url",
                             self.verifier._get_remote_origin("fake_dir"))

    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    def test__clone_failed(self, mock_sp):
        with self.base_repo_patcher:
            # Check that `subprocess.CalledProcessError` is not handled
            # by `_clone`
            mock_sp.side_effect = subprocess.CalledProcessError(0, None)

            self.assertRaises(subprocess.CalledProcessError,
                              self.verifier._clone)
            mock_sp.assert_called_once_with(
                ["git", "clone", "https://github.com/openstack/tempest",
                 "foo-baserepo"])

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.base_repo")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._initialize_testr")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._install_venv")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    @mock.patch("shutil.copytree")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._clone")
    @mock.patch("os.path.exists", return_value=False)
    def test_install_successful(self, mock_exists, mock_clone, mock_copytree,
                                mock_sp, mock_install_venv, mock_testr_init,
                                mock_base_repo):
        mock_base_repo.__get__ = mock.Mock(return_value="fake_dir")
        self.verifier.install()

        self.assertEqual([mock.call(self.verifier.path(".venv")),
                          mock.call(self.verifier.base_repo),
                          mock.call(self.verifier.path())],
                         mock_exists.call_args_list)
        mock_clone.assert_called_once_with()
        mock_copytree.assert_called_once_with(
            self.verifier.base_repo,
            self.verifier.path())
        mock_sp.assert_called_once_with(
            "git checkout master; git pull",
            cwd=self.verifier.path("tempest"),
            shell=True)
        mock_install_venv.assert_called_once_with()
        mock_testr_init.assert_called_once_with()

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.base_repo")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.uninstall")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._initialize_testr")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._install_venv")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess.check_call")
    @mock.patch("shutil.copytree")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._clone")
    @mock.patch("os.path.exists", return_value=False)
    def test_install_failed(self, mock_exists, mock_clone, mock_copytree,
                            mock_sp, mock_install_venv, mock_testr_init,
                            mock_uninstall, mock_base_repo):
        mock_base_repo.__get__ = mock.Mock(return_value="fake_dir")
        mock_sp.side_effect = subprocess.CalledProcessError(0, None)

        self.assertRaises(tempest.TempestSetupFailure, self.verifier.install)

        self.assertEqual([mock.call(self.verifier.path(".venv")),
                          mock.call(self.verifier.base_repo),
                          mock.call(self.verifier.path())],
                         mock_exists.call_args_list)
        mock_clone.assert_called_once_with()
        mock_copytree.assert_called_once_with(
            self.verifier.base_repo,
            self.verifier.path())
        mock_sp.assert_called_once_with(
            "git checkout master; git pull",
            cwd=self.verifier.path("tempest"),
            shell=True)
        self.assertFalse(mock_install_venv.called)
        self.assertFalse(mock_testr_init.called)
        mock_uninstall.assert_called_once_with()

    @mock.patch("shutil.rmtree")
    @mock.patch("os.path.exists", return_value=True)
    def test_uninstall(self, mock_exists, mock_shutil):
        self.verifier.uninstall()
        mock_exists.assert_called_once_with(self.verifier.path())
        mock_shutil.assert_called_once_with(self.verifier.path())

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest._is_git_repo",
                return_value=True)
    @mock.patch("rally.common.utils.generate_random_name",
                return_value="fake_tempest_dir")
    @mock.patch("os.listdir", return_value=["fake_dir"])
    @mock.patch("shutil.move")
    @mock.patch("os.path.exists", return_value=True)
    def test_upgrade_repo_tree(self, mock_exists, mock_move, mock_listdir,
                               mock_rand, mock_isgitrepo):
        with self.base_repo_dir_patcher as foo_base:
            self.verifier._base_repo = "fake_base"
            self.verifier.base_repo
            subdir = mock_rand.return_value
            mock_listdir.assert_called_once_with(foo_base)
            fake_dir = mock_listdir.return_value[0]
            dest = os.path.join(self.base_repo_dir_patcher.new, subdir,
                                fake_dir)
            mock_move.assert_called_once_with(fake_dir, dest)


class TempestVerifyTestCase(BaseTestCase):
    def _get_fake_call(self, testr_arg):
        return (
            "%(venv)s testr run --parallel --subunit tempest.api.%(testr_arg)s"
            " | tee %(tempest_path)s/subunit.stream"
            " | %(venv)s subunit-2to1"
            " | %(venv)s %(tempest_path)s/tools/colorizer.py" % {
                "venv": self.verifier.venv_wrapper,
                "testr_arg": testr_arg,
                "tempest_path": self.verifier.path()})

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=(None, None))
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestConf")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.is_configured",
                return_value=False)
    def test_verify_not_configured(self, mock_is_configured, mock_conf,
                                   mock_sp, mock_env, mock_parse_results):
        set_name = "compute"
        fake_call = self._get_fake_call(set_name)

        self.verifier.verify(set_name, None)

        self.assertEqual(2, mock_is_configured.call_count)
        mock_conf.assert_called_once_with(self.verifier.deployment)
        mock_conf().generate.assert_called_once_with(self.verifier.config_file)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_sp.check_call.assert_called_once_with(
            fake_call, env=mock_env, cwd=self.verifier.path(),
            shell=True)
        mock_parse_results.assert_called_once_with()

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=(None, None))
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestConf")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.is_configured",
                return_value=True)
    def test_verify_when_tempest_configured(self, mock_is_configured,
                                            mock_conf, mock_sp, mock_env,
                                            mock_parse_results):
        set_name = "identity"
        fake_call = self._get_fake_call(set_name)

        self.verifier.verify(set_name, None)

        mock_is_configured.assert_called_once_with()
        self.assertFalse(mock_conf.called)
        self.assertFalse(mock_conf().generate.called)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_sp.check_call.assert_called_once_with(
            fake_call, env=mock_env, cwd=self.verifier.path(),
            shell=True)
        mock_parse_results.assert_called_once_with()

    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.parse_results",
                return_value=(None, None))
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.env")
    @mock.patch(TEMPEST_PATH + ".tempest.subprocess")
    @mock.patch(TEMPEST_PATH + ".config.TempestConf")
    @mock.patch(TEMPEST_PATH + ".tempest.Tempest.is_configured",
                return_value=True)
    def test_verify_failed_and_tempest_is_configured(
            self, mock_is_configured, mock_conf, mock_sp, mock_env,
            mock_parse_results):
        set_name = "identity"
        fake_call = self._get_fake_call(set_name)
        mock_sp.side_effect = subprocess.CalledProcessError

        self.verifier.verify(set_name, None)

        mock_is_configured.assert_called_once_with()
        self.assertFalse(mock_conf.called)
        self.assertFalse(mock_conf().generate.called)
        self.verifier.verification.start_verifying.assert_called_once_with(
            set_name)

        mock_sp.check_call.assert_called_once_with(
            fake_call, env=mock_env, cwd=self.verifier.path(),
            shell=True)
        self.assertTrue(mock_parse_results.called)
        self.verifier.verification.set_failed.assert_called_once_with()
