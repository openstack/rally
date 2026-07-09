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

import configparser
import datetime as dt
import json
import os
import typing as t
import webbrowser

import typer

from rally import exceptions
from rally import plugins
from rally.api import API
from rally.cli import argutils
from rally.cli import cliutils
from rally.cli import envutils
from rally.cli import yamlutils as yaml
from rally.common import logging


TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

LIST_VERIFIERS_HINT = ("HINT: You can list all verifiers, executing "
                       "command `rally verify list-verifiers`.")
LIST_DEPLOYMENTS_HINT = ("HINT: You can list all deployments, executing "
                         "command `rally deployment list`.")
LIST_VERIFICATIONS_HINT = ("HINT: You can list all verifications, executing "
                           "command `rally verify list`.")

DEFAULT_REPORT_TYPES = ("HTML", "HTML-Static", "JSON", "JUnit-XML")

ACTIVE = u":-)"

verify_app = typer.Typer(
    name="verify", no_args_is_help=False,
    help="Verify an OpenStack cloud via a verifier.")


def _print_totals(totals: dict) -> None:
    print("\n======\n"
          "Totals"
          "\n======\n"
          "\nRan: %(tests_count)s tests in %(tests_duration)s sec.\n"
          " - Success: %(success)s\n"
          " - Skipped: %(skipped)s\n"
          " - Expected failures: %(expected_failures)s\n"
          " - Unexpected success: %(unexpected_success)s\n"
          " - Failures: %(failures)s\n" % totals)


def _print_failures(h_text: str, failures: list, symbol: str = "-") -> None:
    print("\n%s" % cliutils.make_header(
        h_text, size=len(h_text), symbol=symbol).strip())
    for f in failures:
        header = "%s\n%s\n" % (f["name"], "-" * len(f["name"]))
        failure = "\n%s%s\n" % (header, f["traceback"].strip())
        print(failure)


def _print_details_after_run(results: dict) -> None:
    failures = [t for t in results["tests"].values()
                if t["status"] == "fail"]
    if failures:
        h_text = "Failed %d %s - output below:" % (
            len(failures), "tests" if len(failures) > 1 else "test")
        _print_failures(h_text, failures, "=")
    else:
        print("\nCongratulations! "
              "Verification doesn't have failed tests ;)")


def _base_dir(uuid: str) -> str:
    return os.path.expanduser("~/.rally/verification/verifier-%s" % uuid)


def _get_location(uuid: str, loc: str) -> str:
    return os.path.join(_base_dir(uuid), loc)


def _use_verifier(api: API, verifier_id: str) -> None:
    verifier = api.verifier.get(verifier_id=verifier_id)
    envutils.update_globals_file(envutils.ENV_VERIFIER, verifier["uuid"])
    print("Using verifier '%s' (UUID=%s) as the default verifier "
          "for the future CLI operations."
          % (verifier["name"], verifier["uuid"]))


def _use(api: API, verification_uuid: str) -> None:
    verification = api.verification.get(verification_uuid=verification_uuid)
    envutils.update_globals_file(
        envutils.ENV_VERIFICATION, verification["uuid"])
    print("Using verification (UUID=%s) as the default verification "
          "for the future operations." % verification["uuid"])


@verify_app.command(name="list-plugins")
@plugins.ensure_plugins_are_loaded
def list_plugins(
    platform: t.Annotated[
        str | None,
        typer.Option(
            help="Required platform (e.g. openstack)."
        )
    ] = None,
) -> None:
    """List all plugins for verifiers management."""
    api = cliutils.get_api()
    if platform:
        platform = platform.lower()
    verifier_plugins = api.verifier.list_plugins(platform=platform)

    fields = ["Plugin name", "Platform", "Description"]
    if logging.is_debug():
        fields.append("Location")

    cliutils.print_list(verifier_plugins, fields,
                        formatters={"Plugin name": lambda p: p["name"]},
                        normalize_field_names=True)


