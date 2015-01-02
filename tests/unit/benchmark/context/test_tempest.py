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

import subprocess

import mock

from rally.benchmark.context import tempest
from rally import exceptions
from rally.verification.tempest import config
from rally.verification.tempest import tempest as tempest_verifier
from tests.unit import test


CONTEXT = "rally.benchmark.context.tempest"
TEMPEST = "rally.verification.tempest.tempest"


class TempestContextTestCase(test.TestCase):

    def setUp(self):
        super(TempestContextTestCase, self).setUp()
        task = mock.MagicMock()
        task.task.deployment_uuid.return_value = "fake_uuid"
        self.context = {"task": task}

    @mock.patch(CONTEXT + ".os.mkdir")
    @mock.patch(TEMPEST + ".Tempest.generate_config_file")
    @mock.patch(TEMPEST + ".Tempest.is_configured", return_value=True)
    @mock.patch(TEMPEST + ".Tempest.install")
    @mock.patch(TEMPEST + ".Tempest.is_installed", return_value=True)
    def test_setup(self, mock_is_install, mock_install, mock_is_cfg, mock_cfg,
                   mock_mkdir):
        benchmark = tempest.Tempest(self.context)

        benchmark.setup()

        self.assertEqual(0, mock_install.call_count)
        self.assertEqual(0, mock_cfg.call_count)
        self.assertEqual('/dev/null', benchmark.verifier.log_file_raw)

    @mock.patch(CONTEXT + ".os.mkdir")
    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed", return_value=False)
    @mock.patch(TEMPEST + ".Tempest.install")
    def test_setup_failure_on_tempest_installation(
            self, mock_install, mock_is_installed, mock_is_cfg, mock_mkdir):
        mock_install.side_effect = tempest_verifier.TempestSetupFailure()

        benchmark = tempest.Tempest(self.context)

        self.assertRaises(exceptions.BenchmarkSetupFailure, benchmark.setup)
        self.assertEqual(0, mock_is_cfg.call_count)

    @mock.patch(CONTEXT + ".os.mkdir")
    @mock.patch(TEMPEST + ".Tempest.is_configured", return_value=False)
    @mock.patch(TEMPEST + ".Tempest.is_installed", return_value=True)
    @mock.patch(TEMPEST + ".Tempest.generate_config_file")
    def test_setup_failure_on_tempest_configuration(
            self, mock_gen, mock_is_installed, mock_is_cfg, mock_mkdir):
        mock_gen.side_effect = config.TempestConfigCreationFailure()

        benchmark = tempest.Tempest(self.context)

        self.assertRaises(exceptions.BenchmarkSetupFailure, benchmark.setup)
        self.assertEqual(1, mock_is_cfg.call_count)

    @mock.patch(CONTEXT + ".os.mkdir")
    @mock.patch(TEMPEST + ".Tempest.is_configured", return_value=False)
    @mock.patch(TEMPEST + ".Tempest.is_installed", return_value=True)
    @mock.patch(TEMPEST + ".Tempest.generate_config_file")
    def test_setup_with_no_configuration(
            self, mock_gen, mock_is_installed, mock_is_cfg, mock_mkdir):

        benchmark = tempest.Tempest(self.context)
        benchmark.setup()
        self.assertEqual(1, mock_is_installed.call_count)
        self.assertEqual('/dev/null', benchmark.verifier.log_file_raw)
        self.assertEqual(1, mock_gen.call_count)

    @mock.patch(CONTEXT + ".os.path.exists", return_value=True)
    @mock.patch(CONTEXT + ".shutil")
    @mock.patch(CONTEXT + ".subprocess")
    def test_cleanup(self, mock_sp, mock_shutil, mock_os_path_exists):
        benchmark = tempest.Tempest(self.context)
        benchmark.verifier = mock.MagicMock()
        benchmark.results_dir = "/tmp/path"

        benchmark.cleanup()

        mock_sp.check_call.assert_called_once_with(
            "cd %s && %s python tempest/stress/tools/cleanup.py" %
            (benchmark.verifier.path, benchmark.verifier.venv_wrapper),
            shell=True, cwd=benchmark.verifier.path,
            env=benchmark.verifier.env)
        mock_shutil.rmtree.assert_called_once_with("/tmp/path")

    @mock.patch(CONTEXT + ".os.path.exists", return_value=False)
    @mock.patch(CONTEXT + ".shutil")
    @mock.patch(CONTEXT + ".subprocess")
    def test_cleanup_fail(self, mock_sp, mock_shutil, mock_os_path_exists):
        benchmark = tempest.Tempest(self.context)
        benchmark.verifier = mock.MagicMock()
        benchmark.results_dir = "/tmp/path"
        benchmark.cleanup()
        mock_sp.check_call.side_effect = subprocess.CalledProcessError(0, '')
        self.assertRaises(subprocess.CalledProcessError, benchmark.cleanup)
