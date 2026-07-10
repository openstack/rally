# Copyright 2013: Mirantis Inc.
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

"""Rally command: deployment"""

import json
import os
import sys
import typing as t

import jsonschema
import typer

from rally import exceptions
from rally import plugins
from rally.api import API
from rally.cli import argutils
from rally.cli import cliutils
from rally.cli import envutils
from rally.cli import yamlutils as yaml
from rally.common import logging
from rally.common import utils
from rally.env import env_mgr


deployment_app = typer.Typer(
    name="deployment", no_args_is_help=False,
    help="Set of commands that allow you to manage deployments.")


def _list_deployments(api: API,
                      deployment_list: list | None = None) -> None:
    headers = ["uuid", "created_at", "name", "status", "active"]
    current_deployment = envutils.get_global("RALLY_DEPLOYMENT")
    deployment_list = deployment_list or api.deployment.list()

    table_rows = []
    if deployment_list:
        for dep in deployment_list:
            r = [str(dep[column]) for column in headers[:-1]]
            r.append("" if dep["uuid"] != current_deployment else "*")
            table_rows.append(utils.Struct(**dict(zip(headers, r))))
        cliutils.print_list(table_rows, headers,
                            sortby_index=headers.index("created_at"))
    else:
        print("There are no deployments. To create a new deployment, use:"
              "\nrally deployment create")


def _update_openrc_deployment_file(deployment: str, credential: dict) -> None:
    openrc_path = os.path.expanduser("~/.rally/openrc-%s" % deployment)
    with open(openrc_path, "w+") as env_file:
        env_file.write("export OS_AUTH_URL='%(auth_url)s'\n"
                       "export OS_USERNAME='%(username)s'\n"
                       "export OS_PASSWORD='%(password)s'\n"
                       "export OS_TENANT_NAME='%(tenant_name)s'\n"
                       "export OS_PROJECT_NAME='%(tenant_name)s'\n"
                       % credential)
        if credential.get("region_name"):
            env_file.write("export OS_REGION_NAME='%s'\n" %
                           credential["region_name"])
        if credential.get("endpoint_type"):
            env_file.write("export OS_ENDPOINT_TYPE='%sURL'\n" %
                           credential["endpoint_type"])
            env_file.write("export OS_INTERFACE='%s'\n" %
                           credential["endpoint_type"])
        if credential.get("endpoint"):
            env_file.write("export OS_ENDPOINT='%s'\n" %
                           credential["endpoint"])
        if credential.get("https_cacert"):
            env_file.write("export OS_CACERT='%s'\n" %
                           credential["https_cacert"])
        if credential.get("project_domain_name"):
            env_file.write("export OS_IDENTITY_API_VERSION=3\n"
                           "export OS_USER_DOMAIN_NAME='%s'\n"
                           "export OS_PROJECT_DOMAIN_NAME='%s'\n" %
                           (credential["user_domain_name"],
                            credential["project_domain_name"]))
    expanded_path = os.path.expanduser("~/.rally/openrc")
    if os.path.exists(expanded_path):
        os.remove(expanded_path)
    os.symlink(openrc_path, expanded_path)


def _use(api: API, deployment: t.Any) -> int | None:
    # TODO(astudenov): make this method platform independent
    try:
        if not isinstance(deployment, dict):
            deployment = api.deployment.get(deployment=deployment)
    except exceptions.DBRecordNotFound:
        print("Deployment %s is not found." % deployment)
        return 1
    print("Using deployment: %s" % deployment["uuid"])

    envutils.update_globals_file(envutils.ENV_DEPLOYMENT, deployment["uuid"])
    envutils.update_globals_file(envutils.ENV_ENV, deployment["uuid"])

    if "openstack" in deployment["credentials"]:
        creds = deployment["credentials"]["openstack"][0]
        _update_openrc_deployment_file(
            deployment["uuid"], creds["admin"] or creds["users"][0])
        print("~/.rally/openrc was updated\n\nHINTS:\n"
              "\n* To use standard OpenStack clients, set up your env by "
              "running:\n\tsource ~/.rally/openrc\n"
              "  OpenStack clients are now configured, e.g run:\n\t"
              "openstack image list")
    return None


