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

import os
import subprocess

import mock

from rally import exceptions
from rally.plugins.common.verification import testr
from tests.unit import test


PATH = "rally.plugins.common.verification.testr"


class TestrContextTestCase(test.TestCase):

    def setUp(self):
        super(TestrContextTestCase, self).setUp()
        self.verifier = mock.Mock()
        self.prepare_run_args = self.verifier.manager.prepare_run_args
        self.prepare_run_args.side_effect = lambda x: x

    def assertEqualCmd(self, expected, actual, msg=""):
        cmd = ["testr", "run", "--subunit"]
        cmd.extend(expected)
        self.assertEqual(cmd, actual, message=msg)

    def test_setup_with_concurrency(self):
        # default behaviour
        cfg = {"verifier": self.verifier}
        ctx = testr.TestrContext(cfg)
        ctx.setup()
        self.assertEqualCmd(["--parallel"], cfg["testr_cmd"])
        cfg = {"verifier": self.verifier, "run_args": {"concurrency": 0}}
        ctx = testr.TestrContext(cfg)
        ctx.setup()
        self.assertEqualCmd(["--parallel"], cfg["testr_cmd"])

        # serial mode
        cfg = {"verifier": self.verifier,
               "run_args": {"concurrency": 1}}
        ctx = testr.TestrContext(cfg)
        ctx.setup()
        self.assertEqualCmd(["--concurrency", "1"], cfg["testr_cmd"])

        # parallel mode
        cfg = {"verifier": self.verifier,
               "run_args": {"concurrency": 2}}
        ctx = testr.TestrContext(cfg)
        ctx.setup()
        self.assertEqualCmd(["--parallel", "--concurrency", "2"],
                            cfg["testr_cmd"])

    @mock.patch("%s.common_utils.generate_random_path" % PATH)
    def test_setup_with_skip_and_load_lists(self, mock_generate_random_path):
        # with load_list, but without skip_list
        load_list = ["tests.foo", "tests.bar"]
        cfg = {"verifier": self.verifier,
               "run_args": {"load_list": load_list}}
        ctx = testr.TestrContext(cfg)
        mock_open = mock.mock_open()
        with mock.patch("%s.open" % PATH, mock_open):
            ctx.setup()
        mock_open.assert_called_once_with(
            mock_generate_random_path.return_value, "w")
        handle = mock_open.return_value
        handle.write.assert_called_once_with("\n".join(load_list))
        self.assertEqualCmd(["--parallel", "--load-list",
                             mock_generate_random_path.return_value],
                            cfg["testr_cmd"])
        self.assertFalse(self.verifier.manager.list_tests.called)

        # with load_list and skip_list
        load_list = ["tests.foo", "tests.bar"]
        skip_list = ["tests.foo"]
        cfg = {"verifier": self.verifier,
               "run_args": {"load_list": load_list,
                            "skip_list": skip_list}}
        ctx = testr.TestrContext(cfg)
        mock_open = mock.mock_open()
        with mock.patch("%s.open" % PATH, mock_open):
            ctx.setup()
        mock_open.assert_called_once_with(
            mock_generate_random_path.return_value, "w")
        handle = mock_open.return_value
        handle.write.assert_called_once_with(load_list[1])
        self.assertEqualCmd(["--parallel", "--load-list",
                             mock_generate_random_path.return_value],
                            cfg["testr_cmd"])
        self.assertFalse(self.verifier.manager.list_tests.called)

        # with skip_list, but without load_list
        load_list = ["tests.foo", "tests.bar"]
        self.verifier.manager.list_tests.return_value = load_list
        skip_list = ["tests.foo"]
        cfg = {"verifier": self.verifier,
               "run_args": {"skip_list": skip_list}}
        ctx = testr.TestrContext(cfg)
        mock_open = mock.mock_open()
        with mock.patch("%s.open" % PATH, mock_open):
            ctx.setup()
        mock_open.assert_called_once_with(
            mock_generate_random_path.return_value, "w")
        handle = mock_open.return_value
        handle.write.assert_called_once_with(load_list[1])
        self.assertEqualCmd(["--parallel", "--load-list",
                             mock_generate_random_path.return_value],
                            cfg["testr_cmd"])
        self.verifier.manager.list_tests.assert_called_once_with()

    def test_setup_with_failing(self):
        cfg = {"verifier": self.verifier, "run_args": {"failed": True}}
        ctx = testr.TestrContext(cfg)
        ctx.setup()
        self.assertEqualCmd(["--parallel", "--failing"], cfg["testr_cmd"])

    def test_setup_with_pattern(self):
        cfg = {"verifier": self.verifier, "run_args": {"pattern": "foo"}}
        ctx = testr.TestrContext(cfg)
        ctx.setup()
        self.assertEqualCmd(["--parallel", "foo"], cfg["testr_cmd"])

    @mock.patch("%s.os.remove" % PATH)
    @mock.patch("%s.os.path.exists" % PATH)
    def test_cleanup(self, mock_exists, mock_remove):
        files = {"/path/foo_1": True,
                 "/path/bar_1": False,
                 "/path/foo_2": False,
                 "/path/bar_2": True}

        def fake_exists(path):
            return files.get(path, False)

        mock_exists.side_effect = fake_exists

        ctx = testr.TestrContext({"verifier": self.verifier})
        ctx._tmp_files = files.keys()

        ctx.cleanup()

        self.assertEqual([mock.call(f) for f in files.keys()],
                         mock_exists.call_args_list)
        self.assertEqual([mock.call(f) for f in files.keys() if files[f]],
                         mock_remove.call_args_list)


