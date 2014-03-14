# Copyright 2014: The Rally team
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

""" Rally command: show """

from __future__ import print_function

import prettytable
import sys

from rally.cmd import cliutils
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally.objects import endpoint
from rally import osclients


class ShowCommands(object):

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def images(self, deploy_id=None):
        """Show the images that are available in a deployment.

        :param deploy_id: the UUID of a deployment
        """
        headers = ['UUID', 'Name', 'Size (B)']
        table = prettytable.PrettyTable(headers)
        try:
            endpoints = db.deployment_get(deploy_id)['endpoints']
            for endpoint_dict in endpoints:
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                glance_client = clients.glance()
                for image in glance_client.images.list():
                    table.add_row([image.id, image.name, image.size])
        except exceptions.InvalidArgumentsException:
            print(_("Authentication Issues: %s") % sys.exc_info()[1])
        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def flavors(self, deploy_id=None):
        """Show the flavors that are available in a deployment.

        :param deploy_id: the UUID of a deployment
        """
        headers = ['ID', 'Name', 'vCPUs', 'RAM (MB)', 'Swap (MB)', 'Disk (GB)']
        table = prettytable.PrettyTable(headers)
        try:
            endpoints = db.deployment_get(deploy_id)['endpoints']
            for endpoint_dict in endpoints:
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for flavor in nova_client.flavors.list():
                    table.add_row([flavor.id, flavor.name, flavor.vcpus,
                                   flavor.ram, flavor.swap, flavor.disk])
        except exceptions.InvalidArgumentsException:
            print(_("Authentication Issues: %s") % sys.exc_info()[1])
        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def networks(self, deploy_id=None):
        headers = ['ID', 'Label', 'CIDR']
        table = prettytable.PrettyTable(headers)
        try:
            endpoints = db.deployment_get(deploy_id)['endpoints']
            for endpoint_dict in endpoints:
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
            nova_client = clients.nova()
            for network in nova_client.networks.list():
                table.add_row([network.id, network.label, network.cidr])
        except exceptions.InvalidArgumentsException:
            print(_("Authentication Issues: %s") % sys.exc_info()[1])
        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def secgroups(self, deploy_id=None):
        headers = ['ID', 'Name', 'Description']
        table = prettytable.PrettyTable(headers)
        try:
            endpoints = db.deployment_get(deploy_id)['endpoints']
            for endpoint_dict in endpoints:
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for secgroup in nova_client.security_groups.list():
                    table.add_row([secgroup.id, secgroup.name,
                                   secgroup.description])
        except exceptions.InvalidArgumentsException:
            print(_("Authentication Issues: %s") % sys.exc_info()[1])
        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def keypairs(self, deploy_id=None):
        headers = ['Name', 'Fingerprint']
        table = prettytable.PrettyTable(headers)
        try:
            endpoints = db.deployment_get(deploy_id)['endpoints']
            for endpoint_dict in endpoints:
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for keypair in nova_client.keypairs.list():
                    table.add_row([keypair.name, keypair.fingerprint])
        except exceptions.InvalidArgumentsException:
            print(_("Authentication Issues: %s") % sys.exc_info()[1])
        print(table)
