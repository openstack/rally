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
import prettytable
import sys

import yaml

from rally.cmd import cliutils
from rally.cmd.commands import use as _use
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally.objects import endpoint
from rally.openstack.common.gettextutils import _
from rally.orchestrator import api
from rally import osclients


class DeploymentCommands(object):

    @cliutils.args('--name', type=str, required=True,
                   help='A name of the deployment.')
    @cliutils.args('--fromenv', action='store_true',
                   help='Read environment variables instead of config file')
    @cliutils.args('--filename', type=str, required=False,
                   help='A path to the configuration file of the '
                   'deployment.')
    @cliutils.args('--no-use', action='store_false', dest='use',
                   help='Don\'t set new deployment as default for'
                        ' future operations')
    def create(self, name, fromenv=False, filename=None, use=False):
        """Create a new deployment on the basis of configuration file.

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
                      "not set: %s" % ' '.join(unavailable_vars))
                return

            config = {
                "name": "DummyEngine",
                "endpoint": {
                    "auth_url": os.environ['OS_AUTH_URL'],
                    "username": os.environ['OS_USERNAME'],
                    "password": os.environ['OS_PASSWORD'],
                    "tenant_name": os.environ['OS_TENANT_NAME']
                }
            }
        else:
            if not filename:
                print("Either --filename or --fromenv is required")
                return
            with open(filename, 'rb') as deploy_file:
                config = yaml.safe_load(deploy_file.read())

        deployment = api.create_deploy(config, name)
        self.list(deployment_list=[deployment])
        if use:
            _use.UseCommands().deployment(deployment['uuid'])

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    @envutils.deploy_id_default
    def recreate(self, deploy_id=None):
        """Destroy and create an existing deployment.

        :param deploy_id: a UUID of the deployment
        """
        api.recreate_deploy(deploy_id)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    @envutils.deploy_id_default
    def destroy(self, deploy_id=None):
        """Destroy the deployment.

        Release resources that are allocated for the deployment. The
        Deployment, related tasks and their results are also deleted.

        :param deploy_id: a UUID of the deployment
        """
        api.destroy_deploy(deploy_id)

    def list(self, deployment_list=None):
        """Print list of deployments."""
        headers = ['uuid', 'created_at', 'name', 'status', 'active']
        current_deploy_id = envutils.default_deployment_id()
        deployment_list = deployment_list or db.deployment_list()
        if deployment_list:
            table = prettytable.PrettyTable(headers)

            for t in deployment_list:
                r = [str(t[column]) for column in headers[:-1]]
                r.append("" if t["uuid"] != current_deploy_id else "*")
                table.add_row(r)

            print(table)
        else:
            print(_("There are no deployments. "
                    "To create a new deployment, use:"
                    "\nrally deployment create"))

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    @envutils.deploy_id_default
    def config(self, deploy_id=None):
        """Print on stdout a config of the deployment in JSON format.

        :param deploy_id: a UUID of the deployment
        """
        deploy = db.deployment_get(deploy_id)
        print(json.dumps(deploy['config']))

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    @envutils.deploy_id_default
    def endpoint(self, deploy_id=None):
        """Print endpoint of the deployment.

        :param deploy_id: a UUID of the deployment
        """
        headers = ['auth_url', 'username', 'password', 'tenant_name']
        table = prettytable.PrettyTable(headers)
        endpoints = db.deployment_get(deploy_id)['endpoints']
        for ep in endpoints:
            table.add_row([ep.get(m, '') for m in headers])
        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    @envutils.deploy_id_default
    def check(self, deploy_id=None):
        """Check the deployment.

        Check keystone authentication and list all available services.

        :param deploy_id: a UUID of the deployment
        """
        headers = ['services', 'type', 'status']
        table = prettytable.PrettyTable(headers)
        try:
            endpoints = db.deployment_get(deploy_id)['endpoints']
            for endpoint_dict in endpoints:
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                client = clients.verified_keystone()
                print("keystone endpoints are valid and following "
                      "services are available:")
                for service in client.service_catalog.get_data():
                    table.add_row([service['name'], service['type'],
                                   'Available'])
        except exceptions.InvalidArgumentsException:
            table.add_row(['keystone', 'identity', 'Error'])
            print(_("Authentication Issues: %s.")
                  % sys.exc_info()[1])
        print(table)
