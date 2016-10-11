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
from rally.task import atomic
from rally.task import validation


"""Scenarios for Nova hypervisors."""


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(name="NovaHypervisors.list_hypervisors")
class ListHypervisors(utils.NovaScenario):

    def run(self, detailed=True):
        """List hypervisors.

        Measure the "nova hypervisor-list" command performance.

        :param detailed: True if the hypervisor listing should contain
                         detailed information about all of them
        """
        self._list_hypervisors(detailed)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(name="NovaHypervisors.list_and_get_hypervisors")
class ListAndGetHypervisors(utils.NovaScenario):
    """Benchmark scenario for Nova hypervisors."""
    def run(self, detailed=True):
        """List and Get hypervisors.

        The scenario fist list all hypervisors,then get detailed information
        of the listed hypervisors in trun.

        Measure the "nova hypervisor-show" command performance.

        :param detailed: True if the hypervisor listing should contain
                         detailed information about all of them
        """
        hypervisors = self._list_hypervisors(detailed)

        with atomic.ActionTimer(self, "nova.get_hypervisor"):
            for hypervisor in hypervisors:
                self._get_hypervisor(hypervisor)