@verify_app.command(name="create-verifier")
@plugins.ensure_plugins_are_loaded
def create_verifier(
    name: t.Annotated[
        str,
        typer.Option(
            help="Verifier name (for example, 'My verifier')."
        )
    ],
    vtype: t.Annotated[
        str,
        typer.Option(
            "--type",
            help="Verifier plugin name. HINT: You can list all verifier "
                 "plugins, executing command `rally verify list-plugins`."
        )
    ],
    platform: t.Annotated[
        str,
        typer.Option(
            help="Verifier plugin platform. Should be specified in case of "
                 "two verifier plugins with equal names but in different "
                 "platforms."
        )
    ] = "",
    source: t.Annotated[
        str | None,
        typer.Option(
            help="Path or URL to the repo to clone verifier from."
        )
    ] = None,
    version: t.Annotated[
        str | None,
        typer.Option(
            help="Branch, tag or commit ID to checkout before verifier "
                 "installation (the 'master' branch is used by default)."
        )
    ] = None,
    system_wide: t.Annotated[
        bool,
        typer.Option(
            "--system-wide",
            help="Use the system-wide environment for verifier instead of a "
                 "virtual environment."
        )
    ] = False,
    extra: t.Annotated[
        str | None,
        typer.Option(
            "--extra-settings",
            help="Extra installation settings for verifier."
        )
    ] = None,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Not to set the created verifier as the default verifier for "
                 "future operations."
        )
    ] = False,
) -> None:
    """Create a verifier."""
    api = cliutils.get_api()
    verifier_uuid = api.verifier.create(
        name=name, vtype=vtype, platform=platform, source=source,
        version=version, system_wide=system_wide, extra_settings=extra)

    if not no_use:
        _use_verifier(api, verifier_uuid)


@verify_app.command(name="use-verifier")
def use_verifier(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
) -> None:
    """Choose a verifier to use for the future operations."""
    _use_verifier(cliutils.get_api(), verifier_id)


@verify_app.command(name="list-verifiers")
@plugins.ensure_plugins_are_loaded
def list_verifiers(
    status: t.Annotated[
        str | None,
        typer.Option(
            help="Status to filter verifiers by."
        )
    ] = None,
) -> None:
    """List all verifiers."""
    api = cliutils.get_api()
    verifiers = api.verifier.list(status=status)
    if verifiers:
        fields = ["UUID", "Name", "Type", "Platform", "Created at",
                  "Updated at", "Status", "Version", "System-wide", "Active"]
        cv = envutils.get_global(envutils.ENV_VERIFIER)
        formatters = {
            "Created at": lambda v: v["created_at"],
            "Updated at": lambda v: v["updated_at"],
            "Active": lambda v: ACTIVE if v["uuid"] == cv else "",
        }
        cliutils.print_list(verifiers, fields, formatters=formatters,
                            normalize_field_names=True, sortby_index=4)
    elif status:
        print("There are no verifiers with status '%s'." % status)
    else:
        print("There are no verifiers. You can create verifier, using "
              "command `rally verify create-verifier`.")


@verify_app.command(name="show-verifier")
@plugins.ensure_plugins_are_loaded
def show_verifier(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
) -> None:
    """Show detailed information about a verifier."""
    api = cliutils.get_api()
    verifier = api.verifier.get(verifier_id=verifier_id)
    fields = ["UUID", "Status", "Created at", "Updated at", "Active",
              "Name", "Description", "Type", "Platform", "Source",
              "Version", "System-wide", "Extra settings", "Location",
              "Venv location"]
    used_verifier = envutils.get_global(envutils.ENV_VERIFIER)
    formatters = {
        "Created at": lambda v: v["created_at"].replace("T", " "),
        "Updated at": lambda v: v["updated_at"].replace("T", " "),
        "Active": lambda v: (ACTIVE if v["uuid"] == used_verifier else None),
        "Extra settings": lambda v: (json.dumps(v["extra_settings"], indent=4)
                                     if v["extra_settings"] else None),
        "Location": lambda v: _get_location((v["uuid"]), "repo")
    }
    if not verifier["system_wide"]:
        formatters["Venv location"] = lambda v: _get_location(
            v["uuid"], ".venv")
    cliutils.print_dict(verifier, fields=fields, formatters=formatters,
                        normalize_field_names=True, print_header=False,
                        table_label="Verifier")
    print("Attention! All you do in the verifier repository or verifier "
          "virtual environment, you do it at your own risk!")


