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

from __future__ import print_function

import json
import os
import sys

import jsonschema

from rally.cli import cliutils
from rally.cli import envutils
from rally.common import fileutils
from rally.common import logging
from rally.common import utils
from rally.common import yamlutils as yaml
from rally import exceptions
from rally import plugins


class DeploymentCommands(object):
    """Set of commands that allow you to manage deployments."""

    @cliutils.args("--name", type=str, required=True,
                   help="Name of the deployment.")
    @cliutils.args("--fromenv", action="store_true",
                   help="Read environment variables instead of config file.")
    @cliutils.args("--filename", type=str, required=False, metavar="<path>",
                   help="Path to the configuration file of the deployment.")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don't set new deployment as default for"
                        " future operations.")
    @plugins.ensure_plugins_are_loaded
    def create(self, api, name, fromenv=False, filename=None, do_use=False):
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

        if fromenv:
            # TODO(astudenov): move this to Credential plugin
            config = {"openstack": envutils.get_creds_from_env_vars()}
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
            return 1
        except exceptions.DBRecordExists:
            print("Error: %s" % sys.exc_info()[1])
            return 1

        self.list(api, deployment_list=[deployment])
        if do_use:
            self.use(api, deployment)

    @cliutils.args("--filename", type=str, required=False, metavar="<path>",
                   help="Path to the configuration file of the deployment.")
    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the deployment.")
    @envutils.with_default_deployment()
    @plugins.ensure_plugins_are_loaded
    def recreate(self, api, deployment=None, filename=None):
        """Destroy and create an existing deployment.

        Unlike 'deployment destroy', the deployment database record
        will not be deleted, so the deployment UUID stays the same.
        """
        config = None
        if filename:
            with open(filename, "rb") as deploy_file:
                config = yaml.safe_load(deploy_file.read())

        api.deployment.recreate(deployment=deployment, config=config)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the deployment.")
    @envutils.with_default_deployment()
    @plugins.ensure_plugins_are_loaded
    def destroy(self, api, deployment=None):
        """Destroy existing deployment.

        This will delete all containers, virtual machines, OpenStack
        instances or Fuel clusters created during Rally deployment
        creation. Also it will remove the deployment record from the
        Rally database.
        """
        api.deployment.destroy(deployment=deployment)

    def list(self, api, deployment_list=None):
        """List existing deployments."""

        headers = ["uuid", "created_at", "name", "status", "active"]
        current_deployment = envutils.get_global("RALLY_DEPLOYMENT")
        deployment_list = deployment_list or api.deployment.list()

        table_rows = []
        if deployment_list:
            for t in deployment_list:
                r = [str(t[column]) for column in headers[:-1]]
                r.append("" if t["uuid"] != current_deployment else "*")
                table_rows.append(utils.Struct(**dict(zip(headers, r))))
            cliutils.print_list(table_rows, headers,
                                sortby_index=headers.index("created_at"))
        else:
            print("There are no deployments. To create a new deployment, use:"
                  "\nrally deployment create")

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the deployment.")
    @envutils.with_default_deployment()
    @cliutils.suppress_warnings
    def config(self, api, deployment=None):
        """Display configuration of the deployment.

        Output is the configuration of the deployment in a
        pretty-printed JSON format.
        """
        deploy = api.deployment.get(deployment=deployment)
        result = deploy["config"]
        print(json.dumps(result, sort_keys=True, indent=4))

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the deployment.")
    @envutils.with_default_deployment()
    @plugins.ensure_plugins_are_loaded
    def show(self, api, deployment=None):
        """Show the credentials of the deployment."""
        # TODO(astudenov): make this method platform independent

        headers = ["auth_url", "username", "password", "tenant_name",
                   "region_name", "endpoint_type"]
        table_rows = []

        deployment = api.deployment.get(deployment=deployment)

        creds = deployment["credentials"]["openstack"][0]
        users = creds["users"]
        admin = creds["admin"]
        credentials = users + [admin] if admin else users
        for ep in credentials:
            data = ["***" if m == "password" else ep.get(m, "")
                    for m in headers]
            table_rows.append(utils.Struct(**dict(zip(headers, data))))
        cliutils.print_list(table_rows, headers)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the deployment.")
    @envutils.with_default_deployment()
    @plugins.ensure_plugins_are_loaded
    def check(self, api, deployment=None):
        """Check all credentials and list all available services."""

        def is_field_there(lst, field):
            return bool([item for item in lst if field in item])

        def print_error(user_type, error):
            print("Error while checking %s credentials:" % user_type)
            if logging.is_debug():
                print(error["trace"])
            else:
                print("\t%s: %s" % (error["etype"], error["msg"]))

        exit_code = 0

        info = api.deployment.check(deployment=deployment)
        for platform in info:
            for i, credentials in enumerate(info[platform]):
                failed = False

                n = "" if len(info[platform]) == 1 else " #%s" % (i + 1)
                header = "Platform %s%s:" % (platform, n)
                print(cliutils.make_header(header))
                if "admin_error" in credentials:
                    print_error("admin", credentials["admin_error"])
                    failed = True
                if "user_error" in credentials:
                    print_error("users", credentials["user_error"])
                    failed = True

                if not failed:
                    print("Available services:")
                    formatters = {
                        "Service": lambda x: x.get("name"),
                        "Service Type": lambda x: x.get("type"),
                        "Status": lambda x: x.get("status", "Available")}
                    if (is_field_there(credentials["services"], "type") and
                            is_field_there(credentials["services"], "name")):
                        headers = ["Service", "Service Type", "Status"]
                    else:
                        headers = ["Service", "Status"]

                    if is_field_there(credentials["services"], "version"):
                        headers.append("Version")

                    if is_field_there(credentials["services"], "description"):
                        headers.append("Description")

                    cliutils.print_list(credentials["services"], headers,
                                        normalize_field_names=True,
                                        formatters=formatters)
                else:
                    exit_code = 1
                print("\n")

        return exit_code

    def _update_openrc_deployment_file(self, deployment, credential):
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

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @plugins.ensure_plugins_are_loaded
    def use(self, api, deployment):
        """Set active deployment."""
        # TODO(astudenov): make this method platform independent
        try:
            if not isinstance(deployment, dict):
                deployment = api.deployment.get(deployment=deployment)
        except exceptions.DBRecordNotFound:
            print("Deployment %s is not found." % deployment)
            return 1
        print("Using deployment: %s" % deployment["uuid"])

        fileutils.update_globals_file(envutils.ENV_DEPLOYMENT,
                                      deployment["uuid"])
        fileutils.update_globals_file(envutils.ENV_ENV,
                                      deployment["uuid"])

        if "openstack" in deployment["credentials"]:
            creds = deployment["credentials"]["openstack"][0]
            self._update_openrc_deployment_file(
                deployment["uuid"], creds["admin"] or creds["users"][0])
            print("~/.rally/openrc was updated\n\nHINTS:\n"
                  "\n* To use standard OpenStack clients, set up your env by "
                  "running:\n\tsource ~/.rally/openrc\n"
                  "  OpenStack clients are now configured, e.g run:\n\t"
                  "openstack image list")