@deployment_app.command()
@plugins.ensure_plugins_are_loaded
def create(
    name: t.Annotated[
        str,
        typer.Option(
            help="Name of the deployment."
        )
    ],
    fromenv: t.Annotated[
        bool,
        typer.Option(
            "--fromenv",
            help="Read environment variables instead of config file."
        )
    ] = False,
    filename: t.Annotated[
        str | None,
        typer.Option(
            help="Path to the configuration file of the deployment."
        )
    ] = None,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Don't set new deployment as default for future operations."
        )
    ] = False,
) -> None:
    """Create new deployment.

    This command will create a new deployment record in rally
    database. In the case of ExistingCloud deployment engine, it
    will use the cloud represented in the configuration. If the
    cloud doesn't exist, Rally can deploy a new one for you with
    Devstack or Fuel. Different deployment engines exist for these
    cases (see `rally plugin list --plugin-base Engine` for
    more details).

    If you use the ExistingCloud deployment engine, you can pass
    the deployment config by environment variables with ``--fromenv``:

        OS_USERNAME
        OS_PASSWORD
        OS_AUTH_URL
        OS_TENANT_NAME or OS_PROJECT_NAME
        OS_ENDPOINT_TYPE or OS_INTERFACE
        OS_ENDPOINT
        OS_REGION_NAME
        OS_CACERT
        OS_INSECURE
        OS_IDENTITY_API_VERSION

    All other deployment engines need more complex configuration
    data, so it should be stored in a configuration file.

    You can use physical servers, LXC containers, KVM virtual
    machines or virtual machines in OpenStack for deploying the
    cloud. Except physical servers, Rally can create cluster nodes
    for you. Interaction with virtualization software, OpenStack
    cloud or physical servers is provided by server providers.
    """
    api = cliutils.get_api()
    if fromenv:
        result = env_mgr.EnvManager.create_spec_from_sys_environ()
        config = result["spec"]
        if "existing@openstack" in config:
            # NOTE(andreykurilin): if we are here it means that
            #   rally-openstack package is installed
            import rally_openstack  # type: ignore[import-not-found]
            if rally_openstack.__version_tuple__ <= (1, 4, 0):
                if ("https_key" in config["existing@openstack"]
                        and config["existing@openstack"]["https_key"]):
                    print("WARNING: OS_KEY is ignored due to old version "
                          "of rally-openstack package.")
                    config["existing@openstack"].pop("https_key")
    else:
        if not filename:
            config = {}
        else:
            with open(os.path.expanduser(filename), "rb") as deploy_file:
                config = yaml.safe_load(deploy_file.read())

    try:
        deployment = api.deployment.create(config=config, name=name)
    except jsonschema.ValidationError:
        print("Config schema validation error: %s." % sys.exc_info()[1])
        raise typer.Exit(code=1)
    except exceptions.DBRecordExists:
        print("Error: %s" % sys.exc_info()[1])
        raise typer.Exit(code=1)

    _list_deployments(api, deployment_list=[deployment])
    if not no_use:
        _use(api, deployment)


@deployment_app.command()
@plugins.ensure_plugins_are_loaded
def recreate(
    deployment: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--deployment",
            help="UUID or name of the deployment.",
            envvar=envutils.ENV_ENV
        )
    ],
    filename: t.Annotated[
        str | None,
        typer.Option(
            help="Path to the configuration file of the deployment."
        )
    ] = None,
) -> None:
    """Destroy and create an existing deployment.

    Unlike 'deployment destroy', the deployment database record
    will not be deleted, so the deployment UUID stays the same.
    """
    api = cliutils.get_api()
    config = None
    if filename:
        with open(filename, "rb") as deploy_file:
            config = yaml.safe_load(deploy_file.read())

    api.deployment.recreate(deployment=deployment, config=config)