@verify_app.command(name="delete-verifier")
@plugins.ensure_plugins_are_loaded
def delete_verifier(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    deployment: t.Annotated[
        str | None,
        typer.Option(
            "--deployment-id",
            help="Deployment name or UUID. If specified, only the "
                 "deployment-specific data will be deleted for verifier. "
                 + LIST_DEPLOYMENTS_HINT
        )
    ] = None,
    force: t.Annotated[
        bool,
        typer.Option(
            "--force",
            help="Delete all stored verifications of the specified verifier. "
                 "If a deployment specified, only verifications of this "
                 "deployment will be deleted. Use this argument carefully! "
                 "You can delete verifications that may be important to you."
        )
    ] = False,
) -> None:
    """Delete a verifier."""
    api = cliutils.get_api()
    api.verifier.delete(verifier_id=verifier_id, deployment_id=deployment,
                        force=force)


@verify_app.command(name="update-verifier")
@plugins.ensure_plugins_are_loaded
def update_verifier(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    update_venv: t.Annotated[
        bool,
        typer.Option(
            "--update-venv",
            help="Update the virtual environment for verifier."
        )
    ] = False,
    version: t.Annotated[
        str | None,
        typer.Option(
            help="Branch, tag or commit ID to checkout. HINT: Specify the "
                 "same version to pull the latest repo code."
        )
    ] = None,
    system_wide: t.Annotated[
        bool,
        typer.Option(
            "--system-wide",
            help="Switch to using the system-wide environment."
        )
    ] = False,
    no_system_wide: t.Annotated[
        bool,
        typer.Option(
            "--no-system-wide",
            help="Switch to using the virtual environment. If the virtual "
                 "environment doesn't exist, it will be created."
        )
    ] = False,
) -> None:
    """Update a verifier."""
    api = cliutils.get_api()
    if not (version or system_wide or no_system_wide or update_venv):
        print("At least one of the following arguments should be "
              "provided: '--update-venv', '--version', '--system-wide', "
              "'--no-system-wide'.")
        raise typer.Exit(code=1)

    msg = ("Arguments '--%s' and '--%s' cannot be used simultaneously. "
           "You can use only one of the mentioned arguments.")
    if update_venv and system_wide:
        print(msg % ("update-venv", "system-wide"))
        raise typer.Exit(code=1)
    if system_wide and no_system_wide:
        print(msg % ("system-wide", "no-system-wide"))
        raise typer.Exit(code=1)

    system_wide_value = False if no_system_wide else (system_wide or None)
    api.verifier.update(verifier_id=verifier_id,
                        system_wide=system_wide_value,
                        version=version,
                        update_venv=update_venv)

    print("HINT: In some cases the verifier config file should be "
          "updated as well. Use `rally verify configure-verifier` "
          "command to update the config file.")


