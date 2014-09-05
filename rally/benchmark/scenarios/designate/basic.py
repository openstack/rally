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
from rally.benchmark.scenarios.designate import utils
from rally.benchmark import validation
from rally import consts


class DesignateBasic(utils.DesignateScenario):

    @validation.required_services(consts.Service.DESIGNATE)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["designate"]})
    def create_and_list_domains(self):
        """Tests creating a domain and listing domains.

        This scenario is a very useful tool to measure
        the "designate domain-list" command performance.

        If you have only 1 user in your context, you will
        add 1 domain on every iteration. So you will have more
        and more domain and will be able to measure the
        performance of the "designate domain-list" command depending on
        the number of domains owned by users.
        """
        self._create_domain()
        self._list_domains()

    @validation.required_services(consts.Service.DESIGNATE)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["designate"]})
    def list_domains(self):
        """Test the designate domain-list command.

        This simple scenario tests the designate domain-list command by listing
        all the domains.

        Suppose if we have 2 users in context and each has 2 domains
        uploaded for them we will be able to test the performance of
        designate domain-list command in this case.
        """

        self._list_domains()

    @validation.required_services(consts.Service.DESIGNATE)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["designate"]})
    def create_and_delete_domain(self):
        """Test adds and then deletes domain.

        This is very useful to measure perfromance of creating and deleting
        domains with different level of load.
        """
        domain = self._create_domain()
        self._delete_domain(domain['id'])

    @validation.required_services(consts.Service.DESIGNATE)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["designate"]})
    def create_and_delete_records(self, records_per_domain=5):
        """Test adds and then deletes records.

        This is very useful to measure perfromance of creating and deleting
        records with different level of load.

        :param records_per_domain: Records to create pr domain.
        """
        domain = self._create_domain()

        records = []

        key = "designate.create_%s_records" % records_per_domain
        with base.AtomicAction(self, key):
            for i in range(records_per_domain):
                record = self._create_record(domain, atomic_action=False)
                records.append(record)

        key = "designate.delete_%s_records" % records_per_domain
        with base.AtomicAction(self, key):
            for record in records:
                self._delete_record(
                    domain['id'], record['id'], atomic_action=False)

    @validation.required_services(consts.Service.DESIGNATE)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["designate"]})
    def list_records(self, domain_id):
        """Test the designate record-list command.

        This simple scenario tests the designate record-list command by listing
        all the records in a domain.

        Suppose if we have 2 users in context and each has 2 domains
        uploaded for them we will be able to test the performance of
        designate record-list command in this case.

        :param domain_id: Domain ID
        """

        self._list_records(domain_id)

    @validation.required_services(consts.Service.DESIGNATE)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["designate"]})
    def create_and_list_records(self, records_per_domain=5):
        """Test adds and then lists records.

        If you have only 1 user in your context, you will
        add 1 record on every iteration. So you will have more
        and more records and will be able to measure the
        performance of the "designate record-list" command depending on
        the number of domains/records owned by users.

        :param records_per_domain: Records to create pr domain.
        """
        domain = self._create_domain()

        key = "designate.create_%s_records" % records_per_domain
        with base.AtomicAction(self, key):
            for i in range(records_per_domain):
                self._create_record(domain, atomic_action=False)

        self._list_records(domain['id'])
