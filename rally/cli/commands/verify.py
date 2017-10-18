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

"""Rally command: verify"""

from __future__ import print_function

import datetime as dt
import json
import os
import webbrowser

from six.moves import configparser

from rally.cli import cliutils
from rally.cli import envutils
from rally.common import fileutils
from rally.common import logging
from rally.common import yamlutils as yaml
from rally import exceptions
from rally import plugins

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

LIST_VERIFIERS_HINT = ("HINT: You can list all verifiers, executing "
                       "command `rally verify list-verifiers`.")
LIST_DEPLOYMENTS_HINT = ("HINT: You can list all deployments, executing "
                         "command `rally deployment list`.")
LIST_VERIFICATIONS_HINT = ("HINT: You can list all verifications, executing "
                           "command `rally verify list`.")

DEFAULT_REPORT_TYPES = ("HTML", "HTML-Static", "JSON", "JUnit-XML")


class VerifyCommands(object):
    """Verify an OpenStack cloud via a verifier."""

    @staticmethod
    def _print_totals(totals):
        print("\n======\n"
              "Totals"
              "\n======\n"
              "\nRan: %(tests_count)s tests in %(tests_duration)s sec.\n"
              " - Success: %(success)s\n"
              " - Skipped: %(skipped)s\n"
              " - Expected failures: %(expected_failures)s\n"
              " - Unexpected success: %(unexpected_success)s\n"
              " - Failures: %(failures)s\n" % totals)

    @staticmethod
    def _print_failures(h_text, failures, symbol="-"):
        print("\n%s" % cliutils.make_header(
            h_text, size=len(h_text), symbol=symbol).strip())
        for f in failures:
            header = "%s\n%s\n" % (f["name"], "-" * len(f["name"]))
            failure = "\n%s%s\n" % (header, f["traceback"].strip())
            print(failure)

    def _print_details_after_run(self, results):
        failures = [t for t in results["tests"].values()
                    if t["status"] == "fail"]
        if failures:
            h_text = "Failed %d %s - output below:" % (
                len(failures), "tests" if len(failures) > 1 else "test")
            self._print_failures(h_text, failures, "=")
        else:
            print("\nCongratulations! "
                  "Verification doesn't have failed tests ;)")

    @staticmethod
    def _base_dir(uuid):
        return os.path.expanduser(
            "~/.rally/verification/verifier-%s" % uuid)

    def _get_location(self, uuid, loc):
        return os.path.join(self._base_dir(uuid), loc)

    @cliutils.args("--platform", dest="platform", type=str,
                   help="Requried patform (e.g. openstack).")
    @cliutils.deprecated_args("--namespace", dest="platform",
                              release="0.10.0", alternative="--platform")
    @plugins.ensure_plugins_are_loaded
    def list_plugins(self, api, platform=None):
        """List all plugins for verifiers management."""

        if platform:
            platform = platform.lower()
        verifier_plugins = api.verifier.list_plugins(platform=platform)

        fields = ["Plugin name", "Platform", "Description"]
        if logging.is_debug():
            fields.append("Location")

        cliutils.print_list(verifier_plugins, fields,
                            formatters={"Plugin name": lambda p: p["name"]},
                            normalize_field_names=True)

    @cliutils.help_group("verifier")
    @cliutils.args("--name", dest="name", type=str, required=True,
                   help="Verifier name (for example, 'My verifier').")
    @cliutils.args("--type", dest="vtype", type=str, required=True,
                   help="Verifier plugin name. HINT: You can list all "
                        "verifier plugins, executing command `rally verify "
                        "list-plugins`.")
    @cliutils.args("--platform", dest="platform", type=str,
                   help="Verifier plugin platform. Should be specified in "
                        "case of two verifier plugins with equal names but "
                        "in different platforms.")
    @cliutils.deprecated_args("--namespace", dest="platform",
                              release="0.10.0", alternative="--platform")
    @cliutils.args("--source", dest="source", type=str, required=False,
                   help="Path or URL to the repo to clone verifier from.")
    @cliutils.args("--version", dest="version", type=str, required=False,
                   help="Branch, tag or commit ID to checkout before "
                        "verifier installation (the 'master' branch is used "
                        "by default).")
    @cliutils.args("--system-wide", dest="system_wide", action="store_true",
                   required=False,
                   help="Use the system-wide environment for verifier instead "
                        "of a virtual environment.")
    @cliutils.args("--extra-settings", dest="extra", type=str, required=False,
                   help="Extra installation settings for verifier.")
    @cliutils.args("--no-use", dest="do_use", action="store_false",
                   help="Not to set the created verifier as the default "
                        "verifier for future operations.")
    @plugins.ensure_plugins_are_loaded
    def create_verifier(self, api, name, vtype, platform="", source=None,
                        version=None, system_wide=False, extra=None,
                        do_use=True):
        """Create a verifier."""

        verifier_uuid = api.verifier.create(
            name=name, vtype=vtype, platform=platform, source=source,
            version=version, system_wide=system_wide, extra_settings=extra)

        if do_use:
            self.use_verifier(api, verifier_uuid)

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str, required=True,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    def use_verifier(self, api, verifier_id):
        """Choose a verifier to use for the future operations."""
        verifier = api.verifier.get(verifier_id=verifier_id)
        fileutils.update_globals_file(envutils.ENV_VERIFIER, verifier["uuid"])
        print("Using verifier '%s' (UUID=%s) as the default verifier "
              "for the future CLI operations."
              % (verifier["name"], verifier["uuid"]))

    @cliutils.help_group("verifier")
    @cliutils.args("--status", dest="status", type=str, required=False,
                   help="Status to filter verifiers by.")
    @plugins.ensure_plugins_are_loaded
    def list_verifiers(self, api, status=None):
        """List all verifiers."""

        verifiers = api.verifier.list(status=status)
        if verifiers:
            fields = ["UUID", "Name", "Type", "Platform", "Created at",
                      "Updated at", "Status", "Version", "System-wide",
                      "Active"]
            cv = envutils.get_global(envutils.ENV_VERIFIER)
            formatters = {
                "Created at": lambda v: v["created_at"],
                "Updated at": lambda v: v["updated_at"],
                "Active": lambda v: u"\u2714" if v["uuid"] == cv else "",
            }
            cliutils.print_list(verifiers, fields, formatters=formatters,
                                normalize_field_names=True, sortby_index=4)
        elif status:
            print("There are no verifiers with status '%s'." % status)
        else:
            print("There are no verifiers. You can create verifier, using "
                  "command `rally verify create-verifier`.")

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def show_verifier(self, api, verifier_id=None):
        """Show detailed information about a verifier."""

        verifier = api.verifier.get(verifier_id=verifier_id)
        fields = ["UUID", "Status", "Created at", "Updated at", "Active",
                  "Name", "Description", "Type", "Platform", "Source",
                  "Version", "System-wide", "Extra settings", "Location",
                  "Venv location"]
        used_verifier = envutils.get_global(envutils.ENV_VERIFIER)
        formatters = {
            "Created at": lambda v: v["created_at"].replace("T", " "),
            "Updated at": lambda v: v["updated_at"].replace("T", " "),
            "Active": lambda v: u"\u2714"
                                if v["uuid"] == used_verifier else None,
            "Extra settings": lambda v: (json.dumps(v["extra_settings"],
                                                    indent=4)
                                         if v["extra_settings"] else None),
            "Location": lambda v: self._get_location((v["uuid"]), "repo")
        }
        if not verifier["system_wide"]:
            formatters["Venv location"] = lambda v: self._get_location(
                v["uuid"], ".venv")
        cliutils.print_dict(verifier, fields=fields, formatters=formatters,
                            normalize_field_names=True, print_header=False,
                            table_label="Verifier")
        print("Attention! All you do in the verifier repository or verifier "
              "virtual environment, you do it at your own risk!")

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str, required=True,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>", required=False,
                   help="Deployment name or UUID. If specified, only the "
                        "deployment-specific data will be deleted for "
                        "verifier. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--force", dest="force", action="store_true",
                   required=False,
                   help="Delete all stored verifications of the specified "
                        "verifier. If a deployment specified, only "
                        "verifications of this deployment will be deleted. "
                        "Use this argument carefully! You can delete "
                        "verifications that may be important to you.")
    @plugins.ensure_plugins_are_loaded
    def delete_verifier(self, api, verifier_id, deployment=None, force=False):
        """Delete a verifier."""

        api.verifier.delete(verifier_id=verifier_id,
                            deployment_id=deployment,
                            force=force)

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--update-venv", dest="update_venv", action="store_true",
                   required=False,
                   help="Update the virtual environment for verifier.")
    @cliutils.args("--version", dest="version", type=str, required=False,
                   help="Branch, tag or commit ID to checkout. HINT: Specify "
                        "the same version to pull the latest repo code.")
    @cliutils.args("--system-wide", dest="system_wide", action="store_true",
                   required=False,
                   help="Switch to using the system-wide environment.")
    @cliutils.args("--no-system-wide", dest="no_system_wide",
                   action="store_true", required=False,
                   help="Switch to using the virtual environment. "
                        "If the virtual environment doesn't exist, "
                        "it will be created.")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def update_verifier(self, api, verifier_id=None, version=None,
                        system_wide=None, no_system_wide=None,
                        update_venv=None):
        """Update a verifier."""

        if not (version or system_wide or no_system_wide or update_venv):
            print("At least one of the following arguments should be "
                  "provided: '--update-venv', '--version', '--system-wide', "
                  "'--no-system-wide'.")
            return 1

        msg = ("Arguments '--%s' and '--%s' cannot be used simultaneously. "
               "You can use only one of the mentioned arguments.")
        if update_venv and system_wide:
            print(msg % ("update-venv", "system-wide"))
            return 1
        if system_wide and no_system_wide:
            print(msg % ("system-wide", "no-system-wide"))
            return 1

        system_wide = False if no_system_wide else (system_wide or None)
        api.verifier.update(verifier_id=verifier_id,
                            system_wide=system_wide,
                            version=version,
                            update_venv=update_venv)

        print("HINT: In some cases the verifier config file should be "
              "updated as well. Use `rally verify configure-verifier` "
              "command to update the config file.")

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>",
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--reconfigure", dest="reconfigure", action="store_true",
                   required=False, help="Reconfigure verifier.")
    @cliutils.args("--extend", dest="extra_options", type=str,
                   metavar="<path/json/yaml>", required=False,
                   help="Extend verifier configuration with extra options. "
                        "If options are already present, the given ones will "
                        "override them. Can be a path to a regular config "
                        "file or just a json/yaml.")
    @cliutils.args("--override", dest="new_configuration", type=str,
                   metavar="<path>", required=False,
                   help="Override verifier configuration by another one "
                        "from a given source.")
    @cliutils.args("--show", dest="show", action="store_true", required=False,
                   help="Show verifier configuration.")
    @envutils.with_default_deployment(cli_arg_name="deployment-id")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def configure_verifier(self, api, verifier_id=None, deployment=None,
                           reconfigure=False, extra_options=None,
                           new_configuration=None, show=False):
        """Configure a verifier for a specific deployment."""

        # TODO(ylobankov): Add an ability to read extra options from
        #                  a json or yaml file.
        if new_configuration and (extra_options or reconfigure):
            print("Argument '--override' cannot be used with arguments "
                  "'--reconfigure' and '--extend'.")
            return 1

        if new_configuration:
            if not os.path.exists(new_configuration):
                print("File '%s' not found." % new_configuration)
                return 1

            with open(new_configuration) as f:
                config = f.read()
            api.verifier.override_configuration(verifier_id=verifier_id,
                                                deployment_id=deployment,
                                                new_configuration=config)
        else:
            if extra_options:
                if os.path.isfile(extra_options):
                    conf = configparser.ConfigParser()
                    conf.read(extra_options)
                    extra_options = dict(conf._sections)
                    for s in extra_options:
                        extra_options[s] = dict(extra_options[s])
                        extra_options[s].pop("__name__", None)

                    defaults = dict(conf.defaults())
                    if defaults:
                        extra_options["DEFAULT"] = dict(conf.defaults())
                else:
                    extra_options = yaml.safe_load(extra_options)

            config = api.verifier.configure(verifier=verifier_id,
                                            deployment_id=deployment,
                                            extra_options=extra_options,
                                            reconfigure=reconfigure)

        if show:
            print("\n%s\n" % config.strip())

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--pattern", dest="pattern", type=str, required=False,
                   help="Pattern which will be used for matching. Can be a "
                        "regexp or a verifier-specific entity (for example, "
                        "in case of Tempest you can specify 'set=smoke').")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def list_verifier_tests(self, api, verifier_id=None, pattern=""):
        """List all verifier tests."""

        tests = api.verifier.list_tests(verifier_id=verifier_id,
                                        pattern=pattern)
        if tests:
            for test in tests:
                print(test)
        else:
            print("No tests found.")

    @cliutils.help_group("verifier-ext")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--source", dest="source", type=str, required=True,
                   help="Path or URL to the repo to clone verifier "
                        "extension from.")
    @cliutils.args("--version", dest="version", type=str, required=False,
                   help="Branch, tag or commit ID to checkout before "
                        "installation of the verifier extension (the "
                        "'master' branch is used by default).")
    @cliutils.args("--extra-settings", dest="extra", type=str, required=False,
                   help="Extra installation settings for verifier extension.")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def add_verifier_ext(self, api, verifier_id=None, source=None,
                         version=None, extra=None):
        """Add a verifier extension."""

        api.verifier.add_extension(verifier_id=verifier_id, source=source,
                                   version=version, extra_settings=extra)

    @cliutils.help_group("verifier-ext")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def list_verifier_exts(self, api, verifier_id=None):
        """List all verifier extensions."""

        verifier_exts = api.verifier.list_extensions(verifier_id=verifier_id)
        if verifier_exts:
            fields = ["Name", "Entry point"]
            if logging.is_debug():
                fields.append("Location")
            cliutils.print_list(verifier_exts, fields,
                                normalize_field_names=True)
        else:
            print("There are no verifier extensions. You can add verifier "
                  "extension, using command `rally verify add-verifier-ext`.")

    @cliutils.help_group("verifier-ext")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--name", type=str, required=True,
                   help="Verifier extension name.")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def delete_verifier_ext(self, api, verifier_id=None, name=None):
        """Delete a verifier extension."""

        api.verifier.delete_extension(verifier_id=verifier_id, name=name)

    @cliutils.help_group("verification")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>",
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--tag", nargs="+", dest="tags", type=str, required=False,
                   help="Mark verification with a tag or a few tags.")
    @cliutils.args("--pattern", dest="pattern", type=str, required=False,
                   help="Pattern which will be used for running tests. Can be "
                        "a regexp or a verifier-specific entity (for example, "
                        "in case of Tempest you can specify 'set=smoke').")
    @cliutils.args("--concurrency", dest="concur", type=int, metavar="<N>",
                   required=False,
                   help="How many processes to be used for running verifier "
                        "tests. The default value (0) auto-detects your CPU "
                        "count.")
    @cliutils.args("--load-list", dest="load_list", type=str, metavar="<path>",
                   required=False,
                   help="Path to a file with a list of tests to run.")
    @cliutils.args("--skip-list", dest="skip_list", type=str, metavar="<path>",
                   required=False,
                   help="Path to a file with a list of tests to skip. "
                        "Format: json or yaml like a dictionary where keys "
                        "are test names and values are reasons.")
    @cliutils.args("--xfail-list", dest="xfail_list", type=str,
                   metavar="<path>", required=False,
                   help="Path to a file with a list of tests that will be "
                        "considered as expected failures. "
                        "Format: json or yaml like a dictionary where keys "
                        "are test names and values are reasons.")
    @cliutils.args("--detailed", dest="detailed", action="store_true",
                   required=False,
                   help="Show verification details such as errors of failed "
                        "tests.")
    @cliutils.args("--no-use", dest="do_use", action="store_false",
                   help="Not to set the finished verification as the default "
                        "verification for future operations.")
    @envutils.with_default_deployment(cli_arg_name="deployment-id")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def start(self, api, verifier_id=None, deployment=None, tags=None,
              pattern=None, concur=0, load_list=None, skip_list=None,
              xfail_list=None, detailed=False, do_use=True):
        """Start a verification (run verifier tests)."""

        if pattern and load_list:
            print("Arguments '--pattern' and '--load-list' cannot be used "
                  "together, use only one of them.")
            return 1

        def parse(filename):
            with open(filename, "r") as f:
                return yaml.safe_load(f.read())

        if load_list:
            if not os.path.exists(load_list):
                print("File '%s' not found." % load_list)
                return 1
            with open(load_list, "r") as f:
                load_list = [test for test in f.read().split("\n") if test]

        if skip_list:
            if not os.path.exists(skip_list):
                print("File '%s' not found." % skip_list)
                return 1
            skip_list = parse(skip_list)

        if xfail_list:
            if not os.path.exists(xfail_list):
                print("File '%s' not found." % xfail_list)
                return 1
            xfail_list = parse(xfail_list)

        run_args = {key: value for key, value in (
            ("pattern", pattern), ("load_list", load_list),
            ("skip_list", skip_list), ("xfail_list", xfail_list),
            ("concurrency", concur)) if value}

        try:
            results = api.verification.start(
                verifier_id=verifier_id, deployment_id=deployment,
                tags=tags, **run_args)
            verification_uuid = results["verification"]["uuid"]
        except exceptions.DeploymentNotFinishedStatus as e:
            print("Cannot start a verefication against unfinished deployment: "
                  " %s" % e)
            return 1

        if detailed:
            self._print_details_after_run(results)

        self._print_totals(results["totals"])

        if do_use:
            self.use(api, verification_uuid)
        else:
            print("Verification UUID: %s." % verification_uuid)

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", dest="verification_uuid", type=str, required=True,
                   help="Verification UUID. " + LIST_VERIFICATIONS_HINT)
    def use(self, api, verification_uuid):
        """Choose a verification to use for the future operations."""

        verification = api.verification.get(
            verification_uuid=verification_uuid)
        fileutils.update_globals_file(
            envutils.ENV_VERIFICATION, verification["uuid"])
        print("Using verification (UUID=%s) as the default verification "
              "for the future operations." % verification["uuid"])

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", dest="verification_uuid", type=str,
                   help="Verification UUID. " + LIST_VERIFICATIONS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>",
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--failed", dest="failed", required=False,
                   help="Rerun only failed tests.", action="store_true")
    @cliutils.args("--tag", nargs="+", dest="tags", type=str, required=False,
                   help="Mark verification with a tag or a few tags.")
    @cliutils.args("--concurrency", dest="concur", type=int, metavar="<N>",
                   required=False,
                   help="How many processes to be used for running verifier "
                        "tests. The default value (0) auto-detects your CPU "
                        "count.")
    @cliutils.args("--detailed", dest="detailed", action="store_true",
                   required=False,
                   help="Show verification details such as errors of failed "
                        "tests.")
    @cliutils.args("--no-use", dest="do_use", action="store_false",
                   help="Not to set the finished verification as the default "
                        "verification for future operations.")
    @envutils.with_default_verification_uuid
    @envutils.with_default_deployment(cli_arg_name="deployment-id")
    @plugins.ensure_plugins_are_loaded
    def rerun(self, api, verification_uuid=None, deployment=None, tags=None,
              concur=None, failed=False, detailed=False, do_use=True):
        """Rerun tests from a verification for a specific deployment."""

        results = api.verification.rerun(verification_uuid=verification_uuid,
                                         deployment_id=deployment,
                                         failed=failed,
                                         tags=tags,
                                         concurrency=concur)
        if detailed:
            self._print_details_after_run(results)

        self._print_totals(results["totals"])

        if do_use:
            self.use(api, results["verification"]["uuid"])
        else:
            print("Verification UUID: %s." % results["verification"]["uuid"])

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", dest="verification_uuid", type=str,
                   help="Verification UUID. " + LIST_VERIFICATIONS_HINT)
    @cliutils.args("--sort-by", metavar="<query>", dest="sort_by", type=str,
                   required=False, choices=("name", "duration", "status"),
                   help="Sort tests by 'name', 'duration' or 'status'.")
    @cliutils.args("--detailed", dest="detailed", action="store_true",
                   required=False,
                   help="Show verification details such as run arguments "
                        "and errors of failed tests.")
    @envutils.with_default_verification_uuid
    def show(self, api, verification_uuid=None, sort_by="name",
             detailed=False):
        """Show detailed information about a verification."""

        verification = api.verification.get(
            verification_uuid=verification_uuid)
        verifier = api.verifier.get(verifier_id=verification["verifier_uuid"])
        deployment = api.deployment.get(
            deployment=verification["deployment_uuid"])

        def run_args_formatter(v):
            run_args = []
            for k in sorted(v["run_args"]):
                if k in ("load_list", "skip_list", "xfail_list"):
                    value = "(value is too long, %s)"
                    if detailed:
                        value %= "will be displayed separately"
                    else:
                        value %= "use 'detailed' flag to display it"
                else:
                    value = v["run_args"][k]
                run_args.append("%s: %s" % (k, value))
            return "\n".join(run_args)

        # Main table
        fields = ["UUID", "Status", "Started at", "Finished at", "Duration",
                  "Run arguments", "Tags", "Verifier name", "Verifier type",
                  "Deployment name", "Tests count", "Tests duration, sec",
                  "Success", "Skipped", "Expected failures",
                  "Unexpected success", "Failures"]
        formatters = {
            "Started at": lambda v: v["created_at"].replace("T", " "),
            "Finished at": lambda v: v["updated_at"].replace("T", " "),
            "Duration": lambda v: (dt.datetime.strptime(v["updated_at"],
                                                        TIME_FORMAT) -
                                   dt.datetime.strptime(v["created_at"],
                                                        TIME_FORMAT)),
            "Run arguments": run_args_formatter,
            "Tags": lambda v: ", ".join(v["tags"]) or None,
            "Verifier name": lambda v: "%s (UUID: %s)" % (verifier["name"],
                                                          verifier["uuid"]),
            "Verifier type": (
                lambda v: "%s (platform: %s)" % (verifier["type"],
                                                 verifier["platform"])),
            "Deployment name": (
                lambda v: "%s (UUID: %s)" % (deployment["name"],
                                             deployment["uuid"])),
            "Tests duration, sec": lambda v: v["tests_duration"]
        }
        cliutils.print_dict(verification, fields, formatters=formatters,
                            normalize_field_names=True, print_header=False,
                            table_label="Verification")

        if detailed:
            h = "Run arguments"
            print("\n%s" % cliutils.make_header(h, len(h)).strip())
            print("\n%s\n" % json.dumps(verification["run_args"], indent=4))

        # Tests table
        tests = verification["tests"]
        values = [tests[test_id] for test_id in tests]
        fields = ["Name", "Duration, sec", "Status"]
        formatters = {"Duration, sec": lambda v: v["duration"]}
        index = ("name", "duration", "status").index(sort_by)
        cliutils.print_list(values, fields, formatters=formatters,
                            table_label="Tests", normalize_field_names=True,
                            sortby_index=index)

        if detailed:
            failures = [t for t in tests.values() if t["status"] == "fail"]
            if failures:
                self._print_failures("Failures", failures)
            else:
                print("\nCongratulations! Verification passed all tests ;)")

    @cliutils.help_group("verification")
    @cliutils.args("--id", dest="verifier_id", type=str, required=False,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>", required=False,
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--tag", nargs="+", dest="tags", type=str, required=False,
                   help="Tags to filter verifications by.")
    @cliutils.args("--status", dest="status", type=str, required=False,
                   help="Status to filter verifications by.")
    def list(self, api, verifier_id=None, deployment=None, tags=None,
             status=None):
        """List all verifications."""

        verifications = api.verification.list(verifier_id=verifier_id,
                                              deployment_id=deployment,
                                              tags=tags, status=status)
        if verifications:
            fields = ["UUID", "Tags", "Verifier name", "Deployment name",
                      "Started at", "Finished at", "Duration", "Status"]
            formatters = {
                "Tags": lambda v: ", ".join(v["tags"]) or "-",
                "Verifier name": (lambda v: api.verifier.get(
                    verifier_id=v["verifier_uuid"])["name"]),
                "Deployment name": (lambda v: api.deployment.get(
                    deployment=v["deployment_uuid"])["name"]),
                "Started at": lambda v: v["created_at"],
                "Finished at": lambda v: v["updated_at"],
                "Duration": lambda v: (dt.datetime.strptime(v["updated_at"],
                                                            TIME_FORMAT) -
                                       dt.datetime.strptime(v["created_at"],
                                                            TIME_FORMAT))
            }
            cliutils.print_list(verifications, fields, formatters=formatters,
                                normalize_field_names=True, sortby_index=4)
        elif verifier_id or deployment or status or tags:
            print("There are no verifications that meet specified criteria.")
        else:
            print("There are no verifications. You can start verification, "
                  "using command `rally verify start`.")

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", nargs="+", dest="verification_uuid", type=str,
                   required=True,
                   help="UUIDs of verifications. " + LIST_VERIFICATIONS_HINT)
    def delete(self, api, verification_uuid):
        """Delete a verification or a few verifications."""

        if not isinstance(verification_uuid, list):
            verification_uuid = [verification_uuid]
        for v_uuid in verification_uuid:
            api.verification.delete(verification_uuid=v_uuid)

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", nargs="+", dest="verification_uuid", type=str,
                   help="UUIDs of verifications. " + LIST_VERIFICATIONS_HINT)
    @cliutils.args("--type", dest="output_type", type=str,
                   required=False, default="json",
                   help="Report type (Defaults to JSON). Out-of-the-box types:"
                        " %s. HINT: You can list all types, executing `rally "
                        "plugin list --plugin-base VerificationReporter` "
                        "command." % ", ".join(DEFAULT_REPORT_TYPES))
    @cliutils.args("--to", dest="output_dest", type=str,
                   metavar="<dest>", required=False,
                   help="Report destination. Can be a path to a file (in case "
                        "of HTML, JSON, etc. types) to save the report to or "
                        "a connection string. It depends on the report type.")
    @cliutils.args("--open", dest="open_it", action="store_true",
                   required=False, help="Open the output file in a browser.")
    @envutils.with_default_verification_uuid
    @plugins.ensure_plugins_are_loaded
    def report(self, api, verification_uuid=None, output_type=None,
               output_dest=None, open_it=None):
        """Generate a report for a verification or a few verifications."""

        if not isinstance(verification_uuid, list):
            verification_uuid = [verification_uuid]

        result = api.verification.report(uuids=verification_uuid,
                                         output_type=output_type,
                                         output_dest=output_dest)
        if "files" in result:
            print("Saving the report to '%s' file. It may take some time."
                  % output_dest)
            for path in result["files"]:
                full_path = os.path.abspath(os.path.expanduser(path))
                if not os.path.exists(os.path.dirname(full_path)):
                    os.makedirs(os.path.dirname(full_path))
                with open(full_path, "w") as f:
                    f.write(result["files"][path])
            print("The report has been successfully saved.")

            if open_it:
                if "open" not in result:
                    print("Cannot open '%s' report in the browser because "
                          "report type doesn't support it." % output_type)
                    return 1
                webbrowser.open_new_tab(
                    "file://" + os.path.abspath(result["open"]))

        if "print" in result:
            # NOTE(andreykurilin): we need a separation between logs and
            #   printed information to be able to parse output
            h = "Verification Report"
            print("\n%s\n%s" % (cliutils.make_header(h, len(h)),
                                result["print"]))

    @cliutils.help_group("verification")
    @cliutils.args("--id", dest="verifier_id", type=str, required=False,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>", required=False,
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--file", dest="file_to_parse", type=str, metavar="<path>",
                   required=True,
                   help="File to import test results from.")
    @cliutils.args("--run-args", dest="run_args", type=str, required=False,
                   help="Arguments that might be used when running tests. For "
                        "example, '{concurrency: 2, pattern: set=identity}'.")
    @cliutils.args("--no-use", dest="do_use", action="store_false",
                   help="Not to set the created verification as the default "
                        "verification for future operations.")
    @cliutils.alias("import")
    @envutils.with_default_deployment(cli_arg_name="deployment-id")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def import_results(self, api, verifier_id=None, deployment=None,
                       file_to_parse=None, run_args=None, do_use=True):
        """Import results of a test run into the Rally database."""

        if not os.path.exists(file_to_parse):
            print("File '%s' not found." % file_to_parse)
            return 1
        with open(file_to_parse, "r") as f:
            data = f.read()

        run_args = yaml.safe_load(run_args) if run_args else {}
        verification, results = api.verification.import_results(
            verifier_id=verifier_id, deployment_id=deployment,
            data=data, **run_args)
        self._print_totals(results["totals"])

        verification_uuid = verification["uuid"]
        if do_use:
            self.use(api, verification_uuid)
        else:
            print("Verification UUID: %s." % verification_uuid)
