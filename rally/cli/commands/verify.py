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
import yaml

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally.common import fileutils
from rally.common.i18n import _
from rally.common import utils
from rally import consts
from rally import exceptions
from rally.verification.tempest import diff
from rally.verification.tempest import json2html


AVAILABLE_SETS = list(consts.TempestTestsSets) + list(consts.TempestTestsAPI)


class VerifyCommands(object):
    """Verify an OpenStack cloud via Tempest.

    Set of commands that allow you to run Tempest tests.
    """

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment")
    @cliutils.args("--set", dest="set_name", type=str, required=False,
                   help="Name of a Tempest test set. "
                        "Available sets are %s" % ", ".join(AVAILABLE_SETS))
    @cliutils.args("--regex", dest="regex", type=str, required=False,
                   help="Regular expression of test")
    @cliutils.args("--tests-file", dest="tests_file", type=str,
                   help="Path to a file with a list of Tempest tests",
                   required=False)
    @cliutils.args("--tempest-config", dest="tempest_config", type=str,
                   required=False,
                   help="User specified Tempest config file location")
    @cliutils.args("--xfails-file", dest="xfails_file", type=str,
                   required=False,
                   help="Path to a file in YAML format with a list of Tempest "
                        "tests that are expected to fail")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don't set new task as default for future operations")
    @cliutils.args("--system-wide", dest="system_wide",
                   help="Don't create a virtual env when installing Tempest; "
                        "use the local env instead of the Tempest virtual env "
                        "when running the tests. Take notice that all Tempest "
                        "requirements have to be already installed in "
                        "the local env!",
                   required=False, action="store_true")
    @cliutils.deprecated_args("--system-wide-install", dest="system_wide",
                              help="Use --system-wide instead",
                              required=False, action="store_true")
    @cliutils.args("--concurrency", dest="concur", type=int, required=False,
                   help="How many processes to use to run Tempest tests. "
                        "The default value (0) auto-detects your CPU count")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def start(self, deployment=None, set_name="", regex=None,
              tests_file=None, tempest_config=None, xfails_file=None,
              do_use=True, system_wide=False, concur=0):
        """Start verification (run Tempest tests).

        :param deployment: UUID or name of a deployment
        :param set_name: Name of a Tempest test set
        :param regex: Regular expression of test
        :param tests_file: Path to a file with a list of Tempest tests
        :param tempest_config: User specified Tempest config file location
        :param xfails_file: Path to a file in YAML format with a list of
                            Tempest tests that are expected to fail
        :param do_use: Use new task as default for future operations
        :param system_wide: Whether or not to create a virtual env when
                            installing Tempest; whether or not to use
                            the local env instead of the Tempest virtual
                            env when running the tests
        :param concur: How many processes to use to run Tempest tests.
                       The default value (0) auto-detects CPU count
        """
        msg = _("Arguments '%s' and '%s' are not compatible. "
                "You can use only one of the mentioned arguments.")
        if regex and set_name:
            print(msg % ("regex", "set"))
            return 1
        if tests_file and set_name:
            print(msg % ("tests_file", "set"))
            return 1
        if tests_file and regex:
            print(msg % ("tests_file", "regex"))
            return 1

        if not (regex or set_name or tests_file):
            set_name = "full"

        if set_name and set_name not in AVAILABLE_SETS:
            print(_("Tempest test set '%s' not found "
                    "in available test sets. Available sets are %s.")
                  % (set_name, ", ".join(AVAILABLE_SETS)))
            return 1

        if tests_file and not os.path.exists(tests_file):
            print(_("File '%s' not found.") % tests_file)
            return 1

        expected_failures = None
        if xfails_file:
            if os.path.exists(xfails_file):
                with open(os.path.abspath(xfails_file), "rb") as f:
                    expected_failures = yaml.load(f)
            else:
                print(_("File '%s' not found.") % xfails_file)
                return 1

        verification = api.Verification.verify(
            deployment, set_name=set_name, regex=regex, tests_file=tests_file,
            tempest_config=tempest_config, expected_failures=expected_failures,
            system_wide=system_wide, concur=concur)
        if do_use:
            self.use(verification["uuid"])

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment")
    @cliutils.args("--set", dest="set_name", type=str, required=False,
                   help="Name of a Tempest test set. "
                        "Available sets are %s" % ", ".join(AVAILABLE_SETS))
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
        :param set_name: Name of a Tempest test set
        :param do_use: Use new task as default for future operations
        :param log_file: User specified Tempest log file in subunit format
        """
        deployment, verification = api.Verification.import_results(deployment,
                                                                   set_name,
                                                                   log_file)
        if do_use:
            self.use(verification["uuid"])

    def list(self):
        """Display verifications table."""

        fields = ["UUID", "Deployment UUID", "Set name", "Tests", "Failures",
                  "Created at", "Duration", "Status"]
        verifications = api.Verification.list()

        for el in verifications:
            el["duration"] = el["updated_at"] - el["created_at"]

        if verifications:
            cliutils.print_list(verifications, fields,
                                sortby_index=fields.index("Created at"))
        else:
            print(_("No verification was started yet. "
                    "To start verification use:\nrally verify start"))

    @cliutils.args("--uuid", type=str, dest="verification_uuid",
                   help="UUID of a verification")
    @cliutils.args("--html", action="store_true", dest="output_html",
                   help="Display results in HTML format")
    @cliutils.args("--json", action="store_true", dest="output_json",
                   help="Display results in JSON format")
    @cliutils.args("--output-file", type=str, required=False,
                   dest="output_file",
                   help="Path to a file to save results")
    @envutils.with_default_verification_id
    @cliutils.suppress_warnings
    def results(self, verification_uuid=None, output_file=None,
                output_html=None, output_json=None):
        """Display results of a verification.

        :param verification_uuid: UUID of a verification
        :param output_file: Path to a file to save results
        :param output_html: Display results in HTML format
        :param output_json: Display results in JSON format (Default)
        """
        try:
            results = api.Verification.get(verification_uuid).get_results()
        except exceptions.NotFoundException as e:
            print(six.text_type(e))
            return 1

        result = ""
        if output_json + output_html > 1:
            print(_("Please specify only one "
                    "output format: --json or --html."))
        elif output_html:
            result = json2html.generate_report(results)
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
                   help="Sort results by 'name' or 'duration'")
    @cliutils.args("--detailed", dest="detailed", action="store_true",
                   required=False,
                   help="Display detailed errors of failed tests")
    @envutils.with_default_verification_id
    def show(self, verification_uuid=None, sort_by="name", detailed=False):
        """Display results table of a verification.

        :param verification_uuid: UUID of a verification
        :param sort_by: Sort results by 'name' or 'duration'
        :param detailed: Display detailed errors of failed tests
        """
        try:
            sortby_index = ("name", "duration").index(sort_by)
        except ValueError:
            print(_("Verification results can't be sorted by '%s'.") % sort_by)
            return 1

        try:
            verification = api.Verification.get(verification_uuid)
            tests = verification.get_results()
        except exceptions.NotFoundException as e:
            print(six.text_type(e))
            return 1

        print(_("Total results of verification:\n"))
        total_fields = ["UUID", "Deployment UUID", "Set name", "Tests",
                        "Failures", "Created at", "Status"]
        cliutils.print_list([verification], fields=total_fields)

        print(_("\nTests:\n"))
        fields = ["name", "time", "status"]

        results = tests["test_cases"]
        values = [utils.Struct(**results[test_name]) for test_name in results]
        cliutils.print_list(values, fields, sortby_index=sortby_index)

        if detailed:
            for test in six.itervalues(tests["test_cases"]):
                if test["status"] == "fail":
                    header = cliutils.make_header(
                        "FAIL: %(name)s\n"
                        "Time: %(time)s" % {"name": test["name"],
                                            "time": test["time"]})
                    formatted_test = "%(header)s%(log)s\n" % {
                        "header": header,
                        "log": test["traceback"]}
                    print(formatted_test)

    @cliutils.args("--uuid", dest="verification_uuid", type=str,
                   required=False, help="UUID of a verification")
    @cliutils.args("--sort-by", dest="sort_by", type=str, required=False,
                   help="Sort results by 'name' or 'duration'")
    @envutils.with_default_verification_id
    def detailed(self, verification_uuid=None, sort_by="name"):
        """Display results table of a verification with detailed errors.

        :param verification_uuid: UUID of a verification
        :param sort_by: Sort results by 'name' or 'duration'
        """
        self.show(verification_uuid, sort_by, True)

    @cliutils.args("--uuid-1", type=str, required=True, dest="uuid1",
                   help="UUID of the first verification")
    @cliutils.args("--uuid-2", type=str, required=True, dest="uuid2",
                   help="UUID of the second verification")
    @cliutils.args("--csv", action="store_true", dest="output_csv",
                   help="Display results in CSV format")
    @cliutils.args("--html", action="store_true", dest="output_html",
                   help="Display results in HTML format")
    @cliutils.args("--json", action="store_true", dest="output_json",
                   help="Display results in JSON format")
    @cliutils.args("--output-file", type=str, required=False,
                   dest="output_file", help="Path to a file to save results")
    @cliutils.args("--threshold", type=int, required=False,
                   dest="threshold", default=0,
                   help="If specified, timing differences must exceed this "
                   "percentage threshold to be included in output")
    def compare(self, uuid1=None, uuid2=None,
                output_file=None, output_csv=None, output_html=None,
                output_json=None, threshold=0):
        """Compare two verification results.

        :param uuid1: UUID of the first verification
        :param uuid2: UUID of the second verification
        :param output_file: Path to a file to save results
        :param output_csv: Display results in CSV format
        :param output_html: Display results in HTML format
        :param output_json: Display results in JSON format (Default)
        :param threshold: Timing difference threshold percentage
        """
        try:
            res_1 = api.Verification.get(uuid1).get_results()["test_cases"]
            res_2 = api.Verification.get(uuid2).get_results()["test_cases"]
            _diff = diff.Diff(res_1, res_2, threshold)
        except exceptions.NotFoundException as e:
            print(six.text_type(e))
            return 1

        result = ""
        if output_json + output_html + output_csv > 1:
            print(_("Please specify only one output "
                    "format: --json, --html or --csv."))
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
                   required=False, help="UUID of a verification")
    def use(self, verification):
        """Set active verification.

        :param verification: UUID of a verification
        """
        print(_("Verification UUID: %s") % verification)
        api.Verification.get(verification)
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
        :param override: Whether or not to override existing Tempest
                         config file
        """
        api.Verification.configure_tempest(deployment, tempest_config,
                                           override)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of a deployment")
    @cliutils.args("--source", type=str, dest="source", required=False,
                   help="Path/URL to repo to clone Tempest from")
    @cliutils.args("--no-tempest-venv", dest="no_tempest_venv",
                   help="Don't create a virtual env for Tempest. Take notice "
                        "that all Tempest requirements have to be already "
                        "installed in the local env!",
                   required=False, action="store_true")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def install(self, deployment=None, source=None, no_tempest_venv=False):
        """Install Tempest.

        :param deployment: UUID or name of a deployment
        :param source: Path/URL to repo to clone Tempest from
        :param no_tempest_venv: Whether or not to create a Tempest virtual env
        """
        api.Verification.install_tempest(deployment, source, no_tempest_venv)

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
    @cliutils.args("--source", type=str, dest="source", required=False,
                   help="Path/URL to repo to clone Tempest from")
    @cliutils.args("--no-tempest-venv", dest="no_tempest_venv",
                   help="Don't create a virtual env for Tempest. Take notice "
                        "that all Tempest requirements have to be already "
                        "installed in the local env!",
                   required=False, action="store_true")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def reinstall(self, deployment=None,
                  tempest_config=None, source=None, no_tempest_venv=False):
        """Uninstall Tempest and install again.

        :param deployment: UUID or name of a deployment
        :param tempest_config: User specified Tempest config file location
        :param source: Path/URL to repo to clone Tempest from
        :param no_tempest_venv: Whether or not to create a Tempest virtual env
        """
        api.Verification.reinstall_tempest(deployment, tempest_config,
                                           source, no_tempest_venv)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of a deployment")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def showconfig(self, deployment=None):
        """Show configuration file of Tempest.

        :param deployment: UUID or name of a deployment
        """
        conf_info = api.Verification.show_config_info(deployment)
        print(_("Tempest config file: %s") % conf_info["conf_path"])
        print("\n" + conf_info["conf_data"])
