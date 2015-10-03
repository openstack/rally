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

""" Rally command: verify """

import csv
import json
import os

import six

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally.common import db
from rally.common import fileutils
from rally.common.i18n import _
from rally.common import objects
from rally import consts
from rally import exceptions
from rally.verification.tempest import diff
from rally.verification.tempest import json2html


class VerifyCommands(object):
    """Test cloud with Tempest

    Set of commands that allow you to perform Tempest tests of
    OpenStack live cloud.
    """

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @cliutils.args("--set", dest="set_name", type=str, required=False,
                   help="Name of tempest test set. Available sets: %s" % ", ".
                   join(list(consts.TempestTestsSets) +
                        list(consts.TempestTestsAPI)))
    @cliutils.args("--regex", dest="regex", type=str, required=False,
                   help="Regular expression of test.")
    @cliutils.args("--tempest-config", dest="tempest_config", type=str,
                   required=False,
                   help="User specified Tempest config file location")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don't set new task as default for future operations")
    @cliutils.args("--system-wide-install", dest="system_wide_install",
                   help="Use virtualenv else run tests in local environment",
                   required=False, action="store_true")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def start(self, set_name="", deployment=None, regex=None,
              tempest_config=None, do_use=True,
              system_wide_install=False):
        """Start set of tests.

        :param set_name: Name of tempest test set
        :param deployment: UUID or name of a deployment
        :param regex: Regular expression of test
        :param tempest_config: User specified Tempest config file location
        :param do_use: Use new task as default for future operations
        :param system_wide_install: Use virtualenv else run tests in
                                    local environment
        """

        if regex and set_name:
            raise exceptions.InvalidArgumentsException("set_name and regex "
                                                       "are not compatible")
        if not (regex or set_name):
            set_name = "full"
        if set_name and set_name not in (list(consts.TempestTestsSets) +
                                         list(consts.TempestTestsAPI)):
            print("Sorry, but there are no desired Tempest test set. Please, "
                  "choose from: %s" % ", ".join(list(consts.TempestTestsSets) +
                                                list(consts.TempestTestsAPI)))
            return (1)
        verification = api.Verification.verify(deployment, set_name, regex,
                                               tempest_config,
                                               system_wide_install)
        if do_use:
            self.use(verification["uuid"])

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @cliutils.args("--set", dest="set_name", type=str, required=False,
                   help="Name of tempest test set. Available sets: %s" % ", ".
                   join(list(consts.TempestTestsSets) +
                        list(consts.TempestTestsAPI)))
    @cliutils.args("--file", dest="log_file", type=str,
                   required=True,
                   help="User specified Tempest log file location. "
                        "Note, Tempest log file needs to be in subunit format")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   required=False,
                   help="Don't set new task as default for future operations")
    @cliutils.alias("import")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def import_results(self, deployment=None, set_name="", log_file=None,
                       do_use=True):
        """Import Tempest tests results into the Rally database.

        :param deployment: UUID or name of a deployment
        :param set_name: Name of tempest test set
        :param do_use: Use new task as default for future operations
        :param log_file: User specified Tempest log file in subunit format
        """

        deployment, verification = api.Verification.import_results(deployment,
                                                                   set_name,
                                                                   log_file)

        if do_use:
            self.use(verification["uuid"])

    def list(self):
        """Display all verifications table, started and finished."""

        fields = ["UUID", "Deployment UUID", "Set name", "Tests", "Failures",
                  "Created at", "Duration", "Status"]
        verifications = db.verification_list()

        for el in verifications:
            el["duration"] = el["updated_at"] - el["created_at"]

        if verifications:
            cliutils.print_list(verifications, fields,
                                sortby_index=fields.index("Created at"))
        else:
            print(_("There are no results from verifier. To run a verifier, "
                    "use:\nrally verify start"))

    @cliutils.args("--uuid", type=str, dest="verification_uuid",
                   help="UUID of the verification")
    @cliutils.args("--html", action="store_true", dest="output_html",
                   help=("Results will be in html format"))
    @cliutils.args("--json", action="store_true", dest="output_json",
                   help=("Results will be in json format"))
    @cliutils.args("--output-file", type=str, required=False,
                   dest="output_file",
                   help="If specified, output will be saved to given file")
    @envutils.with_default_verification_id
    @cliutils.suppress_warnings
    def results(self, verification_uuid=None, output_file=None,
                output_html=None, output_json=None):
        """Get raw results of the verification.

        :param verification_uuid: Verification UUID
        :param output_file: If specified, output will be saved to given file
        :param output_html: The output will be in HTML format
        :param output_json: The output will be in JSON format (Default)
        """

        try:
            results = db.verification_result_get(verification_uuid)["data"]
        except exceptions.NotFoundException as e:
            print(six.text_type(e))
            return 1

        result = ""
        if output_json + output_html > 1:
            print("Please specify only one output format.")
        elif output_html:
            result = json2html.HtmlOutput(results).create_report()
        else:
            result = json.dumps(results, sort_keys=True, indent=4)

        if output_file:
            output_file = os.path.expanduser(output_file)
            with open(output_file, "wb") as f:
                f.write(result)
        else:
            print(result)

    @cliutils.args("--uuid", dest="verification_uuid", type=str,
                   required=False,
                   help="UUID of a verification")
    @cliutils.args("--sort-by", dest="sort_by", type=str, required=False,
                   help="Tests can be sorted by 'name' or 'duration'")
    @cliutils.args("--detailed", dest="detailed", action="store_true",
                   required=False, help="Prints traceback of failed tests")
    @envutils.with_default_verification_id
    def show(self, verification_uuid=None, sort_by="name", detailed=False):
        """Display results table of the verification."""

        try:
            sortby_index = ("name", "duration").index(sort_by)
        except ValueError:
            print("Sorry, but verification results can't be sorted "
                  "by '%s'." % sort_by)
            return 1

        try:
            verification = db.verification_get(verification_uuid)
            tests = db.verification_result_get(verification_uuid)
        except exceptions.NotFoundException as e:
            print(six.text_type(e))
            return 1

        print ("Total results of verification:\n")
        total_fields = ["UUID", "Deployment UUID", "Set name", "Tests",
                        "Failures", "Created at", "Status"]
        cliutils.print_list([verification], fields=total_fields)

        print ("\nTests:\n")
        fields = ["name", "time", "status"]

        values = [objects.Verification(test)
                  for test in six.itervalues(tests.data["test_cases"])]
        cliutils.print_list(values, fields, sortby_index=sortby_index)

        if detailed:
            for test in six.itervalues(tests.data["test_cases"]):
                if test["status"] == "FAIL":
                    header = cliutils.make_header(
                        "FAIL: %(name)s\n"
                        "Time: %(time)s\n"
                        "Type: %(type)s" % {"name": test["name"],
                                            "time": test["time"],
                                            "type": test["failure"]["type"]})
                    formatted_test = "%(header)s%(log)s\n" % {
                        "header": header,
                        "log": test["failure"]["log"]}
                    print (formatted_test)

    @cliutils.args("--uuid", dest="verification_uuid", type=str,
                   required=False,
                   help="UUID of a verification")
    @cliutils.args("--sort-by", dest="sort_by", type=str, required=False,
                   help="Tests can be sorted by 'name' or 'duration'")
    @envutils.with_default_verification_id
    def detailed(self, verification_uuid=None, sort_by="name"):
        """Display results table of verification with detailed errors."""

        self.show(verification_uuid, sort_by, True)

    @cliutils.args("--uuid-1", type=str, dest="uuid1",
                   help="UUID of the first verification")
    @cliutils.args("--uuid-2", type=str, dest="uuid2",
                   help="UUID of the second verification")
    @cliutils.args("--csv", action="store_true", dest="output_csv",
                   help=("Save results in csv format to specified file"))
    @cliutils.args("--html", action="store_true", dest="output_html",
                   help=("Save results in html format to specified file"))
    @cliutils.args("--json", action="store_true", dest="output_json",
                   help=("Save results in json format to specified file"))
    @cliutils.args("--output-file", type=str, required=False,
                   dest="output_file",
                   help="If specified, output will be saved to given file")
    @cliutils.args("--threshold", type=int, required=False,
                   dest="threshold", default=0,
                   help="If specified, timing differences must exceed this "
                   "percentage threshold to be included in output")
    def compare(self, uuid1=None, uuid2=None,
                output_file=None, output_csv=None, output_html=None,
                output_json=None, threshold=0):
        """Compare two verification results.

        :param uuid1: First Verification UUID
        :param uuid2: Second Verification UUID
        :param output_file: If specified, output will be saved to given file
        :param output_csv: Save results in csv format to the specified file
        :param output_html: Save results in html format to the specified file
        :param output_json: Save results in json format to the specified file
                            (Default)
        :param threshold: Timing difference threshold percentage
        """

        try:
            results1 = db.verification_result_get(uuid1)["data"]["test_cases"]
            results2 = db.verification_result_get(uuid2)["data"]["test_cases"]
            _diff = diff.Diff(results1, results2, threshold)
        except exceptions.NotFoundException as e:
            print(six.text_type(e))
            return 1

        result = ""
        if output_json + output_html + output_csv > 1:
            print("Please specify only one output format, either --json, "
                  "--html or --csv.")
            return 1
        elif output_html:
            result = _diff.to_html()
        elif output_csv:
            result = _diff.to_csv()
        else:
            result = _diff.to_json()

        if output_file:
            with open(output_file, "wb") as f:
                if output_csv:
                    writer = csv.writer(f, dialect="excel")
                    writer.writerows(result)
                else:
                    f.write(result)
        else:
            print(result)

    @cliutils.args("--verification", type=str, dest="verification",
                   required=False, help="UUID of the verification")
    def use(self, verification):
        """Set active verification.

        :param verification: a UUID of verification
        """
        print("Verification UUID: %s" % verification)
        db.verification_get(verification)
        fileutils.update_globals_file("RALLY_VERIFICATION", verification)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment")
    @cliutils.args("--tempest-config", dest="tempest_config", type=str,
                   required=False,
                   help="User specified Tempest config file location")
    @cliutils.args("--override", dest="override",
                   help="Override existing Tempest config file",
                   required=False, action="store_true")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def genconfig(self, deployment=None, tempest_config=None, override=False):
        """Generate configuration file of Tempest.

        :param deployment: UUID or name of a deployment
        :param tempest_config: User specified Tempest config file location
        :param override: Whether or not override existing Tempest config file
        """
        api.Verification.configure_tempest(deployment, tempest_config,
                                           override)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of a deployment")
    @cliutils.args("--source", type=str, dest="source", required=False,
                   help="Path/URL to repo to pull Tempest from")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def install(self, deployment=None, source=None):
        """Install Tempest.

        :param deployment: UUID or name of a deployment
        :param source: Path/URL to repo to pull Tempest from
        """
        api.Verification.install_tempest(deployment, source)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of a deployment")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def uninstall(self, deployment=None):
        """Remove deployment's local Tempest installation.

        :param deployment: UUID or name of a deployment
        """
        api.Verification.uninstall_tempest(deployment)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of a deployment")
    @cliutils.args("--tempest-config", dest="tempest_config", type=str,
                   required=False,
                   help="User specified Tempest config file location")
    @cliutils.args("--source", type=str, dest="source",
                   required=False, help="New path/URL to repo to pull Tempest "
                                        "from. Use old source as default")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def reinstall(self, deployment=None, tempest_config=None, source=None):
        """Uninstall Tempest and then reinstall from new source.

        :param deployment: UUID or name of a deployment
        :param tempest_config: User specified Tempest config file location
        :param source: New path/URL to repo to pull Tempest from
        """
        api.Verification.reinstall_tempest(deployment, tempest_config, source)