@verify_app.command(name="configure-verifier")
@plugins.ensure_plugins_are_loaded
def configure_verifier(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            "--deployment-id",
            envvar=envutils.ENV_ENV,
            help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT
        )
    ],
    reconfigure: t.Annotated[
        bool,
        typer.Option(
            "--reconfigure",
            help="Reconfigure verifier."
        )
    ] = False,
    extra_options: t.Annotated[
        str | None,
        typer.Option(
            "--extend",
            help="Extend verifier configuration with extra options. If "
                 "options are already present, the given ones will override "
                 "them. Can be a path to a regular config file or just a "
                 "json/yaml."
        )
    ] = None,
    new_configuration: t.Annotated[
        str | None,
        typer.Option(
            "--override",
            help="Override verifier configuration by another one from a given "
                 "source."
        )
    ] = None,
    show: t.Annotated[
        bool,
        typer.Option(
            "--show",
            help="Show verifier configuration."
        )
    ] = False,
) -> None:
    """Configure a verifier for a specific deployment."""
    api = cliutils.get_api()
    # TODO(ylobankov): Add an ability to read extra options from
    #                  a json or yaml file.
    if new_configuration and (extra_options or reconfigure):
        print("Argument '--override' cannot be used with arguments "
              "'--reconfigure' and '--extend'.")
        raise typer.Exit(code=1)

    if new_configuration:
        if not os.path.exists(new_configuration):
            print("File '%s' not found." % new_configuration)
            raise typer.Exit(code=1)

        with open(new_configuration) as f:
            config = f.read()
        api.verifier.override_configuration(verifier_id=verifier_id,
                                            deployment_id=deployment,
                                            new_configuration=config)
    else:
        options: object = extra_options
        if extra_options:
            if os.path.isfile(extra_options):
                conf = configparser.ConfigParser()
                setattr(conf, "optionxform", str)
                conf.read(extra_options)
                options = dict(conf._sections)  # type: ignore[attr-defined]
                for s in options:
                    options[s] = dict(options[s])
                    options[s].pop("__name__", None)

                defaults = dict(conf.defaults())
                if defaults:
                    options["DEFAULT"] = dict(conf.defaults())
            else:
                options = yaml.safe_load(extra_options)

        config = api.verifier.configure(verifier=verifier_id,
                                        deployment_id=deployment,
                                        extra_options=options,
                                        reconfigure=reconfigure)

    if show:
        print("\n%s\n" % config.strip())


@verify_app.command(name="list-verifier-tests")
@plugins.ensure_plugins_are_loaded
def list_verifier_tests(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    pattern: t.Annotated[
        str,
        typer.Option(
            help="Pattern which will be used for matching. Can be a regexp or "
                 "a verifier-specific entity (for example, in case of Tempest "
                 "you can specify 'set=smoke')."
        )
    ] = "",
) -> None:
    """List all verifier tests."""
    api = cliutils.get_api()
    tests = api.verifier.list_tests(verifier_id=verifier_id, pattern=pattern)
    if tests:
        for test in tests:
            print(test)
    else:
        print("No tests found.")


@verify_app.command(name="add-verifier-ext")
@plugins.ensure_plugins_are_loaded
def add_verifier_ext(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    source: t.Annotated[
        str,
        typer.Option(
            help="Path or URL to the repo to clone verifier extension from."
        )
    ],
    version: t.Annotated[
        str | None,
        typer.Option(
            help="Branch, tag or commit ID to checkout before installation of "
                 "the verifier extension (the 'master' branch is used by "
                 "default)."
        )
    ] = None,
    extra: t.Annotated[
        str | None,
        typer.Option(
            "--extra-settings",
            help="Extra installation settings for verifier extension."
        )
    ] = None,
) -> None:
    """Add a verifier extension."""
    api = cliutils.get_api()
    api.verifier.add_extension(verifier_id=verifier_id, source=source,
                               version=version, extra_settings=extra)


@verify_app.command(name="list-verifier-exts")
@plugins.ensure_plugins_are_loaded
def list_verifier_exts(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
) -> None:
    """List all verifier extensions."""
    api = cliutils.get_api()
    verifier_exts = api.verifier.list_extensions(verifier_id=verifier_id)
    if verifier_exts:
        fields = ["Name", "Entry point"]
        if logging.is_debug():
            fields.append("Location")
        cliutils.print_list(verifier_exts, fields, normalize_field_names=True)
    else:
        print("There are no verifier extensions. You can add verifier "
              "extension, using command `rally verify add-verifier-ext`.")


