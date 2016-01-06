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

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally.common.i18n import _
from rally.common import objects
from rally.common import utils
from rally import osclients


class ShowCommands(object):
    """[Deprecated since 0.2.0] Show resources.

    Set of commands that allow you to view resources, provided by OpenStack
    cloud represented by deployment.
    """

    def _print_header(self, resource_name, credentials):
        print(_("\n%(resource)s for user `%(user)s` in tenant `%(tenant)s`:")
              % {"resource": resource_name,
                 "user": credentials["username"],
                 "tenant": credentials["tenant_name"]})

    @staticmethod
    def _get_credentials(deployment):
        deployment = api.Deployment.get(deployment)
        # NOTE(andreykurilin): it is a bad practise to access to inner db_obj,
        # but we can do it here, since we are planning to deprecate and remove
        # this  command at all.
        admin = deployment.deployment.get("admin")
        credentials = [admin] if admin else []

        return credentials + deployment.deployment.get("users", [])

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @cliutils.process_keystone_exc
    def images(self, deployment=None):
        """Display available images.

        :param deployment: UUID or name of a deployment
        """
        headers = ["UUID", "Name", "Size (B)"]
        mixed_case_fields = ["UUID", "Name"]
        float_cols = ["Size (B)"]
        formatters = dict(zip(float_cols,
                              [cliutils.pretty_float_formatter(col)
                               for col in float_cols]))

        for credential_dict in self._get_credentials(deployment):
            self._print_header("Images", credential_dict)
            table_rows = []

            clients = osclients.Clients(objects.Credential(**credential_dict))
            glance_client = clients.glance()
            for image in glance_client.images.list():
                data = [image.id, image.name, image.size]
                table_rows.append(utils.Struct(**dict(zip(headers, data))))

            cliutils.print_list(table_rows,
                                fields=headers,
                                formatters=formatters,
                                mixed_case_fields=mixed_case_fields)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @cliutils.process_keystone_exc
    def flavors(self, deployment=None):
        """Display available flavors.

        :param deployment: UUID or name of a deployment
        """
        headers = ["ID", "Name", "vCPUs", "RAM (MB)", "Swap (MB)", "Disk (GB)"]
        mixed_case_fields = ["ID", "Name", "vCPUs"]
        float_cols = ["RAM (MB)", "Swap (MB)", "Disk (GB)"]
        formatters = dict(zip(float_cols,
                              [cliutils.pretty_float_formatter(col)
                               for col in float_cols]))

        for credential_dict in self._get_credentials(deployment):
            self._print_header("Flavors", credential_dict)
            table_rows = []
            clients = osclients.Clients(objects.Credential(**credential_dict))
            nova_client = clients.nova()
            for flavor in nova_client.flavors.list():
                data = [flavor.id, flavor.name, flavor.vcpus,
                        flavor.ram, flavor.swap, flavor.disk]
                table_rows.append(utils.Struct(**dict(zip(headers, data))))

            cliutils.print_list(table_rows,
                                fields=headers,
                                formatters=formatters,
                                mixed_case_fields=mixed_case_fields)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @cliutils.process_keystone_exc
    def networks(self, deployment=None):
        """Display configured networks."""

        headers = ["ID", "Label", "CIDR"]
        mixed_case_fields = ["ID", "Label", "CIDR"]

        for credential_dict in self._get_credentials(deployment):
            self._print_header("Networks", credential_dict)
            table_rows = []
            clients = osclients.Clients(objects.Credential(**credential_dict))
            nova_client = clients.nova()
            for network in nova_client.networks.list():
                data = [network.id, network.label, network.cidr]
                table_rows.append(utils.Struct(**dict(zip(headers, data))))

            cliutils.print_list(table_rows,
                                fields=headers,
                                mixed_case_fields=mixed_case_fields)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @cliutils.process_keystone_exc
    def secgroups(self, deployment=None):
        """Display security groups."""

        headers = ["ID", "Name", "Description"]
        mixed_case_fields = ["ID", "Name", "Description"]
        for credential_dict in self._get_credentials(deployment):
            self._print_header("Security groups", credential_dict)
            table_rows = []
            clients = osclients.Clients(objects.Credential(**credential_dict))
            nova_client = clients.nova()
            for secgroup in nova_client.security_groups.list():
                data = [secgroup.id, secgroup.name,
                        secgroup.description]
                table_rows.append(utils.Struct(**dict(zip(headers,
                                                          data))))
            cliutils.print_list(
                table_rows,
                fields=headers,
                mixed_case_fields=mixed_case_fields)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @cliutils.process_keystone_exc
    def keypairs(self, deployment=None):
        """Display available ssh keypairs."""

        headers = ["Name", "Fingerprint"]
        mixed_case_fields = ["Name", "Fingerprint"]

        for credential_dict in self._get_credentials(deployment):
            self._print_header("Keypairs", credential_dict)
            table_rows = []
            clients = osclients.Clients(objects.Credential(**credential_dict))
            nova_client = clients.nova()
            for keypair in nova_client.keypairs.list():
                data = [keypair.name, keypair.fingerprint]
                table_rows.append(utils.Struct(**dict(zip(headers, data))))
            cliutils.print_list(table_rows,
                                fields=headers,
                                mixed_case_fields=mixed_case_fields)
