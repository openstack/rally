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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.tempest import utils
from rally.task import validation


"""Scenarios that launch Tempest tests."""


@validation.tempest_tests_exists()
@validation.required_openstack(admin=True)
@scenario.configure(context={"tempest": {}},
                    name="TempestScenario.single_test")
class SingleTest(scenario.OpenStackScenario):

    @utils.tempest_log_wrapper
    def run(self, test_name, log_file, tempest_conf=None):
        """Launch a single Tempest test by its name.

        :param test_name: name of tempest scenario for launching
        :param log_file: name of file for junitxml results
        :param tempest_conf: User specified tempest.conf location
        """
        if (not test_name.startswith("tempest.api.") and
                test_name.split(".")[0] in consts.TempestTestsAPI):
            test_name = "tempest.api." + test_name

        self.context["verifier"].run(test_name, log_file=log_file,
                                     tempest_conf=tempest_conf)


@validation.required_openstack(admin=True)
@scenario.configure(context={"tempest": {}},
                    name="TempestScenario.all")
class All(scenario.OpenStackScenario):

    @utils.tempest_log_wrapper
    def run(self, log_file, tempest_conf=None):
        """Launch all discovered Tempest tests by their names.

        :param log_file: name of file for junitxml results
        :param tempest_conf: User specified tempest.conf location
        """

        self.context["verifier"].run("", log_file=log_file,
                                     tempest_conf=tempest_conf)


@validation.tempest_set_exists()
@validation.required_openstack(admin=True)
@scenario.configure(context={"tempest": {}},
                    name="TempestScenario.set")
class Set(scenario.OpenStackScenario):

    @utils.tempest_log_wrapper
    def run(self, set_name, log_file, tempest_conf=None):
        """Launch all Tempest tests from a given set.

        :param set_name: set name of tempest scenarios for launching
        :param log_file: name of file for junitxml results
        :param tempest_conf: User specified tempest.conf location
        """

        if set_name == "full":
            testr_arg = ""
        elif set_name == "smoke":
            testr_arg = "smoke"
        else:
            testr_arg = "tempest.api.%s" % set_name

        self.context["verifier"].run(testr_arg, log_file=log_file,
                                     tempest_conf=tempest_conf)


@validation.tempest_tests_exists()
@validation.required_openstack(admin=True)
@scenario.configure(context={"tempest": {}},
                    name="TempestScenario.list_of_tests")
class ListOfTests(scenario.OpenStackScenario):

    @utils.tempest_log_wrapper
    def run(self, test_names, log_file, tempest_conf=None):
        """Launch all Tempest tests from a given list of their names.

        :param test_names: list of tempest scenarios for launching
        :param log_file: name of file for junitxml results
        :param tempest_conf: User specified tempest.conf location
        """

        self.context["verifier"].run(" ".join(test_names), log_file=log_file,
                                     tempest_conf=tempest_conf)


@validation.required_openstack(admin=True)
@scenario.configure(context={"tempest": {}},
                    name="TempestScenario.specific_regex")
class SpecificRegex(scenario.OpenStackScenario):

    @utils.tempest_log_wrapper
    def run(self, regex, log_file, tempest_conf=None):
        """Launch Tempest tests whose names match a given regular expression.

        :param regex: regexp to match Tempest test names against
        :param log_file: name of file for junitxml results
        :param tempest_conf: User specified tempest.conf location
        """

        self.context["verifier"].run(regex, log_file=log_file,
                                     tempest_conf=tempest_conf)