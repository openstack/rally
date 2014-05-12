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
from rally.benchmark.scenarios.tempest import utils
from rally.benchmark import validation as valid
from rally import consts


class TempestScenario(base.Scenario):

    @valid.add_validator(valid.tempest_tests_exists())
    @base.scenario(context={"tempest": {}})
    @utils.tempest_log_wrapper
    def single_test(self, test_name, log_file):
        """Launch a single test

        :param test_name: name of tempest scenario for launching
        :param log_file: name of file for junitxml results
        """
        if (not test_name.startswith("tempest.api.")
                and test_name.split('.')[0] in consts.TEMPEST_TEST_SETS):
            test_name = "tempest.api." + test_name

        self.context()["verifier"].run(test_name, log_file)

    @base.scenario(context={"tempest": {}})
    @utils.tempest_log_wrapper
    def all(self, log_file):
        """Launch all discovered tests

        :param log_file: name of file for junitxml results
        """

        self.context()["verifier"].run("", log_file)

    @valid.add_validator(valid.tempest_set_exists())
    @base.scenario(context={"tempest": {}})
    @utils.tempest_log_wrapper
    def set(self, set_name, log_file):
        """Launch one by one methods from the set

        :param set_name: set name of tempest scenarios for launching
        :param log_file: name of file for junitxml results
        """

        if set_name == "full":
            testr_arg = ""
        elif set_name == "smoke":
            testr_arg = "smoke"
        else:
            testr_arg = "tempest.api.%s" % set_name

        self._context["verifier"].run(testr_arg, log_file)

    @valid.add_validator(valid.tempest_tests_exists())
    @base.scenario(context={"tempest": {}})
    @utils.tempest_log_wrapper
    def list_of_tests(self, test_names, log_file):
        """Launch all tests from given list

        :param test_names: list of tempest scenarios for launching
        :param log_file: name of file for junitxml results
        """

        self._context["verifier"].run(" ".join(test_names), log_file)

    @base.scenario(context={"tempest": {}})
    @utils.tempest_log_wrapper
    def specific_regex(self, regex, log_file):
        """Launch all tests which match given regex

        :param log_file: name of file for junitxml results
        """

        self._context["verifier"].run(regex, log_file)
