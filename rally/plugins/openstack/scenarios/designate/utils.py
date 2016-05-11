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

    @atomic.action_timer("designate.create_domain")
    def _create_domain(self, domain=None):
        """Create domain.

        :param domain: dict, POST /v1/domains request options
        :returns: designate domain dict
        """
        domain = domain or {}

        domain.setdefault("email", "root@random.name")
        domain["name"] = "%s.name." % self.generate_random_name()
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

    @atomic.action_timer("designate.update_domain")
    def _update_domain(self, domain):
        """Update designate domain.

        :param domain: designate domain
        :returns: designate updated domain dict
        """
        domain["description"] = "updated domain"
        domain["email"] = "updated@random.name"
        return self.clients("designate").domains.update(domain)

    @atomic.optional_action_timer("designate.create_record")
    def _create_record(self, domain, record=None):
        """Create a record in a domain.

        :param domain: domain dict
        :param record: record dict
        :param atomic_action: True if the record creation should be
                              tracked as an atomic action. added and
                              handled by the optional_action_timer()
                              decorator
        :returns: Designate record dict
        """
        record = record or {}
        record.setdefault("type", "A")
        record["name"] = "%s.%s" % (self.generate_random_name(),
                                    domain["name"])
        record.setdefault("data", "10.0.0.1")

        client = self.clients("designate")

        return client.records.create(domain["id"], record)

    @atomic.action_timer("designate.list_records")
    def _list_records(self, domain_id):
        """List domain records.

        :param domain_id: domain ID
        :returns: domain records list
        """
        return self.clients("designate").records.list(domain_id)

    @atomic.optional_action_timer("designate.delete_record")
    def _delete_record(self, domain_id, record_id):
        """Delete a domain record.

        :param domain_id: domain ID
        :param record_id: record ID
        :param atomic_action: True if the record creation should be
                              tracked as an atomic action. added and
                              handled by the optional_action_timer()
                              decorator
        """
        self.clients("designate").records.delete(domain_id, record_id)

    @atomic.action_timer("designate.create_server")
    def _create_server(self, server=None):
        """Create server.

        :param server: dict, POST /v1/servers request options
        :returns: designate server dict
        """
        server = server or {}

        server["name"] = "name.%s." % self.generate_random_name()
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

    # NOTE: API V2
    @atomic.action_timer("designate.create_zone")
    def _create_zone(self, name=None, type_=None, email=None, description=None,
                     ttl=None):
        """Create zone.

        :param name: Zone name
        :param type_: Zone type, PRIMARY or SECONDARY
        :param email: Zone owner email
        :param description: Zone description
        :param ttl: Zone ttl - Time to live in seconds
        :returns: designate zone dict
        """
        type_ = type_ or "PRIMARY"

        if type_ == "PRIMARY":
            email = email or "root@random.name"
            # Name is only useful to be random for PRIMARY
            name = name or "%s.name." % self.generate_random_name()

        return self.clients("designate", version="2").zones.create(
            name=name,
            type_=type_,
            email=email,
            description=description,
            ttl=ttl
        )

    @atomic.action_timer("designate.list_zones")
    def _list_zones(self, criterion=None, marker=None, limit=None):
        """Return user zone list.

        :param criterion: API Criterion to filter by
        :param marker: UUID marker of the item to start the page from
        :param limit: How many items to return in the page.
        :returns: list of designate zones
        """
        return self.clients("designate", version="2").zones.list()

    @atomic.action_timer("designate.delete_zone")
    def _delete_zone(self, zone_id):
        """Delete designate zone.

        :param zone_id: Zone ID
        """
        self.clients("designate", version="2").zones.delete(zone_id)

    @atomic.action_timer("designate.list_recordsets")
    def _list_recordsets(self, zone_id, criterion=None, marker=None,
                         limit=None):
        """List zone recordsets.

        :param zone_id: Zone ID
        :param criterion: API Criterion to filter by
        :param marker: UUID marker of the item to start the page from
        :param limit: How many items to return in the page.
        :returns: zone recordsets list
        """
        return self.clients("designate", version="2").recordsets.list(
            zone_id, criterion=criterion, marker=marker, limit=limit)

    @atomic.optional_action_timer("designate.create_recordset")
    def _create_recordset(self, zone, recordset=None):
        """Create a recordset in a zone.

        :param zone: zone dict
        :param recordset: recordset dict
        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        :returns: Designate recordset dict
        """
        recordset = recordset or {}
        recordset.setdefault("type_", recordset.pop("type", "A"))
        if "name" not in recordset:
            recordset["name"] = "%s.%s" % (self.generate_random_name(),
                                           zone["name"])
        if "records" not in recordset:
            recordset["records"] = ["10.0.0.1"]

        return self.clients("designate", version="2").recordsets.create(
            zone["id"], **recordset)

    @atomic.optional_action_timer("designate.delete_recordset")
    def _delete_recordset(self, zone_id, recordset_id):
        """Delete a zone recordset.

        :param zone_id: Zone ID
        :param recordset_id: Recordset ID
        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        """

        self.clients("designate", version="2").recordsets.delete(
            zone_id, recordset_id)
