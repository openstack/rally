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

    @base.scenario(context={"cleanup": ["designate"]})
    @validation.required_services(consts.Service.DESIGNATE)
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

    @base.scenario(context={"cleanup": ["designate"]})
    @validation.required_services(consts.Service.DESIGNATE)
    def list_domains(self):
        """Test the designate domain-list command.

        This simple scenario tests the designate domain-list command by listing
        all the domains.

        Suppose if we have 2 users in context and each has 2 domains
        uploaded for them we will be able to test the performance of
        designate domain-list command in this case.
        """

        self._list_domains()

    @base.scenario(context={"cleanup": ["designate"]})
    @validation.required_services(consts.Service.DESIGNATE)
    def create_and_delete_domain(self):
        """Test adds and then deletes domain.

        This is very useful to measure perfromance of creating and deleting
        domains with different level of load.
        """
        domain = self._create_domain()
        self._delete_domain(domain['id'])
