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

from rally.benchmark.scenarios import base
from rally.benchmark import validation as valid
from rally import consts


class TempestScenario(base.Scenario):

    @valid.add_validator(valid.tempest_tests_exists())
    @base.scenario(context={"tempest": {}})
    def single_test(self, test_name):
        """Launch a single test

        :param test_name: name of tempest scenario for launching
        """
        if (not test_name.startswith("tempest.api.")
                and test_name.split('.')[0] in consts.TEMPEST_TEST_SETS):
            test_name = "tempest.api." + test_name

        self.context()["verifier"].run(test_name)
