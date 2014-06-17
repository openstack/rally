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

from rally.benchmark.scenarios.tempest import tempest
from rally.verification.verifiers.tempest import tempest as verifier
from tests import test

VERIFIER = "rally.verification.verifiers.tempest.tempest"
TS = "rally.benchmark.scenarios.tempest"


class TempestScenarioTestCase(test.TestCase):

    def setUp(self):
        super(TempestScenarioTestCase, self).setUp()
        self.verifier = verifier.Tempest("fake_uuid")
        self.verifier.log_file_raw = "/dev/null"
        self.verifier.parse_results = mock.MagicMock()
        self.verifier.parse_results.return_value = ({"fake": True},
                                                    {"have_results": True})
        self.context = {"verifier": self.verifier,
                        "tmp_results_dir": "/dev"}
        self.scenario = tempest.TempestScenario(self.context)
        self.scenario._add_atomic_actions = mock.MagicMock()

    def get_tests_launcher_cmd(self, tests):
        return ("%(venv)s testr run --parallel --subunit %(tests)s "
                "| tee /dev/null "
                "| %(venv)s subunit-2to1 "
                "| %(venv)s %(tempest_path)s/tools/colorizer.py" %
                {
                    "venv": self.verifier.venv_wrapper,
                    "tempest_path": self.verifier.tempest_path,
                    "tests": " ".join(tests)
                })

    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    def test_single_test(self, mock_sp, mock_tmp):
        mock_tmp.NamedTemporaryFile().name = "/dev/null"
        fake_test = "tempest.api.fake.test"

        self.scenario.single_test(test_name=fake_test)

        expected_call = self.get_tests_launcher_cmd([fake_test])
        mock_sp.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.tempest_path,
            env=self.verifier.env, shell=True)

    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    def test_all(self, mock_sp, mock_tmp):
        mock_tmp.NamedTemporaryFile().name = "/dev/null"

        self.scenario.all()

        expected_call = self.get_tests_launcher_cmd([])
        mock_sp.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.tempest_path,
            env=self.verifier.env, shell=True)

    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    def test_set(self, mock_sp, mock_tmp):
        mock_tmp.NamedTemporaryFile().name = "/dev/null"

        self.scenario.set("smoke")

        expected_call = self.get_tests_launcher_cmd(["smoke"])
        mock_sp.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.tempest_path,
            env=self.verifier.env, shell=True)

    @mock.patch(TS + ".utils.tempfile")
    @mock.patch(VERIFIER + ".subprocess")
    def test_list_of_tests(self, mock_sp, mock_tmp):
        mock_tmp.NamedTemporaryFile().name = "/dev/null"
        fake_tests = ["tempest.fake.test1", "tempest.fake.test2"]

        self.scenario.list_of_tests(fake_tests)

        expected_call = self.get_tests_launcher_cmd(fake_tests)
        mock_sp.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.tempest_path,
            env=self.verifier.env, shell=True)