class TestrLauncherTestCase(test.TestCase):
    def test_run_environ_property(self):
        env = mock.Mock()

        class FakeLauncher(testr.TestrLauncher):
            @property
            def environ(self):
                return env

        self.assertEqual(env, FakeLauncher(mock.Mock()).run_environ)

    @mock.patch("%s.utils.check_output" % PATH)
    def test_list_tests(self, mock_check_output):
        mock_check_output.return_value = (
            "logging message\n"  # should be ignored
            "one more useless data\n"  # should be ignored
            "tests.FooTestCase.test_something\n"  # valid
            "tests.FooTestCase.test_another[\n"  # invalid
            "tests.BarTestCase.test_another[id=123]\n"  # valid
            "tests.FooTestCase.test_another[id=a2-213,smoke]\n"  # valid
        )
        verifier = mock.Mock()

        launcher = testr.TestrLauncher(verifier)

        self.assertEqual(["tests.FooTestCase.test_something",
                          "tests.BarTestCase.test_another[id=123]",
                          "tests.FooTestCase.test_another[id=a2-213,smoke]"],
                         launcher.list_tests())

        mock_check_output.assert_called_once_with(
            ["testr", "list-tests", ""],
            cwd=launcher.repo_dir, env=launcher.environ, debug_output=False)

    @mock.patch("%s.shutil.rmtree" % PATH)
    @mock.patch("%s.utils.check_output" % PATH)
    @mock.patch("%s.os.path.exists" % PATH)
    @mock.patch("%s.os.path.isdir" % PATH)
    def test__init_testr(self, mock_isdir, mock_exists, mock_check_output,
                         mock_rmtree):
        launcher = testr.TestrLauncher(mock.Mock())

        # case #1: testr already initialized
        mock_isdir.return_value = True

        launcher._init_testr()

        self.assertFalse(mock_check_output.called)
        self.assertFalse(mock_exists.called)
        self.assertFalse(mock_rmtree.called)

        # case #2: initializing testr without errors
        mock_isdir.return_value = False

        launcher._init_testr()

        mock_check_output.assert_called_once_with(
            ["testr", "init"], cwd=launcher.repo_dir, env=launcher.environ)
        self.assertFalse(mock_exists.called)
        self.assertFalse(mock_rmtree.called)
        mock_check_output.reset_mock()

        # case #3: initializing testr with error
        mock_check_output.side_effect = OSError
        test_repository_dir = os.path.join(launcher.base_dir,
                                           ".testrepository")

        self.assertRaises(exceptions.RallyException, launcher._init_testr)

        mock_check_output.assert_called_once_with(
            ["testr", "init"], cwd=launcher.repo_dir, env=launcher.environ)
        mock_exists.assert_called_once_with(test_repository_dir)
        mock_rmtree.assert_called_once_with(test_repository_dir)

    @mock.patch("%s.subunit_v2.parse" % PATH)
    @mock.patch("%s.subprocess.Popen" % PATH)
    def test_run(self, mock_popen, mock_parse):
        launcher = testr.TestrLauncher(mock.Mock())
        ctx = {"testr_cmd": ["ls", "-la"],
               "run_args": {"xfail_list": mock.Mock(),
                            "skip_list": mock.Mock()}}

        self.assertEqual(mock_parse.return_value, launcher.run(ctx))

        mock_popen.assert_called_once_with(ctx["testr_cmd"],
                                           env=launcher.run_environ,
                                           cwd=launcher.repo_dir,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT)
        mock_popen.return_value.wait.assert_called_once_with()
        mock_parse.assert_called_once_with(
            mock_popen.return_value.stdout, live=True,
            expected_failures=ctx["run_args"]["xfail_list"],
            skipped_tests=ctx["run_args"]["skip_list"],
            logger_name=launcher.verifier.name)

    @mock.patch("%s.manager.VerifierManager.install" % PATH)
    def test_install(self, mock_verifier_manager_install):
        launcher = testr.TestrLauncher(mock.Mock())
        launcher._init_testr = mock.Mock()

        launcher.install()

        mock_verifier_manager_install.assert_called_once_with()
        launcher._init_testr.assert_called_once_with()
