# Copyright 2015: Mirantis Inc.
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

from rally import osclients
from rally.task import scenario

# NOTE(boris-42): Shortcut to remove import of both rally.task.scenario and
#                 rally.plugins.openstack.scenario
configure = scenario.configure


class OpenStackScenario(scenario.Scenario):
    """Base class for all OpenStack scenarios."""

    def __init__(self, context=None, admin_clients=None, clients=None):
        super(OpenStackScenario, self).__init__(context)
        if context:
            api_info = {}
            if "api_versions" in context.get("config", {}):
                api_versions = context["config"]["api_versions"]
                for service in api_versions:
                    api_info[service] = {
                        "version": api_versions[service].get("version"),
                        "service_type": api_versions[service].get(
                            "service_type")}
            if "admin" in context:
                self._admin_clients = osclients.Clients(
                    context["admin"]["credential"], api_info)
            if "user" in context:
                self._clients = osclients.Clients(
                    context["user"]["credential"], api_info)

        if admin_clients:
            if hasattr(self, "_admin_clients"):
                raise ValueError(
                    "Only one of context[\"admin\"] or admin_clients"
                    " must be supplied")
            self._admin_clients = admin_clients
        if clients:
            if hasattr(self, "_clients"):
                raise ValueError(
                    "Only one of context[\"user\"] or clients"
                    " must be supplied")
            self._clients = clients

    def clients(self, client_type, version=None):
        """Returns a python openstack client of the requested type.

        The client will be that for one of the temporary non-administrator
        users created before the benchmark launch.

        :param client_type: Client type ("nova"/"glance" etc.)
        :param version: client version ("1"/"2" etc.)

        :returns: Standard python OpenStack client instance
        """
        client = getattr(self._clients, client_type)

        return client(version) if version is not None else client()

    def admin_clients(self, client_type, version=None):
        """Returns a python admin openstack client of the requested type.

        :param client_type: Client type ("nova"/"glance" etc.)
        :param version: client version ("1"/"2" etc.)

        :returns: Python openstack client object
        """
        client = getattr(self._admin_clients, client_type)

        return client(version) if version is not None else client()
