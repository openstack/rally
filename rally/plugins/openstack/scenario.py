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
from rally.task.scenarios import base


class OpenStackScenario(base.Scenario):
    """Base class for all OpenStack scenarios."""

    def __init__(self, context=None):
        super(OpenStackScenario, self).__init__(context)
        if context:
            if "admin" in context:
                self._admin_clients = osclients.Clients(
                    context["admin"]["endpoint"])
            if "user" in context:
                self._clients = osclients.Clients(context["user"]["endpoint"])

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
