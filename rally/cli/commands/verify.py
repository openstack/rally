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

import json
import os
import webbrowser

from six.moves import configparser
import yaml

from rally.cli import cliutils
from rally.cli import envutils
from rally.common import fileutils
from rally.common.i18n import _
from rally.common import logging
from rally import plugins


LIST_VERIFIERS_HINT = ("HINT: You can list all verifiers, executing "
                       "command `rally verify list-verifiers`.")
LIST_DEPLOYMENTS_HINT = ("HINT: You can list all deployments, executing "
                         "command `rally deployment list`.")
LIST_VERIFICATIONS_HINT = ("HINT: You can list all verifications, executing "
                           "command `rally verify list`.")


class VerifyCommands(object):
    """Verify an OpenStack cloud via a verifier."""

    @staticmethod
    def _print_totals(totals):
        print("\n======\n"
              "Totals"
              "\n======\n"
              "Ran: %(tests_count)s tests in %(tests_duration)s sec.\n"
              " - Success: %(success)s\n"
              " - Skipped: %(skipped)s\n"
              " - Expected failures: %(expected_failures)s\n"
              " - Unexpected success: %(unexpected_success)s\n"
              " - Failures: %(failures)s\n" % totals)

    @cliutils.args("--namespace", dest="namespace", type=str, metavar="<name>",
                   required=False,
                   help="Namespace name (for example, openstack).")
    @plugins.ensure_plugins_are_loaded
    def list_plugins(self, api, namespace=None):
        """List all plugins for verifiers management."""
        if namespace:
            namespace = namespace.lower()
        verifier_plugins = api.verifier.list_plugins(namespace)

        fields = ["Plugin name", "Namespace", "Description"]
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
    @cliutils.args("--namespace", dest="namespace", type=str, metavar="<name>",
                   required=False,
                   help="Verifier plugin namespace. Should be specified in "
                        "case of two verifier plugins with equal names but "
                        "in different namespaces.")
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
    def create_verifier(self, api, name, vtype, namespace="openstack",
                        source=None, version="master", system_wide=False,
                        extra=None, do_use=True):
        """Create a verifier."""
        verifier_uuid = api.verifier.create(
            name, vtype=vtype, namespace=namespace, source=source,
            version=version, system_wide=system_wide, extra_settings=extra)

        if do_use:
            self.use_verifier(api, verifier_uuid)

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str, required=True,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    def use_verifier(self, api, verifier_id):
        """Choose a verifier to use for the future operations."""
        verifier = api.verifier.get(verifier_id)
        fileutils.update_globals_file(envutils.ENV_VERIFIER, verifier.uuid)
        print(_("Using verifier '%s' (UUID=%s) as the default verifier "
                "for the future operations.") % (verifier.name, verifier.uuid))

    @cliutils.help_group("verifier")
    @cliutils.args("--status", dest="status", type=str, required=False,
                   help="Status to filter verifiers by.")
    @plugins.ensure_plugins_are_loaded
    def list_verifiers(self, api, status=None):
        """List all verifiers."""
        verifiers = api.verifier.list(status)
        if verifiers:
            fields = ["UUID", "Name", "Type", "Namespace", "Created at",
                      "Status", "Version", "System-wide", "Active"]
            if logging.is_debug():
                fields.append("Location")
            cv = envutils.get_global(envutils.ENV_VERIFIER)
            formatters = {
                "Created at": lambda v: v.created_at.replace(microsecond=0),
                "Active": lambda v: u"\u2714" if v.uuid == cv else "",
                "Location": lambda v: v.manager.repo_dir
            }
            cliutils.print_list(verifiers, fields, formatters=formatters,
                                normalize_field_names=True, sortby_index=4)
        else:
            print(_("There are no verifiers. You can create verifier, using "
                    "command `rally verify create-verifier`."))

    @cliutils.help_group("verifier")
    @cliutils.args("--verifier-id", dest="verifier_id", type=str,
                   metavar="<id>",
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>", required=False,
                   help="Deployment name or UUID. If specified, only "
                        "deployment-specific data will be deleted for "
                        "verifier. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--force", dest="force", action="store_true",
                   required=False,
                   help="Delete all stored verifications of the specified "
                        "verifier. If deployment specified, only verifications"
                        " of this deployment will be deleted. Use this "
                        "argument carefully! You can delete verifications "
                        "that may be important to you.")
    @envutils.with_default_verifier_id(cli_arg_name="verifier-id")
    @plugins.ensure_plugins_are_loaded
    def delete_verifier(self, api, verifier_id=None, deployment=None,
                        force=False):
        """Delete a verifier."""
        api.verifier.delete(verifier_id, deployment, force)

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
            print(_("At least one of the following arguments should be "
                    "provided: '--update-venv', '--version', '--system-wide', "
                    "'--no-system-wide'."))
            return 1

        msg = _("Arguments '--%s' and '--%s' cannot be used simultaneously. "
                "You can use only one of the mentioned arguments.")
        if update_venv and system_wide:
            print(msg % ("update-venv", "system-wide"))
            return 1
        if system_wide and no_system_wide:
            print(msg % ("system-wide", "no-system-wide"))
            return 1

        system_wide = False if no_system_wide else (system_wide or None)
        api.verifier.update(verifier_id, system_wide=system_wide,
                            version=version, update_venv=update_venv)

        print(_("HINT: In some cases the verifier config file should be "
                "updated as well. Use `rally verify configure-verifier` "
                "command to update the config file."))

    @cliutils.help_group("verifier")
    @cliutils.args("--verifier-id", dest="verifier_id", type=str,
                   metavar="<id>",
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>",
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--recreate", dest="recreate", action="store_true",
                   required=False, help="Recreate the verifier config file.")
    @cliutils.args("--add-options", dest="extra_options", type=str,
                   metavar="<path/json/yaml>", required=False,
                   help="Add options to the verifier config file. If options "
                        "are already present in the verifier config file, the "
                        "given ones will override them. Can be a path to a "
                        "regular config file or just a json/yaml.")
    @cliutils.args("--replace-by", dest="replace", type=str, metavar="<path>",
                   required=False,
                   help="Replace the verifier config file by another one "
                        "from a given source.")
    @cliutils.args("--show", dest="show", action="store_true", required=False,
                   help="Show the verifier config file.")
    @envutils.with_default_deployment(cli_arg_name="deployment-id")
    @envutils.with_default_verifier_id(cli_arg_name="verifier-id")
    @plugins.ensure_plugins_are_loaded
    def configure_verifier(self, api, verifier_id=None, deployment=None,
                           recreate=False, extra_options=None, replace=None,
                           show=False):
        """Configure a verifier for a specific deployment."""

        # TODO(ylobankov): Add an ability to read extra options from
        #                  a json or yaml file.

        if replace and (extra_options or recreate):
            print(_("Argument '--replace-by' cannot be used with arguments "
                    "'--recreate' and '--add-options'."))
            return 1

        if replace:
            if not os.path.exists(replace):
                print(_("File '%s' not found.") % replace)
                return 1

            with open(replace, "r") as f:
                config = f.read()
            api.verifier.override_configuration(verifier_id,
                                                deployment, config)
        else:
            if extra_options:
                if os.path.isfile(extra_options):
                    print(extra_options)
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

            config = api.verifier.configure(verifier_id, deployment,
                                            extra_options=extra_options,
                                            recreate=recreate)

        if show:
            print("\n" + config.strip() + "\n")

    @cliutils.help_group("verifier")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--pattern", dest="pattern", type=str, required=False,
                   help="Pattern which will be used for matching. Can be a "
                        "regexp or a verifier-specific entity (for example, "
                        "in case of Tempest you can specify 'set=smoke'.")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def list_verifier_tests(self, api, verifier_id=None, pattern=""):
        """Show all verifier tests."""
        tests = api.verifier.list_tests(verifier_id, pattern)
        if tests:
            for test in tests:
                print(test)
        else:
            print(_("No tests found."))

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
        api.verifier.add_extension(verifier_id, source=source, version=version,
                                   extra_settings=extra)

    @cliutils.help_group("verifier-ext")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def list_verifier_exts(self, api, verifier_id=None):
        """List all verifier extensions."""
        verifier_exts = api.verifier.list_extensions(verifier_id)
        if verifier_exts:
            fields = ["Name", "Entry point"]
            if logging.is_debug():
                fields.append("Location")
            cliutils.print_list(verifier_exts, fields,
                                normalize_field_names=True)
        else:
            print(_("There are no verifier extensions. You can add "
                    "verifier extension, using command `rally verify "
                    "add-verifier-ext`."))

    @cliutils.help_group("verifier-ext")
    @cliutils.args("--id", dest="verifier_id", type=str,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--name", type=str, required=True,
                   help="Verifier extension name.")
    @envutils.with_default_verifier_id()
    @plugins.ensure_plugins_are_loaded
    def delete_verifier_ext(self, api, verifier_id=None, name=None):
        """Delete a verifier extension."""
        api.verifier.delete_extension(verifier_id, name)

    @cliutils.help_group("verification")
    @cliutils.args("--verifier-id", dest="verifier_id", type=str,
                   metavar="<id>",
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>",
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--pattern", dest="pattern", type=str, required=False,
                   help="Pattern which will be used for running tests. Can be "
                        "a regexp or a verifier-specific entity (for example, "
                        "in case of Tempest you can specify 'set=smoke'.")
    @cliutils.args("--concurrency", dest="concur", type=int, metavar="<N>",
                   required=False,
                   help="How many processes to use to run verifier tests. "
                        "The default value (0) auto-detects your CPU count.")
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
    @cliutils.args("--failed", dest="failed", required=False,
                   help="Re-run tests that failed in the last verification.",
                   action="store_true")
    @cliutils.args("--no-use", dest="do_use", action="store_false",
                   help="Not to set the finished verification as the default "
                        "verification for future operations.")
    @envutils.with_default_deployment(cli_arg_name="deployment-id")
    @envutils.with_default_verifier_id(cli_arg_name="verifier-id")
    @plugins.ensure_plugins_are_loaded
    def start(self, api, verifier_id=None, deployment=None, pattern=None,
              concur=0, load_list=None, skip_list=None, xfail_list=None,
              failed=False, do_use=True):
        """Start a verification (run verifier tests)."""
        incompatible_args_map = [{"load-list": load_list, "pattern": pattern},
                                 {"failed": failed, "pattern": pattern},
                                 {"failed": failed, "load-list": load_list},
                                 {"failed": failed, "skip-list": skip_list}]
        msg = _("Arguments '--%s' and '--%s' cannot be used simultaneously. "
                "You can use only one of the mentioned arguments.")
        for args in incompatible_args_map:
            args_keys = list(args)
            if args[args_keys[0]] and args[args_keys[1]]:
                print(msg % (args_keys[0], args_keys[1]))
                return 1

        def parse(filename):
            with open(filename, "r") as f:
                return yaml.safe_load(f.read())

        if load_list:
            if not os.path.exists(load_list):
                print(_("File '%s' not found.") % load_list)
                return 1
            with open(load_list, "r") as f:
                load_list = [test for test in f.read().split("\n") if test]

        if skip_list:
            if not os.path.exists(skip_list):
                print(_("File '%s' not found.") % skip_list)
                return 1
            skip_list = parse(skip_list)

        if xfail_list:
            if not os.path.exists(xfail_list):
                print(_("File '%s' not found.") % xfail_list)
                return 1
            xfail_list = parse(xfail_list)

        run_args = {key: value for key, value in (
            ("pattern", pattern), ("load_list", load_list),
            ("skip_list", skip_list), ("xfail_list", xfail_list),
            ("concurrency", concur), ("failed", failed)) if value}

        verification, results = api.verification.start(verifier_id, deployment,
                                                       **run_args)
        self._print_totals(results.totals)

        if do_use:
            self.use(api, verification.uuid)
        else:
            print(_("Verification UUID: %s.") % verification.uuid)

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", dest="verification_uuid", type=str, required=True,
                   help="Verification UUID. " + LIST_VERIFICATIONS_HINT)
    def use(self, api, verification_uuid):
        """Choose a verification to use for the future operations."""
        verification = api.verification.get(verification_uuid)
        fileutils.update_globals_file(
            envutils.ENV_VERIFICATION, verification.uuid)
        print(_("Using verification (UUID=%s) as the default verification "
                "for the future operations.") % verification.uuid)

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
        """Show a verification."""
        verification = api.verification.get(verification_uuid)

        # Main Table
        def run_args_formatter(v):
            run_args = []
            for k in sorted(v.run_args):
                if k in ("load_list", "skip_list", "xfail_list"):
                    value = "(value is too long, %s)"
                    if detailed:
                        value %= "will be displayed separately"
                    else:
                        value %= "use 'detailed' flag to display it"
                else:
                    value = v.run_args[k]
                run_args.append("%s: %s" % (k, value))
            return "\n".join(run_args)

        formatters = {
            "Verifier name": lambda v: verifier.name,
            "Verifier type": (
                lambda v: "%s (namespace: %s)" % (verifier.type,
                                                  verifier.namespace)),
            "Deployment name": (
                lambda v: api.deployment.get(v.deployment_uuid)["name"]),
            "Started at": lambda v: v.created_at.replace(microsecond=0),
            "Finished at": lambda v: v.updated_at.replace(microsecond=0),
            "Duration": lambda v: (v.updated_at.replace(microsecond=0) -
                                   v.created_at.replace(microsecond=0)),
            "Run arguments": run_args_formatter,
            "Tests duration, sec": lambda v: v.tests_duration
        }
        fields = ["UUID", "Verifier name", "Verifier type", "Deployment name",
                  "Started at", "Finished at", "Duration", "Run arguments",
                  "Tests count", "Tests duration, sec", "Success", "Skipped",
                  "Expected failures", "Unexpected success", "Failures",
                  "Status"]
        verifier = api.verifier.get(verification.verifier_uuid)
        cliutils.print_dict(verification, fields, formatters=formatters,
                            normalize_field_names=True, print_header=False,
                            table_label="Verification")

        if detailed:
            print(_("\nRun arguments:"))
            print(json.dumps(verification.run_args, indent=4))

        # Tests
        print("\n")
        tests = verification.tests
        values = [tests[test_id] for test_id in tests]
        fields = ["Name", "Duration, sec", "Status"]
        formatters = {"Duration, sec": lambda v: v["duration"]}
        index = ("name", "duration", "status").index(sort_by)
        cliutils.print_list(values, fields, formatters=formatters,
                            table_label="Tests", normalize_field_names=True,
                            sortby_index=index)

        if detailed:
            # Tracebacks
            failures = [t for t in tests.values() if t["status"] == "fail"]
            if failures:
                print(_("\nFailures:"))
                for t in failures:
                    header = cliutils.make_header("FAIL: %s" % t["name"])
                    formatted_test = "%s\n" % (header + t["traceback"].strip())
                    print(formatted_test)

    @cliutils.help_group("verification")
    @cliutils.args("--verifier-id", dest="verifier_id", type=str,
                   metavar="<id>", required=False,
                   help="Verifier name or UUID. " + LIST_VERIFIERS_HINT)
    @cliutils.args("--deployment-id", dest="deployment", type=str,
                   metavar="<id>", required=False,
                   help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT)
    @cliutils.args("--status", dest="status", type=str, required=False,
                   help="Status to filter verifications by.")
    def list(self, api, verifier_id=None, deployment=None, status=None):
        """List all verifications."""
        verifications = api.verification.list(verifier_id, deployment, status)
        if verifications:
            fields = ["UUID", "Verifier name", "Deployment name", "Started at",
                      "Finished at", "Duration", "Status"]
            formatters = {
                "Verifier name": (
                    lambda v: api.verifier.get(v.verifier_uuid).name),
                "Deployment name": (
                    lambda v: api.deployment.get(v.deployment_uuid)["name"]),
                "Started at": lambda v: v.created_at.replace(microsecond=0),
                "Finished at": lambda v: v.updated_at.replace(microsecond=0),
                "Duration": lambda v: (v.updated_at.replace(microsecond=0) -
                                       v.created_at.replace(microsecond=0))
            }
            cliutils.print_list(verifications, fields, formatters=formatters,
                                normalize_field_names=True, sortby_index=3)
        else:
            print(_("There are no verifications. You can start verification, "
                    "using command `rally verify start`."))

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", nargs="+", dest="verification_uuid", type=str,
                   help="UUIDs of verifications. HINT: You can list all "
                        "verifications, executing command `rally verify "
                        "list`")
    @envutils.with_default_verification_uuid
    def delete(self, api, verification_uuid=None):
        """Delete a verification or a few verifications."""
        if not isinstance(verification_uuid, list):
            verification_uuid = [verification_uuid]
        for v_uuid in verification_uuid:
            api.verification.delete(v_uuid)

    @cliutils.help_group("verification")
    @cliutils.args("--uuid", nargs="+", dest="verification_uuid", type=str,
                   help="UUIDs of verifications. " + LIST_VERIFICATIONS_HINT)
    @cliutils.args("--html", dest="html", action="store_true", required=False,
                   help="Generate the report in HTML format instead of JSON.")
    @cliutils.args("--file", dest="output_file", type=str,
                   metavar="<path>", required=False,
                   help="Path to a file to save the report to.")
    @cliutils.args("--open", dest="open_it", action="store_true",
                   required=False, help="Open the output file in a browser.")
    @envutils.with_default_verification_uuid
    def report(self, api, verification_uuid=None, html=False, output_file=None,
               open_it=False):
        """Generate a report for a verification or a few verifications."""

        # TODO(ylobankov): Add support for CSV format.

        if not isinstance(verification_uuid, list):
            verification_uuid = [verification_uuid]
        raw_report = api.verification.report(verification_uuid, html)

        if output_file:
            with open(output_file, "w") as f:
                f.write(raw_report)
            if open_it:
                webbrowser.open_new_tab(
                    "file://" + os.path.realpath(output_file))
        else:
            print(raw_report)

    @cliutils.help_group("verification")
    @cliutils.args("--verifier-id", dest="verifier_id", type=str,
                   metavar="<id>", required=False,
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
    @envutils.with_default_verifier_id(cli_arg_name="verifier-id")
    @plugins.ensure_plugins_are_loaded
    def import_results(self, api, verifier_id=None, deployment=None,
                       file_to_parse=None, run_args=None, do_use=True):
        """Import results of a test run into the Rally database."""
        if not os.path.exists(file_to_parse):
            print(_("File '%s' not found.") % file_to_parse)
            return 1
        with open(file_to_parse, "r") as f:
            data = f.read()

        run_args = yaml.safe_load(run_args) if run_args else {}
        verification, results = api.verification.import_results(
            verifier_id, deployment, data, **run_args)
        self._print_totals(results.totals)

        if do_use:
            self.use(verification.uuid)
        else:
            print(_("Verification UUID: %s.") % verification.uuid)
