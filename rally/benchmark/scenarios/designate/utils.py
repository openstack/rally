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

from rally.benchmark.scenarios import base


class DesignateScenario(base.Scenario):
    """This class should contain base operations for benchmarking designate."""

    RESOURCE_NAME_PREFIX = "rally_"

    @base.atomic_action_timer('designate.create_domain')
    def _create_domain(self, domain=None):
        """Create domain.

        :param domain: dict, POST /v1/domains request options
        :returns: designate domain dict
        """
        domain = domain or {}

        domain.setdefault('email', 'root@random.name')
        domain.setdefault('name', '%s.name.' % self._generate_random_name())
        return self.clients("designate").domains.create(domain)

    @base.atomic_action_timer('designate.list_domains')
    def _list_domains(self):
        """Return user domain list."""
        return self.clients("designate").domains.list()

    @base.atomic_action_timer('designate.delete_domain')
    def _delete_domain(self, domain_id):
        """Delete designate zone.

        :param domain: Domain object
        """
        self.clients("designate").domains.delete(domain_id)

    def _create_record(self, domain, record=None, atomic_action=True):
        """Create a record in a domain.

        :param domain: Domain object
        :param record: Record object
        :returns: designate record dict
        """
        record = record or {}
        record.setdefault('type', 'A')
        record.setdefault('name', '%s.%s' % (self._generate_random_name(),
                                             domain['name']))
        record.setdefault('data', '10.0.0.1')

        client = self.clients('designate')

        if atomic_action:
            with base.AtomicAction(self, 'designate.create_record'):
                return client.records.create(domain['id'], record)

        return client.records.create(domain['id'], record)

    @base.atomic_action_timer('designate.list_records')
    def _list_records(self, domain_id):
        """List records in a domain..

        :param domain_id: Domain ID
        :returns: domain record list
        """
        return self.clients("designate").records.list(domain_id)

    def _delete_record(self, domain_id, record_id, atomic_action=True):
        """Delete a record in a domain..

        :param domain_id: Domain ID
        :param record_id: Record ID
        """
        client = self.clients('designate')

        if atomic_action:
            with base.AtomicAction(self, 'designate.delete_record'):
                client.records.create(domain_id, record_id)

        client.records.delete(domain_id, record_id)
