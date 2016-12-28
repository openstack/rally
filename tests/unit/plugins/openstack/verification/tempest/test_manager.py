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

import json
import os
import subprocess

import mock

from rally import exceptions
from rally.plugins.openstack.verification.tempest import manager
from tests.unit import test


PATH = "rally.plugins.openstack.verification.tempest.manager"


class TempestManagerTestCase(test.TestCase):
    def test_run_environ_property(self):
        mock.patch("%s.testr.TestrLauncher.run_environ" % PATH,
                   new={"some": "key"}).start()
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))
        env = {"some": "key",
               "OS_TEST_PATH": os.path.join(tempest.repo_dir,
                                            "tempest/test_discover"),
               "TEMPEST_CONFIG": "tempest.conf",
               "TEMPEST_CONFIG_DIR": os.path.dirname(tempest.configfile)}

        self.assertEqual(env, tempest.run_environ)

    def test_configfile_property(self):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))
        self.assertEqual(os.path.join(tempest.home_dir, "tempest.conf"),
                         tempest.configfile)

    @mock.patch("%s.config.read_configfile" % PATH)
    def test_get_configuration(self, mock_read_configfile):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))
        self.assertEqual(mock_read_configfile.return_value,
                         tempest.get_configuration())
        mock_read_configfile.assert_called_once_with(tempest.configfile)

    @mock.patch("%s.config.TempestConfigfileManager" % PATH)
    def test_configure(self, mock_tempest_configfile_manager):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))
        cm = mock_tempest_configfile_manager.return_value
        extra_options = mock.Mock()

        self.assertEqual(cm.create.return_value,
                         tempest.configure(extra_options))
        mock_tempest_configfile_manager.assert_called_once_with(
            tempest.verifier.deployment)
        cm.create.assert_called_once_with(tempest.configfile, extra_options)

    @mock.patch("%s.config.extend_configfile" % PATH)
    def test_extend_configuration(self, mock_extend_configfile):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))
        extra_options = mock.Mock()
        self.assertEqual(mock_extend_configfile.return_value,
                         tempest.extend_configuration(extra_options))
        mock_extend_configfile.assert_called_once_with(tempest.configfile,
                                                       extra_options)

    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    def test_override_configuration(self, mock_open):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))
        new_content = mock.Mock()

        tempest.override_configuration(new_content)

        mock_open.assert_called_once_with(tempest.configfile, "w")
        mock_open.side_effect().write.assert_called_once_with(new_content)

    @mock.patch("%s.os.path.exists" % PATH)
    @mock.patch("%s.utils.check_output" % PATH)
    @mock.patch("%s.TempestManager.check_system_wide" % PATH)
    def test_install_extension(self, mock_check_system_wide, mock_check_output,
                               mock_exists):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd",
                                                        system_wide=True))
        e = self.assertRaises(NotImplementedError, tempest.install_extension,
                              None, None, {"key": "value"})
        self.assertIn("verifiers don't support extra installation settings",
                      "%s" % e)

        test_reqs_path = os.path.join(tempest.base_dir, "extensions",
                                      "example", "test-requirements.txt")

        # case #1 system-wide installation
        source = "https://github.com/example/example"
        tempest.install_extension(source)

        path = os.path.join(tempest.base_dir, "extensions")
        mock_check_output.assert_called_once_with(
            ["pip", "install", "--no-deps", "--src", path, "-e",
             "git+https://github.com/example/example@master#egg=example"],
            cwd=tempest.base_dir, env=tempest.environ)
        mock_check_system_wide.assert_called_once_with(
            reqs_file_path=test_reqs_path)

        mock_check_output.reset_mock()

        # case #2 virtual env with specified version
        tempest.verifier.system_wide = False
        version = "some"
        tempest.install_extension(source, version=version)

        self.assertEqual([
            mock.call([
                "pip", "install", "--src", path, "-e",
                "git+https://github.com/example/example@some#egg=example"],
                cwd=tempest.base_dir, env=tempest.environ),
            mock.call(["pip", "install", "-r", test_reqs_path],
                      cwd=tempest.base_dir, env=tempest.environ)],
            mock_check_output.call_args_list)

    @mock.patch("%s.utils.check_output" % PATH)
    def test_list_extensions(self, mock_check_output):
        plugins_list = [
            {"name": "some", "entry_point": "foo.bar", "location": "/tmp"},
            {"name": "another", "entry_point": "bar.foo", "location": "/tmp"}
        ]
        mock_check_output.return_value = json.dumps(plugins_list)

        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))

        self.assertEqual(plugins_list, tempest.list_extensions())
        self.assertEqual(1, mock_check_output.call_count)
        mock_check_output.reset_mock()

        mock_check_output.side_effect = subprocess.CalledProcessError("", "")
        self.assertRaises(exceptions.RallyException, tempest.list_extensions)
        self.assertEqual(1, mock_check_output.call_count)

    @mock.patch("%s.TempestManager.list_extensions" % PATH)
    @mock.patch("%s.os.path.exists" % PATH)
    @mock.patch("%s.shutil.rmtree" % PATH)
    def test_uninstall_extension(self, mock_rmtree, mock_exists,
                                 mock_list_extensions):
        plugins_list = [
            {"name": "some", "entry_point": "foo.bar", "location": "/tmp"},
            {"name": "another", "entry_point": "bar.foo", "location": "/tmp"}
        ]
        mock_list_extensions.return_value = plugins_list

        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))

        tempest.uninstall_extension("some")
        mock_rmtree.assert_called_once_with(plugins_list[0]["location"])
        mock_list_extensions.assert_called_once_with()

        mock_rmtree.reset_mock()
        mock_list_extensions.reset_mock()

        self.assertRaises(exceptions.RallyException,
                          tempest.uninstall_extension, "unexist")

        mock_list_extensions.assert_called_once_with()
        self.assertFalse(mock_rmtree.called)

    @mock.patch("%s.TempestManager._transform_pattern" % PATH)
    @mock.patch("%s.testr.TestrLauncher.list_tests" % PATH)
    def test_list_tests(self, mock_testr_launcher_list_tests,
                        mock__transform_pattern):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))

        self.assertEqual(mock_testr_launcher_list_tests.return_value,
                         tempest.list_tests())
        mock_testr_launcher_list_tests.assert_called_once_with("")
        self.assertFalse(mock__transform_pattern.called)
        mock_testr_launcher_list_tests.reset_mock()

        pattern = mock.Mock()

        self.assertEqual(mock_testr_launcher_list_tests.return_value,
                         tempest.list_tests(pattern))
        mock_testr_launcher_list_tests.assert_called_once_with(
            mock__transform_pattern.return_value)
        mock__transform_pattern.assert_called_once_with(pattern)

    @mock.patch("%s.testr.TestrLauncher.validate_args" % PATH)
    def test_validate_args(self, mock_testr_launcher_validate_args):
        tm = manager.TempestManager(mock.Mock())
        tm.validate_args({})
        tm.validate_args({"pattern": "some.test"})
        tm.validate_args({"pattern": "set=smoke"})
        tm.validate_args({"pattern": "set=compute"})
        tm.validate_args({"pattern": "set=full"})

        e = self.assertRaises(exceptions.ValidationError, tm.validate_args,
                              {"pattern": "foo=bar"})
        self.assertEqual("Validation error: 'pattern' argument should be a "
                         "regexp or set name (format: 'tempest.api.identity."
                         "v3', 'set=smoke').", "%s" % e)

        e = self.assertRaises(exceptions.ValidationError, tm.validate_args,
                              {"pattern": "set=foo"})
        self.assertIn("Test set 'foo' not found in available Tempest test "
                      "sets. Available sets are ", "%s" % e)

    def test__transform_pattern(self):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))

        self.assertEqual("foo", tempest._transform_pattern("foo"))
        self.assertEqual("foo=bar", tempest._transform_pattern("foo=bar"))
        self.assertEqual("", tempest._transform_pattern("set=full"))
        self.assertEqual("smoke", tempest._transform_pattern("set=smoke"))
        self.assertEqual("tempest.bar", tempest._transform_pattern("set=bar"))
        self.assertEqual("tempest.api.compute",
                         tempest._transform_pattern("set=compute"))

    @mock.patch("%s.TempestManager._transform_pattern" % PATH)
    def test_prepare_run_args(self, mock__transform_pattern):
        tempest = manager.TempestManager(mock.MagicMock(uuid="uuuiiiddd"))

        self.assertEqual({}, tempest.prepare_run_args({}))
        self.assertFalse(mock__transform_pattern.called)

        self.assertEqual({"foo": "bar"},
                         tempest.prepare_run_args({"foo": "bar"}))
        self.assertFalse(mock__transform_pattern.called)

        pattern = mock.Mock()
        self.assertEqual({"pattern": mock__transform_pattern.return_value},
                         tempest.prepare_run_args({"pattern": pattern}))
        mock__transform_pattern.assert_called_once_with(pattern)
