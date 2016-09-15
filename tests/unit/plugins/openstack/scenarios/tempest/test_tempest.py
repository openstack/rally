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

from rally.plugins.openstack.scenarios.tempest import tempest
from rally.verification.tempest import tempest as verifier
from tests.unit import test

TEMPEST_DIR = "rally.verification.tempest"
VERIFIER = TEMPEST_DIR + ".tempest"
TS = "rally.plugins.openstack.scenarios.tempest"


class TempestScenarioTestCase(test.TestCase):

    def setUp(self):
        super(TempestScenarioTestCase, self).setUp()
        self.verifier = verifier.Tempest("fake_uuid")
        self.verifier.log_file_raw = "/dev/null"
        self.verifier.parse_results = mock.MagicMock()
        self.verifier.parse_results.return_value = mock.MagicMock(
            tests={}, total={"time": 0})
        self.context = test.get_test_context()
        self.context.update({"verifier": self.verifier,
                             "tmp_results_dir": "/dev"})

    def get_tests_launcher_cmd(self, tests):
        return ("%(venv)s testr run --subunit --parallel --concurrency 0 "
                "%(tests)s "
                "| tee /dev/null "
                "| %(venv)s subunit-trace -f -n" %
                {
                    "venv": self.verifier.venv_wrapper,
                    "tests": " ".join(tests)
                })

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_single_test(self, mock_tempest_resources_context,
                         mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.SingleTest(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"
        fake_test = "tempest.api.fake.test"

        scenario.run(test_name=fake_test)

        expected_call = self.get_tests_launcher_cmd([fake_test])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_single_test_negative(self, mock_tempest_resources_context,
                                  mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.SingleTest(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"
        fake_test = "tempest.api.network"

        scenario.run(test_name=fake_test)

        expected_call = self.get_tests_launcher_cmd([fake_test])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_single_test_without_prefix(self, mock_tempest_resources_context,
                                        mock_subprocess, mock_tempfile,
                                        mock_isfile):
        scenario = tempest.SingleTest(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"

        scenario.run("network")

        expected_call = self.get_tests_launcher_cmd(["tempest.api.network"])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_all(self, mock_tempest_resources_context,
                 mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.All(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"

        scenario.run()

        expected_call = self.get_tests_launcher_cmd([])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_set_smoke(self, mock_tempest_resources_context,
                       mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.Set(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"

        scenario.run("smoke")

        expected_call = self.get_tests_launcher_cmd(["smoke"])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_set_full(self, mock_tempest_resources_context,
                      mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.Set(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"

        scenario.run("full")

        expected_call = self.get_tests_launcher_cmd([])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_set_from_list(self, mock_tempest_resources_context,
                           mock_tempfile, mock_isfile):
        scenario = tempest.Set(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"

        fake_scenarios = ["network", "volume", "baremetal",
                          "image", "identity", "compute", "database",
                          "data_processing", "object_storage",
                          "telemetry", "queuing", "orchestration"]
        for fake_scenario in fake_scenarios:
            with mock.patch(VERIFIER + ".subprocess") as mock_subprocess:
                scenario.run(fake_scenario)
                fake_test = "tempest.api." + fake_scenario

                expected_call = self.get_tests_launcher_cmd([fake_test])
                mock_subprocess.check_call.assert_called_once_with(
                    expected_call, cwd=self.verifier.path(),
                    env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_set_selective(self, mock_tempest_resources_context,
                           mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.Set(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"

        scenario.run("network")

        expected_call = self.get_tests_launcher_cmd(["tempest.api.network"])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_list_of_tests(self, mock_tempest_resources_context,
                           mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.ListOfTests(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"
        fake_tests = ["tempest.fake.test1", "tempest.fake.test2"]

        scenario.run(fake_tests)

        expected_call = self.get_tests_launcher_cmd(fake_tests)
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    @mock.patch(TEMPEST_DIR + ".config.TempestResourcesContext")
    def test_specific_regex(self, mock_tempest_resources_context,
                            mock_subprocess, mock_tempfile, mock_isfile):
        scenario = tempest.SpecificRegex(self.context)
        scenario._add_atomic_actions = mock.MagicMock()

        mock_tempfile.NamedTemporaryFile().name = "/dev/null"
        regex = "tempest.fake.test1"

        scenario.run(regex)

        expected_call = self.get_tests_launcher_cmd([regex])
        mock_subprocess.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.path(),
            env=self.verifier.env, shell=True)
