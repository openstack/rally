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


class TempestScenarioTestCase(test.TestCase):

    def setUp(self):
        super(TempestScenarioTestCase, self).setUp()
        self.verifier = verifier.Tempest("fake_uuid")
        self.verifier.log_file = "/dev/null"
        self.context = {"verifier": self.verifier}
        self.scenario = tempest.TempestScenario(self.context)

    @mock.patch(VERIFIER + ".subprocess")
    def test_single_test(self, mock_sp):
        self.scenario.single_test("tempest.api.fake.test")
        expected_call = (
            "%(venv)s python -m subunit.run tempest.api.fake.test "
            "| %(venv)s subunit2junitxml --forward --output-to=/dev/null "
            "| %(venv)s subunit-2to1 "
            "| %(venv)s %(tempest_path)s/tools/colorizer.py" %
            {
                "venv": self.verifier.venv_wrapper,
                "tempest_path": self.verifier.tempest_path
            })
        mock_sp.check_call.assert_called_once_with(
            expected_call, cwd=self.verifier.tempest_path,
            env=self.verifier.env, shell=True)
