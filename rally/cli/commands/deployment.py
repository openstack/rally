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

""" Rally command: deployment """

from __future__ import print_function

import json
import os
import re
import sys

import jsonschema
from keystoneclient import exceptions as keystone_exceptions
from six.moves.urllib import parse
import yaml

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally.common import db
from rally.common import fileutils
from rally.common.i18n import _
from rally.common import objects
from rally.common import utils
from rally import exceptions
from rally import osclients
from rally import plugins


class DeploymentCommands(object):
    """Set of commands that allow you to manage deployments."""

    @cliutils.args("--name", type=str, required=True,
                   help="A name of the deployment.")
    @cliutils.args("--fromenv", action="store_true",
                   help="Read environment variables instead of config file")
    @cliutils.args("--filename", type=str, required=False,
                   help="A path to the configuration file of the "
                   "deployment.")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don\'t set new deployment as default for"
                        " future operations")
    @plugins.ensure_plugins_are_loaded
    def create(self, name, fromenv=False, filename=None, do_use=False):
        """Create new deployment.

        This command will create new deployment record in rally database.
        In case of ExistingCloud deployment engine it will use cloud,
        represented in config.
        In cases when cloud doesn't exists Rally will deploy new one
        for you with Devstack or Fuel. For this purposes different deployment
        engines are developed.

        If you use ExistingCloud deployment engine you can pass deployment
        config by environment variables:
            OS_USERNAME
            OS_PASSWORD
            OS_AUTH_URL
            OS_TENANT_NAME
            OS_ENDPOINT
            OS_REGION_NAME

        All other deployment engines need more complex configuration data, so
        it should be stored in configuration file.

        You can use physical servers, lxc containers, KVM virtual machines
        or virtual machines in OpenStack for deploying the cloud in.
        Except physical servers, Rally can create cluster nodes for you.
        Interaction with virtualization software, OpenStack
        cloud or physical servers is provided by server providers.

        :param fromenv: boolean, read environment instead of config file
        :param filename: a path to the configuration file
        :param name: a name of the deployment
        """

        if fromenv:
            required_env_vars = ["OS_USERNAME", "OS_PASSWORD", "OS_AUTH_URL",
                                 "OS_TENANT_NAME"]

            unavailable_vars = [v for v in required_env_vars
                                if v not in os.environ]
            if unavailable_vars:
                print("The following environment variables are required but "
                      "not set: %s" % " ".join(unavailable_vars))
                return(1)

            config = {
                "type": "ExistingCloud",
                "auth_url": os.environ["OS_AUTH_URL"],
                "endpoint": os.environ.get("OS_ENDPOINT"),
                "admin": {
                    "username": os.environ["OS_USERNAME"],
                    "password": os.environ["OS_PASSWORD"],
                    "tenant_name": os.environ["OS_TENANT_NAME"]
                }
            }
            region_name = os.environ.get("OS_REGION_NAME")
            if region_name and region_name != "None":
                config["region_name"] = region_name
        else:
            if not filename:
                print("Either --filename or --fromenv is required")
                return(1)
            filename = os.path.expanduser(filename)
            with open(filename, "rb") as deploy_file:
                config = yaml.safe_load(deploy_file.read())

        try:
            deployment = api.Deployment.create(config, name)
        except jsonschema.ValidationError:
            print(_("Config schema validation error: %s.") % sys.exc_info()[1])
            return(1)
        except exceptions.DeploymentNameExists:
            print(_("Error: %s") % sys.exc_info()[1])
            return(1)

        self.list(deployment_list=[deployment])
        if do_use:
            self.use(deployment["uuid"])

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @envutils.with_default_deployment()
    @plugins.ensure_plugins_are_loaded
    def recreate(self, deployment=None):
        """Destroy and create an existing deployment.

        Unlike 'deployment destroy' command deployment database record will
        not be deleted, so deployment's UUID stay same.

        :param deployment: a UUID or name of the deployment
        """
        api.Deployment.recreate(deployment)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @envutils.with_default_deployment()
    @plugins.ensure_plugins_are_loaded
    def destroy(self, deployment=None):
        """Destroy existing deployment.

        This will delete all containers, virtual machines, OpenStack instances
        or Fuel clusters created during Rally deployment creation. Also it will
        remove deployment record from Rally database.

        :param deployment: a UUID or name of the deployment
        """
        api.Deployment.destroy(deployment)

    def list(self, deployment_list=None):
        """List existing deployments."""

        headers = ["uuid", "created_at", "name", "status", "active"]
        current_deployment = envutils.get_global("RALLY_DEPLOYMENT")
        deployment_list = deployment_list or db.deployment_list()

        table_rows = []
        if deployment_list:
            for t in deployment_list:
                r = [str(t[column]) for column in headers[:-1]]
                r.append("" if t["uuid"] != current_deployment else "*")
                table_rows.append(utils.Struct(**dict(zip(headers, r))))
            cliutils.print_list(table_rows, headers,
                                sortby_index=headers.index("created_at"))
        else:
            print(_("There are no deployments. "
                    "To create a new deployment, use:"
                    "\nrally deployment create"))

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @envutils.with_default_deployment()
    @cliutils.suppress_warnings
    def config(self, deployment=None):
        """Display configuration of the deployment.

        Output is the configuration of the deployment in a
        pretty-printed JSON format.

        :param deployment: a UUID or name of the deployment
        """
        deploy = db.deployment_get(deployment)
        result = deploy["config"]
        print(json.dumps(result, sort_keys=True, indent=4))

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @envutils.with_default_deployment()
    def show(self, deployment=None):
        """Show the endpoints of the deployment.

        :param deployment: a UUID or name of the deployment
        """

        headers = ["auth_url", "username", "password", "tenant_name",
                   "region_name", "endpoint_type"]
        table_rows = []

        deployment = db.deployment_get(deployment)
        users = deployment.get("users", [])
        admin = deployment.get("admin")
        endpoints = users + [admin] if admin else users

        for ep in endpoints:
            data = ["***" if m == "password" else ep.get(m, "")
                    for m in headers]
            table_rows.append(utils.Struct(**dict(zip(headers, data))))
        cliutils.print_list(table_rows, headers)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   required=False, help="UUID or name of a deployment.")
    @envutils.with_default_deployment()
    def check(self, deployment=None):
        """Check keystone authentication and list all available services.

        :param deployment: a UUID or name of the deployment
        """
        headers = ["services", "type", "status"]
        table_rows = []
        try:
            deployment = api.Deployment.get(deployment)

        except exceptions.DeploymentNotFound:
            print(_("Deployment %s is not found.") % deployment)
            return(1)

        try:
            services = api.Deployment.service_list(deployment)
            users = deployment["users"]
            for endpoint_dict in users:
                osclients.Clients(objects.Endpoint(**endpoint_dict)).keystone()

        except keystone_exceptions.ConnectionRefused:
            print(_("Unable to connect %s.") % deployment["admin"]["auth_url"])
            return(1)

        except exceptions.InvalidArgumentsException:
            data = ["keystone", "identity", "Error"]
            table_rows.append(utils.Struct(**dict(zip(headers, data))))
            print(_("Authentication Issues: %s.")
                  % sys.exc_info()[1])
            return(1)

        for serv_type, serv in services.items():
            data = [serv, serv_type, "Available"]
            table_rows.append(utils.Struct(**dict(zip(headers, data))))
        print(_("keystone endpoints are valid and following"
              " services are available:"))
        cliutils.print_list(table_rows, headers)

    def _update_openrc_deployment_file(self, deployment, endpoint):
        openrc_path = os.path.expanduser("~/.rally/openrc-%s" % deployment)
        with open(openrc_path, "w+") as env_file:
            env_file.write("export OS_AUTH_URL=%(auth_url)s\n"
                           "export OS_USERNAME=%(username)s\n"
                           "export OS_PASSWORD=%(password)s\n"
                           "export OS_TENANT_NAME=%(tenant_name)s\n"
                           % endpoint)
            if endpoint.get("region_name"):
                env_file.write("export OS_REGION_NAME=%s\n" %
                               endpoint["region_name"])
            if endpoint.get("endpoint"):
                env_file.write("export OS_ENDPOINT=%s\n" %
                               endpoint["endpoint"])
            if re.match(r"^/v3/?$",
                        parse.urlparse(endpoint["auth_url"]).path) is not None:
                env_file.write("export OS_USER_DOMAIN_NAME=%s\n"
                               "export OS_PROJECT_DOMAIN_NAME=%s\n" %
                               (endpoint["user_domain_name"],
                                endpoint["project_domain_name"]))
        expanded_path = os.path.expanduser("~/.rally/openrc")
        if os.path.exists(expanded_path):
            os.remove(expanded_path)
        os.symlink(openrc_path, expanded_path)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   help="UUID or name of the deployment")
    def use(self, deployment):
        """Set active deployment.

        :param deployment: UUID or name of a deployment
        """
        try:
            deployment = db.deployment_get(deployment)
            print("Using deployment: %s" % deployment["uuid"])
            fileutils.update_globals_file("RALLY_DEPLOYMENT",
                                          deployment["uuid"])
            self._update_openrc_deployment_file(
                deployment["uuid"], deployment.get("admin") or
                deployment.get("users")[0])
            print ("~/.rally/openrc was updated\n\nHINTS:\n"
                   "* To get your cloud resources, run:\n\t"
                   "rally show [flavors|images|keypairs|networks|secgroups]\n"
                   "\n* To use standard OpenStack clients, set up your env by "
                   "running:\n\tsource ~/.rally/openrc\n"
                   "  OpenStack clients are now configured, e.g run:\n\t"
                   "glance image-list")
        except exceptions.DeploymentNotFound:
            print("Deployment %s is not found." % deployment)
            return 1