@verify_app.command(name="delete-verifier-ext")
@plugins.ensure_plugins_are_loaded
def delete_verifier_ext(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    name: t.Annotated[
        str,
        typer.Option(
            help="Verifier extension name."
        )
    ],
) -> None:
    """Delete a verifier extension."""
    api = cliutils.get_api()
    api.verifier.delete_extension(verifier_id=verifier_id, name=name)


@verify_app.command(name="start")
@plugins.ensure_plugins_are_loaded
def start(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            "--deployment-id",
            envvar=envutils.ENV_ENV,
            help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT
        )
    ],
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Mark verification with a tag or a few tags."
        )
    ] = None,
    pattern: t.Annotated[
        str | None,
        typer.Option(
            help="Pattern which will be used for running tests. Can be a "
                 "regexp or a verifier-specific entity (for example, in case "
                 "of Tempest you can specify 'set=smoke')."
        )
    ] = None,
    concur: t.Annotated[
        int,
        typer.Option(
            "--concurrency",
            help="How many processes to be used for running verifier tests. "
                 "The default value (0) auto-detects your CPU count."
        )
    ] = 0,
    load_list: t.Annotated[
        str | None,
        typer.Option(
            help="Path to a file with a list of tests to run."
        )
    ] = None,
    skip_list: t.Annotated[
        str | None,
        typer.Option(
            help="Path to a file with a list of tests to skip. Format: json "
                 "or yaml like a dictionary where keys are regexes matching "
                 "test names and values are reasons."
        )
    ] = None,
    xfail_list: t.Annotated[
        str | None,
        typer.Option(
            help="Path to a file with a list of tests that will be considered "
                 "as expected failures. Format: json or yaml like a "
                 "dictionary where keys are test names and values are reasons."
        )
    ] = None,
    detailed: t.Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show verification details such as errors of failed tests."
        )
    ] = False,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Not to set the finished verification as the default "
                 "verification for future operations."
        )
    ] = False,
) -> None:
    """Start a verification (run verifier tests)."""
    api = cliutils.get_api()
    if pattern and load_list:
        print("Arguments '--pattern' and '--load-list' cannot be used "
              "together, use only one of them.")
        raise typer.Exit(code=1)

    def parse(filename: str) -> t.Any:
        with open(filename, "r") as f:
            return yaml.safe_load(f.read())

    load_list_data = None
    if load_list:
        if not os.path.exists(load_list):
            print("File '%s' not found." % load_list)
            raise typer.Exit(code=1)
        with open(load_list, "r") as f:
            load_list_data = [test for test in f.read().split("\n") if test]

    skip_list_data = None
    if skip_list:
        if not os.path.exists(skip_list):
            print("File '%s' not found." % skip_list)
            raise typer.Exit(code=1)
        skip_list_data = parse(skip_list)

    xfail_list_data = None
    if xfail_list:
        if not os.path.exists(xfail_list):
            print("File '%s' not found." % xfail_list)
            raise typer.Exit(code=1)
        xfail_list_data = parse(xfail_list)

    run_args = {key: value for key, value in (
        ("pattern", pattern), ("load_list", load_list_data),
        ("skip_list", skip_list_data), ("xfail_list", xfail_list_data),
        ("concurrency", concur)) if value}

    try:
        results = api.verification.start(
            verifier_id=verifier_id, deployment_id=deployment,
            tags=tags, **run_args)
        verification_uuid = results["verification"]["uuid"]
    except exceptions.DeploymentNotFinishedStatus as e:
        print("Cannot start a verification against unfinished deployment: "
              " %s" % e)
        raise typer.Exit(code=1)

    if detailed:
        _print_details_after_run(results)

    _print_totals(results["totals"])

    if not no_use:
        _use(api, verification_uuid)
    else:
        print("Verification UUID: %s." % verification_uuid)

    if results["totals"]["unexpected_success"] > 0:
        raise typer.Exit(code=2)
    if results["totals"]["failures"] > 0:
        raise typer.Exit(code=3)


