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
import sys

import mock

from rally import exceptions
from rally.verification import manager
from tests.unit import test


DEFAULT_REPO = "git.example.com"
DEFAULT_VERSION = 3.14159


@manager.configure("some_fake_verifier", default_repo=DEFAULT_REPO,
                   default_version=DEFAULT_VERSION)
class FakeVerifier(manager.VerifierManager):

    @classmethod
    def _get_default_meta(cls):
        return {"fake_key1": "fake_value"}

    def run(self, verification, pattern=None, load_list=None, skip_list=None,
            xfail_list=None, concurrency=None, failed=False, extra_args=None):
        pass

    def list_tests(self, pattern=""):
        pass


class VerifierManagerTestCase(test.TestCase):
    def setUp(self):
        super(VerifierManagerTestCase, self).setUp()
        check_output_p = mock.patch("rally.verification.manager.utils."
                                    "check_output")
        self.check_output = check_output_p.start()
        self.addCleanup(check_output_p.stop)

    @mock.patch.dict(os.environ, values={"PATH": ""}, clear=True)
    def test_environ(self):
        verifier = mock.Mock(system_wide=False)
        vmanager = FakeVerifier(verifier)

        self.assertEqual({"PATH": "%s/bin:" % vmanager.venv_dir,
                          "VIRTUAL_ENV": vmanager.venv_dir},
                         vmanager.environ)

        verifier.system_wide = True
        self.assertEqual({"PATH": ""}, vmanager.environ)

    @mock.patch("rally.verification.manager.VerifierManager.validate_args")
    @mock.patch("rally.verification.context.ContextManager.validate")
    def test_validate(self, mock_context_manager_validate, mock_validate_args):
        fvmanager = FakeVerifier(mock.Mock())
        args = mock.Mock()
        with mock.patch.object(FakeVerifier, "_meta_get") as mock__meta_get:
            fvmanager.validate(args)
            mock__meta_get.assert_called_once_with("context")
            mock_validate_args.assert_called_once_with(args)
            mock_context_manager_validate.assert_called_once_with(
                mock__meta_get.return_value)

    def test__clone(self):
        verifier = mock.Mock(source=None)
        vmanager = FakeVerifier(verifier)
        verifier.version = None

        vmanager._clone()
        self.assertEqual(
            [mock.call(["git", "clone", DEFAULT_REPO, vmanager.repo_dir]),
             mock.call(["git", "checkout", DEFAULT_VERSION],
                       cwd=vmanager.repo_dir)],
            self.check_output.call_args_list)

        self.check_output.reset_mock()
        verifier.version = "master"

        verifier.source = "some_source"

        vmanager._clone()
        self.check_output.assert_called_once_with(
            ["git", "clone", verifier.source, vmanager.repo_dir])

    @mock.patch("rally.verification.utils.create_dir")
    def test_install(self, mock_create_dir):
        verifier = mock.Mock()
        vmanager = FakeVerifier(verifier)
        vmanager._clone = mock.Mock()
        vmanager.check_system_wide = mock.Mock()
        vmanager.install_venv = mock.Mock()

        # venv case
        verifier.system_wide = False

        vmanager.install()

        vmanager._clone.assert_called_once_with()
        self.assertFalse(vmanager.check_system_wide.called)
        vmanager.install_venv.assert_called_once_with()

        # system-wide case
        vmanager._clone.reset_mock()
        vmanager.check_system_wide.reset_mock()
        vmanager.install_venv.reset_mock()
        verifier.system_wide = True

        vmanager.install()

        vmanager._clone.assert_called_once_with()
        vmanager.check_system_wide.assert_called_once_with()
        self.assertFalse(vmanager.install_venv.called)

    @mock.patch("rally.verification.manager.shutil.rmtree")
    @mock.patch("rally.verification.manager.os.path.exists", return_value=True)
    def test_uninstall(self, mock_exists, mock_rmtree):
        vmanager = FakeVerifier(mock.MagicMock())

        vmanager.uninstall()
        mock_exists.assert_called_once_with(vmanager.home_dir)
        mock_rmtree.assert_called_once_with(vmanager.home_dir)

        mock_exists.reset_mock()
        mock_rmtree.reset_mock()

        vmanager.uninstall(full=True)
        mock_exists.assert_called_once_with(vmanager.base_dir)
        mock_rmtree.assert_called_once_with(vmanager.base_dir)

    @mock.patch("rally.verification.manager.shutil.rmtree")
    @mock.patch("rally.verification.manager.os.path.exists")
    def test_install_venv(self, mock_exists, mock_rmtree):
        mock_exists.return_value = False
        vmanager = FakeVerifier(mock.Mock())

        vmanager.install_venv()
        self.assertEqual(
            [mock.call(["virtualenv", "-p", sys.executable, vmanager.venv_dir],
                       cwd=vmanager.repo_dir,
                       msg_on_err="Failed to initialize virtual env in %s "
                                  "directory." % vmanager.venv_dir),
             mock.call(["pip", "install", "-e", "./"],
                       cwd=vmanager.repo_dir, env=vmanager.environ)
             ],
            self.check_output.call_args_list)
        self.assertFalse(mock_rmtree.called)

        # case: venv was created previously
        mock_exists.return_value = True
        self.check_output.reset_mock()

        vmanager.install_venv()

        self.assertEqual(
            [mock.call(["virtualenv", "-p", sys.executable, vmanager.venv_dir],
                       cwd=vmanager.repo_dir,
                       msg_on_err="Failed to initialize virtual env in %s "
                                  "directory." % vmanager.venv_dir),
             mock.call(["pip", "install", "-e", "./"],
                       cwd=vmanager.repo_dir, env=vmanager.environ)
             ],
            self.check_output.call_args_list)
        mock_rmtree.assert_called_once_with(vmanager.venv_dir)

    def test_check_system_wide(self):
        vmanager = FakeVerifier(mock.Mock())
        pip_module = mock.Mock()
        pip_module_gid = pip_module.get_installed_distributions

        packages = []
        for name in ("SQLAlchemy", "NumPy"):
            packages.append(mock.Mock())
            packages[-1].name = name
        pip_module.req.parse_requirements.return_value = packages

        with mock.patch.dict("sys.modules", {"pip": pip_module}):
            pip_module_gid.return_value = [mock.Mock(key="sqlalchemy"),
                                           mock.Mock(key="numpy")]

            vmanager.check_system_wide()
            pip_module.req.parse_requirements.assert_called_once_with(
                "%s/requirements.txt" % vmanager.repo_dir, session=False)
            pip_module_gid.assert_called_once_with()

            # failure
            pip_module_gid.reset_mock()
            missed_package = pip_module_gid.return_value.pop()
            e = self.assertRaises(manager.VerifierSetupFailure,
                                  vmanager.check_system_wide)
            self.assertIn("Please install '%s'." % missed_package.key,
                          "%s" % e)

    def test_checkout(self):
        vmanager = FakeVerifier(mock.Mock())
        version = "3.14159"

        vmanager.checkout(version)

        self.assertEqual(
            [mock.call(["git", "checkout", "master"], cwd=vmanager.repo_dir),
             mock.call(["git", "remote", "update"], cwd=vmanager.repo_dir),
             mock.call(["git", "pull"], cwd=vmanager.repo_dir),
             mock.call(["git", "checkout", version], cwd=vmanager.repo_dir)],
            self.check_output.call_args_list)

    def test_configure(self):
        vmanager = FakeVerifier(mock.Mock())
        vmanager.configure()
        self.assertRaises(NotImplementedError, vmanager.configure,
                          extra_options={"key": "value"})

    def test_override_configuration(self):
        # coverage should be 100%...
        self.assertRaises(NotImplementedError,
                          FakeVerifier(mock.Mock()).override_configuration,
                          "something")

    def test_extend_configuration(self):
        # coverage should be 100%...
        self.assertRaises(NotImplementedError,
                          FakeVerifier(mock.Mock()).extend_configuration,
                          "something")

    def test_get_configuration(self):
        self.assertEqual("", FakeVerifier(mock.Mock()).get_configuration())

    def test_install_extension(self):
        # coverage should be 100%...
        self.assertRaises(NotImplementedError,
                          FakeVerifier(mock.Mock()).install_extension,
                          "source")

    def test_list_extensions(self):
        self.assertEqual([], FakeVerifier(mock.Mock()).list_extensions())

    def test_uninstall_extension(self):
        # coverage should be 100%...
        self.assertRaises(NotImplementedError,
                          FakeVerifier(mock.Mock()).uninstall_extension,
                          "name")

    @mock.patch("rally.verification.manager.six.StringIO")
    @mock.patch("rally.verification.manager.subunit_v2")
    def test_parse_results(self, mock_subunit_v2, mock_string_io):
        data = "123123"
        self.assertEqual(mock_subunit_v2.parse.return_value,
                         FakeVerifier(mock.Mock()).parse_results(data))
        mock_subunit_v2.parse.assert_called_once_with(
            mock_string_io.return_value)
        mock_string_io.assert_called_once_with(data)

    def test_validate_args(self):
        # validating "pattern" argument
        fvmanager = FakeVerifier(mock.Mock())
        fvmanager.validate_args({"pattern": "it is string"})
        e = self.assertRaises(exceptions.ValidationError,
                              fvmanager.validate_args, {"pattern": 2})
        self.assertEqual("'pattern' argument should be a string.",
                         e.kwargs["message"])

        # validating "concurrency" argument
        fvmanager.validate_args({"concurrency": 1})
        fvmanager.validate_args({"concurrency": 5})
        fvmanager.validate_args({"concurrency": 0})
        e = self.assertRaises(exceptions.ValidationError,
                              fvmanager.validate_args, {"concurrency": -1})
        self.assertEqual("'concurrency' argument should be a positive integer "
                         "or zero.", e.kwargs["message"])
        e = self.assertRaises(exceptions.ValidationError,
                              fvmanager.validate_args, {"concurrency": "bla"})
        self.assertEqual("'concurrency' argument should be a positive integer "
                         "or zero.", e.kwargs["message"])

        # validating "load_list" argument
        fvmanager.validate_args({"load_list": []})
        e = self.assertRaises(exceptions.ValidationError,
                              fvmanager.validate_args, {"load_list": "str"})
        self.assertEqual("'load_list' argument should be a list of tests.",
                         e.kwargs["message"])

        # validating "skip_list" argument
        fvmanager.validate_args({"skip_list": {}})
        e = self.assertRaises(exceptions.ValidationError,
                              fvmanager.validate_args, {"skip_list": "str"})
        self.assertEqual("'skip_list' argument should be a dict of tests where"
                         " keys are test names and values are reasons.",
                         e.kwargs["message"])

        # validating "xfail_list" argument
        fvmanager.validate_args({"xfail_list": {}})
        e = self.assertRaises(exceptions.ValidationError,
                              fvmanager.validate_args,
                              {"xfail_list": "str"})
        self.assertEqual("'xfail_list' argument should be a dict of tests "
                         "where keys are test names and values are reasons.",
                         e.kwargs["message"])