@deployment_app.command()
@plugins.ensure_plugins_are_loaded
def destroy(
    deployment: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--deployment",
            help="UUID or name of the deployment.",
            envvar=envutils.ENV_ENV
        )
    ],
) -> None:
    """Destroy existing deployment.

    This will delete all containers, virtual machines, OpenStack
    instances or Fuel clusters created during Rally deployment
    creation. Also it will remove the deployment record from the
    Rally database.
    """
    api = cliutils.get_api()
    api.deployment.destroy(deployment=deployment)


@deployment_app.command(name="list")
@plugins.ensure_plugins_are_loaded
def list_() -> None:
    """List existing deployments."""
    _list_deployments(cliutils.get_api())


@deployment_app.command()
@cliutils.suppress_warnings
def config(
    deployment: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--deployment",
            help="UUID or name of the deployment.",
            envvar=envutils.ENV_ENV
        )
    ],
) -> None:
    """Display configuration of the deployment.

    Output is the configuration of the deployment in a
    pretty-printed JSON format.
    """
    deploy = cliutils.get_api().deployment.get(deployment=deployment)
    result = deploy["config"]
    print(json.dumps(result, sort_keys=True, indent=4))


@deployment_app.command()
@plugins.ensure_plugins_are_loaded
def show(
    deployment: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--deployment",
            help="UUID or name of the deployment.",
            envvar=envutils.ENV_ENV
        )
    ],
) -> None:
    """Show the credentials of the deployment."""
    # TODO(astudenov): make this method platform independent
    headers = ["auth_url", "username", "password", "tenant_name",
               "region_name", "endpoint_type"]
    table_rows = []

    deployment = cliutils.get_api().deployment.get(deployment=deployment)

    creds = deployment["credentials"]["openstack"][0]
    users = creds["users"]
    admin = creds["admin"]
    credentials = users + [admin] if admin else users
    for ep in credentials:
        data = ["***" if m == "password" else ep.get(m, "")
                for m in headers]
        table_rows.append(utils.Struct(**dict(zip(headers, data))))
    cliutils.print_list(table_rows, headers)


@deployment_app.command()
@plugins.ensure_plugins_are_loaded
def check(
    deployment: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--deployment",
            help="UUID or name of the deployment.",
            envvar=envutils.ENV_ENV
        )
    ],
) -> None:
    """Check all credentials and list all available services."""

    def is_field_there(lst: list, field: str) -> bool:
        return bool([item for item in lst if field in item])

    def print_error(user_type: str, error: dict) -> None:
        print("Error while checking %s credentials:" % user_type)
        if logging.is_debug():
            print(error["trace"])
        else:
            print("\t%s: %s" % (error["etype"], error["msg"]))

    exit_code = 0

    info = cliutils.get_api().deployment.check(deployment=deployment)
    for platform in info:
        for i, creds in enumerate(info[platform]):
            failed = False

            n = "" if len(info[platform]) == 1 else " #%s" % (i + 1)
            header = "Platform %s%s:" % (platform, n)
            print(cliutils.make_header(header))
            if "admin_error" in creds:
                print_error("admin", creds["admin_error"])
                failed = True
            if "user_error" in creds:
                print_error("users", creds["user_error"])
                failed = True

            if not failed:
                print("Available services:")
                formatters = {
                    "Service": lambda x: x.get("name"),
                    "Service Type": lambda x: x.get("type"),
                    "Status": lambda x: x.get("status", "Available")}
                if (is_field_there(creds["services"], "type")
                        and is_field_there(creds["services"], "name")):
                    headers = ["Service", "Service Type", "Status"]
                else:
                    headers = ["Service", "Status"]

                if is_field_there(creds["services"], "version"):
                    headers.append("Version")

                if is_field_there(creds["services"], "description"):
                    headers.append("Description")

                cliutils.print_list(creds["services"], headers,
                                    normalize_field_names=True,
                                    formatters=formatters)
            else:
                exit_code = 1
            print("\n")

    if exit_code:
        raise typer.Exit(code=exit_code)


@deployment_app.command()
@plugins.ensure_plugins_are_loaded
def use(
    deployment: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--deployment",
            help="UUID or name of a deployment."
        )
    ],
) -> None:
    """Set active deployment."""
    rc = _use(cliutils.get_api(), deployment)
    if rc:
        raise typer.Exit(code=rc)