@verify_app.command(name="use")
def use(
    verification_uuid: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            help="Verification UUID. " + LIST_VERIFICATIONS_HINT
        )
    ],
) -> None:
    """Choose a verification to use for the future operations."""
    _use(cliutils.get_api(), verification_uuid)


@verify_app.command(name="rerun")
@plugins.ensure_plugins_are_loaded
def rerun(
    verification_uuid: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_VERIFICATION,
            help="Verification UUID. " + LIST_VERIFICATIONS_HINT
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            "--deployment-id",
            envvar=envutils.ENV_ENV,
            help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT
        )
    ],
    failed: t.Annotated[
        bool,
        typer.Option(
            "--failed",
            help="Rerun only failed tests."
        )
    ] = False,
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Mark verification with a tag or a few tags."
        )
    ] = None,
    concur: t.Annotated[
        int | None,
        typer.Option(
            "--concurrency",
            help="How many processes to be used for running verifier tests. "
                 "The default value (0) auto-detects your CPU count."
        )
    ] = None,
    detailed: t.Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show verification details such as errors of failed tests."
        )
    ] = False,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Not to set the finished verification as the default "
                 "verification for future operations."
        )
    ] = False,
) -> None:
    """Rerun tests from a verification for a specific deployment."""
    api = cliutils.get_api()
    results = api.verification.rerun(verification_uuid=verification_uuid,
                                     deployment_id=deployment,
                                     failed=failed,
                                     tags=tags,
                                     concurrency=concur)
    if detailed:
        _print_details_after_run(results)

    _print_totals(results["totals"])

    if not no_use:
        _use(api, results["verification"]["uuid"])
    else:
        print("Verification UUID: %s." % results["verification"]["uuid"])


@verify_app.command(name="show")
def show(
    verification_uuid: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_VERIFICATION,
            help="Verification UUID. " + LIST_VERIFICATIONS_HINT
        )
    ],
    sort_by: t.Annotated[
        t.Literal["name", "duration", "status"],
        typer.Option(
            "--sort-by",
            help="Sort tests by 'name', 'duration' or 'status'."
        )
    ] = "name",
    detailed: t.Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show verification details such as run arguments and errors "
                 "of failed tests."
        )
    ] = False,
) -> None:
    """Show detailed information about a verification."""
    api = cliutils.get_api()
    verification = api.verification.get(verification_uuid=verification_uuid)
    verifier = api.verifier.get(verifier_id=verification["verifier_uuid"])
    deployment = api.deployment.get(
        deployment=verification["deployment_uuid"])

    def run_args_formatter(v: dict) -> str:
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
        "Duration": lambda v: (
            dt.datetime.strptime(v["updated_at"], TIME_FORMAT)
            - dt.datetime.strptime(v["created_at"], TIME_FORMAT)),
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
            _print_failures("Failures", failures)
        else:
            print("\nCongratulations! Verification passed all tests ;)")


@verify_app.command(name="list")
def list_(
    verifier_id: t.Annotated[
        str | None,
        typer.Option(
            "--id",
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ] = None,
    deployment: t.Annotated[
        str | None,
        typer.Option(
            "--deployment-id",
            help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT
        )
    ] = None,
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Tags to filter verifications by."
        )
    ] = None,
    status: t.Annotated[
        str | None,
        typer.Option(
            help="Status to filter verifications by."
        )
    ] = None,
) -> None:
    """List all verifications."""
    api = cliutils.get_api()
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
            "Duration": lambda v:
            (dt.datetime.strptime(v["updated_at"], TIME_FORMAT)
             - dt.datetime.strptime(v["created_at"], TIME_FORMAT))
        }
        cliutils.print_list(verifications, fields, formatters=formatters,
                            normalize_field_names=True, sortby_index=4)
    elif verifier_id or deployment or status or tags:
        print("There are no verifications that meet specified criteria.")
    else:
        print("There are no verifications. You can start verification, "
              "using command `rally verify start`.")


