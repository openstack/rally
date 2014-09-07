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

from rally.cmd import cliutils
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally.objects import endpoint
from rally.openstack.common import cliutils as common_cliutils
from rally.openstack.common.gettextutils import _
from rally import osclients
from rally import utils


class ShowCommands(object):

    def _get_endpoints(self, deploy_id):
        deployment = db.deployment_get(deploy_id)
        admin = deployment.get("admin")
        admin = [admin] if admin else []

        return admin + deployment.get("users", [])

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def images(self, deploy_id=None):
        """Show the images that are available in a deployment.

        :param deploy_id: the UUID of a deployment
        """
        headers = ['UUID', 'Name', 'Size (B)']
        mixed_case_fields = ['UUID', 'Name']
        float_cols = ["Size (B)"]
        table_rows = []
        formatters = dict(zip(float_cols,
                              [cliutils.pretty_float_formatter(col)
                               for col in float_cols]))

        try:
            for endpoint_dict in self._get_endpoints(deploy_id):
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                glance_client = clients.glance()
                for image in glance_client.images.list():
                    data = [image.id, image.name, image.size]
                    table_rows.append(utils.Struct(**dict(zip(headers, data))))

                common_cliutils.print_list(table_rows,
                                           fields=headers,
                                           formatters=formatters,
                                           mixed_case_fields=mixed_case_fields)

        except exceptions.InvalidArgumentsException as e:
            print(_("Authentication Issues: %s") % e)
            return(1)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def flavors(self, deploy_id=None):
        """Show the flavors that are available in a deployment.

        :param deploy_id: the UUID of a deployment
        """
        headers = ['ID', 'Name', 'vCPUs', 'RAM (MB)', 'Swap (MB)', 'Disk (GB)']
        mixed_case_fields = ['ID', 'Name', 'vCPUs']
        float_cols = ['RAM (MB)', 'Swap (MB)', 'Disk (GB)']
        formatters = dict(zip(float_cols,
                              [cliutils.pretty_float_formatter(col)
                               for col in float_cols]))
        table_rows = []
        try:
            for endpoint_dict in self._get_endpoints(deploy_id):
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for flavor in nova_client.flavors.list():
                    data = [flavor.id, flavor.name, flavor.vcpus,
                            flavor.ram, flavor.swap, flavor.disk]
                    table_rows.append(utils.Struct(**dict(zip(headers, data))))

                common_cliutils.print_list(table_rows,
                                           fields=headers,
                                           formatters=formatters,
                                           mixed_case_fields=mixed_case_fields)

        except exceptions.InvalidArgumentsException as e:
            print(_("Authentication Issues: %s") % e)
            return(1)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def networks(self, deploy_id=None):
        headers = ['ID', 'Label', 'CIDR']
        mixed_case_fields = ['ID', 'Label', 'CIDR']
        table_rows = []
        try:
            for endpoint_dict in self._get_endpoints(deploy_id):
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for network in nova_client.networks.list():
                    data = [network.id, network.label, network.cidr]
                    table_rows.append(utils.Struct(**dict(zip(headers, data))))

                common_cliutils.print_list(table_rows,
                                           fields=headers,
                                           mixed_case_fields=mixed_case_fields)
        except exceptions.InvalidArgumentsException as e:
            print(_("Authentication Issues: %s") % e)
            return(1)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def secgroups(self, deploy_id=None):
        headers = ['ID', 'Name', 'Description']
        mixed_case_fields = ['ID', 'Name', 'Description']
        table_rows = []
        try:
            for endpoint_dict in self._get_endpoints(deploy_id):
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for secgroup in nova_client.security_groups.list():
                    data = [secgroup.id, secgroup.name,
                            secgroup.description]
                    table_rows.append(utils.Struct(**dict(zip(headers,
                                                              data))))
                    common_cliutils.print_list(
                        table_rows,
                        fields=headers,
                        mixed_case_fields=mixed_case_fields)

        except exceptions.InvalidArgumentsException as e:
            print(_("Authentication Issues: %s") % e)
            return(1)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='the UUID of a deployment')
    @envutils.with_default_deploy_id
    def keypairs(self, deploy_id=None):
        headers = ['Name', 'Fingerprint']
        mixed_case_fields = ['Name', 'Fingerprint']
        table_rows = []
        try:
            for endpoint_dict in self._get_endpoints(deploy_id):
                clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
                nova_client = clients.nova()
                for keypair in nova_client.keypairs.list():
                    data = [keypair.name, keypair.fingerprint]
                    table_rows.append(utils.Struct(**dict(zip(headers, data))))
                common_cliutils.print_list(table_rows,
                                           fields=headers,
                                           mixed_case_fields=mixed_case_fields)

        except exceptions.InvalidArgumentsException as e:
            print(_("Authentication Issues: %s") % e)
            return(1)
