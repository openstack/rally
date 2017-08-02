# Copyright 2015 Cisco Systems Inc.
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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import validation


"""Scenarios for Nova hypervisors."""


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="NovaHypervisors.list_hypervisors",
                    platform="openstack")
class ListHypervisors(utils.NovaScenario):

    def run(self, detailed=True):
        """List hypervisors.

        Measure the "nova hypervisor-list" command performance.

        :param detailed: True if the hypervisor listing should contain
                         detailed information about all of them
        """
        self._list_hypervisors(detailed)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="NovaHypervisors.list_and_get_hypervisors",
                    platform="openstack")
class ListAndGetHypervisors(utils.NovaScenario):

    def run(self, detailed=True):
        """List and Get hypervisors.

        The scenario first lists all hypervisors, then get detailed information
        of the listed hypervisors in turn.

        Measure the "nova hypervisor-show" command performance.

        :param detailed: True if the hypervisor listing should contain
                         detailed information about all of them
        """
        hypervisors = self._list_hypervisors(detailed)

        for hypervisor in hypervisors:
            self._get_hypervisor(hypervisor)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="NovaHypervisors.statistics_hypervisors",
                    platform="openstack")
class StatisticsHypervisors(utils.NovaScenario):

    def run(self):
        """Get hypervisor statistics over all compute nodes.

        Measure the "nova hypervisor-stats" command performance.
        """
        self._statistics_hypervisors()


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="NovaHypervisors.list_and_get_uptime_hypervisors",
                    platform="openstack")
class ListAndGetUptimeHypervisors(utils.NovaScenario):

    def run(self, detailed=True):
        """List hypervisors,then display the uptime of it.

        The scenario first list all hypervisors,then display
        the uptime of the listed hypervisors in turn.

        Measure the "nova hypervisor-uptime" command performance.

        :param detailed: True if the hypervisor listing should contain
                         detailed information about all of them
        """
        hypervisors = self._list_hypervisors(detailed)

        for hypervisor in hypervisors:
            self._uptime_hypervisor(hypervisor)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="NovaHypervisors.list_and_search_hypervisors",
                    platform="openstack")
class ListAndSearchHypervisors(utils.NovaScenario):

    def run(self, detailed=True):
        """List all servers belonging to specific hypervisor.

        The scenario first list all hypervisors,then find its hostname,
        then list all servers belonging to the hypervisor

        Measure the "nova hypervisor-servers <hostname>" command performance.

        :param detailed: True if the hypervisor listing should contain
                         detailed information about all of them
        """
        hypervisors = self._list_hypervisors(detailed)

        for hypervisor in hypervisors:
            self._search_hypervisors(hypervisor.hypervisor_hostname)