@verify_app.command(name="delete")
def delete(
    verification_uuid: t.Annotated[
        list[str],
        argutils.ArgumentOrKeyword(
            "--uuid",
            help="UUIDs of verifications. " + LIST_VERIFICATIONS_HINT
        )
    ],
) -> None:
    """Delete a verification or a few verifications."""
    api = cliutils.get_api()
    for v_uuid in verification_uuid:
        api.verification.delete(verification_uuid=v_uuid)


@verify_app.command(name="report")
@plugins.ensure_plugins_are_loaded
def report(
    verification_uuid: t.Annotated[
        list[str],
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_VERIFICATION,
            help="UUIDs of verifications. " + LIST_VERIFICATIONS_HINT
        )
    ],
    output_type: t.Annotated[
        str,
        typer.Option(
            "--type",
            help="Report type (Defaults to JSON). Out-of-the-box types: %s. "
                 "HINT: You can list all types, executing `rally plugin list "
                 "--plugin-base VerificationReporter` command."
                 % ", ".join(DEFAULT_REPORT_TYPES)
        )
    ] = "json",
    output_dest: t.Annotated[
        str | None,
        typer.Option(
            "--to",
            help="Report destination. Can be a path to a file (in case of "
                 "HTML, JSON, etc. types) to save the report to or a "
                 "connection string. It depends on the report type."
        )
    ] = None,
    open_it: t.Annotated[
        bool,
        typer.Option(
            "--open",
            help="Open the output file in a browser."
        )
    ] = False,
) -> None:
    """Generate a report for a verification or a few verifications."""
    api = cliutils.get_api()
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
                raise typer.Exit(code=1)
            webbrowser.open_new_tab(
                "file://" + os.path.abspath(result["open"]))

    if "print" in result:
        # NOTE(andreykurilin): we need a separation between logs and
        #   printed information to be able to parse output
        h = "Verification Report"
        print("\n%s\n%s" % (cliutils.make_header(h, len(h)), result["print"]))


@verify_app.command(name="import")
@plugins.ensure_plugins_are_loaded
def import_results(
    verifier_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--id",
            envvar=envutils.ENV_VERIFIER,
            help="Verifier name or UUID. " + LIST_VERIFIERS_HINT
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            "--deployment-id",
            envvar=envutils.ENV_ENV,
            help="Deployment name or UUID. " + LIST_DEPLOYMENTS_HINT
        )
    ],
    file_to_parse: t.Annotated[
        str,
        typer.Option(
            "--file",
            help="File to import test results from."
        )
    ],
    run_args: t.Annotated[
        str | None,
        typer.Option(
            help="Arguments that might be used when running tests. For "
                 "example, '{concurrency: 2, pattern: set=identity}'."
        )
    ] = None,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Not to set the created verification as the default "
                 "verification for future operations."
        )
    ] = False,
) -> None:
    """Import results of a test run into the Rally database."""
    api = cliutils.get_api()
    if not os.path.exists(file_to_parse):
        print("File '%s' not found." % file_to_parse)
        raise typer.Exit(code=1)
    with open(file_to_parse, "r") as f:
        data = f.read()

    parsed_run_args = yaml.safe_load(run_args) if run_args else {}
    verification, results = api.verification.import_results(
        verifier_id=verifier_id, deployment_id=deployment,
        data=data, **parsed_run_args)
    _print_totals(results["totals"])

    verification_uuid = verification["uuid"]
    if not no_use:
        _use(api, verification_uuid)
    else:
        print("Verification UUID: %s." % verification_uuid)
