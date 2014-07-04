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

import mock

from rally.benchmark.context import tempest
from rally import exceptions
from tests import test


CONTEXT = "rally.benchmark.context.tempest"
TEMPEST = "rally.verification.verifiers.tempest.tempest"


class TempestContextTestCase(test.TestCase):

    def setUp(self):
        super(TempestContextTestCase, self).setUp()
        task = mock.MagicMock()
        task.task.deployment_uuid.return_value = "fake_uuid"
        self.context = {"task": task}

    @mock.patch(CONTEXT + ".os.mkdir")
    @mock.patch(TEMPEST + ".Tempest.generate_config_file")
    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.install")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    def test_setup(self, mock_is_install, mock_install, mock_is_cfg, mock_cfg,
                   mock_mkdir):
        mock_is_install.return_value = True
        mock_is_cfg.return_value = False

        benchmark = tempest.Tempest(self.context)

        benchmark.setup()

        self.assertEqual(0, mock_install.call_count)
        self.assertEqual(1, mock_cfg.call_count)
        self.assertEqual('/dev/null', benchmark.verifier.log_file_raw)

    @mock.patch(CONTEXT + ".os.mkdir")
    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    @mock.patch(TEMPEST + ".Tempest.install")
    def test_setup_failure_on_tempest_installation(
            self, mock_install, mock_is_installed, mock_is_cfg, mock_mkdir):
        mock_is_installed.return_value = False
        mock_install.side_effect = exceptions.TempestSetupFailure()

        benchmark = tempest.Tempest(self.context)

        self.assertRaises(exceptions.BenchmarkSetupFailure, benchmark.setup)
        self.assertEqual(0, mock_is_cfg.call_count)

    @mock.patch(CONTEXT + ".os.path.exists")
    @mock.patch(CONTEXT + ".shutil")
    @mock.patch(CONTEXT + ".subprocess")
    def test_cleanup(self, mock_sp, mock_shutil, mock_os_path_exists):
        benchmark = tempest.Tempest(self.context)
        benchmark.verifier = mock.MagicMock()
        benchmark.results_dir = "/tmp/path"
        mock_os_path_exists.return_value = True

        benchmark.cleanup()

        mock_sp.check_call.assert_called_once_with(
            "cd %s && %s python tempest/stress/tools/cleanup.py" %
            (benchmark.verifier.tempest_path, benchmark.verifier.venv_wrapper),
            shell=True, cwd=benchmark.verifier.tempest_path,
            env=benchmark.verifier.env)
        mock_shutil.rmtree.assert_called_once_with("/tmp/path")
