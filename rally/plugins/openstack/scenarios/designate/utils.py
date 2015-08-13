# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from rally.plugins.openstack import scenario
from rally.task import atomic


class DesignateScenario(scenario.OpenStackScenario):
    """Base class for Designate scenarios with basic atomic actions."""

    RESOURCE_NAME_PREFIX = "rally_"

    @atomic.action_timer("designate.create_domain")
    def _create_domain(self, domain=None):
        """Create domain.

        :param domain: dict, POST /v1/domains request options
        :returns: designate domain dict
        """
        domain = domain or {}

        domain.setdefault("email", "root@random.name")
        domain.setdefault("name", "%s.name." % self._generate_random_name())
        return self.clients("designate").domains.create(domain)

    @atomic.action_timer("designate.list_domains")
    def _list_domains(self):
        """Return user domain list."""
        return self.clients("designate").domains.list()

    @atomic.action_timer("designate.delete_domain")
    def _delete_domain(self, domain_id):
        """Delete designate zone.

        :param domain_id: domain ID
        """
        self.clients("designate").domains.delete(domain_id)

    def _create_record(self, domain, record=None, atomic_action=True):
        """Create a record in a domain.

        :param domain: domain dict
        :param record: record dict
        :param atomic_action: True if the record creation should be tracked
                              as an atomic action
        :returns: Designate record dict
        """
        record = record or {}
        record.setdefault("type", "A")
        record.setdefault("name", "%s.%s" % (self._generate_random_name(),
                                             domain["name"]))
        record.setdefault("data", "10.0.0.1")

        client = self.clients("designate")

        if atomic_action:
            with atomic.ActionTimer(self, "designate.create_record"):
                return client.records.create(domain["id"], record)

        return client.records.create(domain["id"], record)

    @atomic.action_timer("designate.list_records")
    def _list_records(self, domain_id):
        """List domain records.

        :param domain_id: domain ID
        :returns: domain records list
        """
        return self.clients("designate").records.list(domain_id)

    def _delete_record(self, domain_id, record_id, atomic_action=True):
        """Delete a domain record.

        :param domain_id: domain ID
        :param record_id: record ID
        :param atomic_action: True if the record creation should be tracked
                              as an atomic action
        """
        client = self.clients("designate")

        if atomic_action:
            with atomic.ActionTimer(self, "designate.delete_record"):
                client.records.delete(domain_id, record_id)
        else:
            client.records.delete(domain_id, record_id)

    @atomic.action_timer("designate.create_server")
    def _create_server(self, server=None):
        """Create server.

        :param server: dict, POST /v1/servers request options
        :returns: designate server dict
        """
        server = server or {}

        server.setdefault("name", "name.%s." % self._generate_random_name())
        return self.admin_clients("designate").servers.create(server)

    @atomic.action_timer("designate.list_servers")
    def _list_servers(self):
        """Return user server list."""
        return self.admin_clients("designate").servers.list()

    @atomic.action_timer("designate.delete_server")
    def _delete_server(self, server_id):
        """Delete Server.

        :param server_id: unicode server ID
        """
        self.admin_clients("designate").servers.delete(server_id)
