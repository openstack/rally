# Copyright 2016 IBM Corp.
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


class NovaAgents(utils.NovaScenario):
    """Benchmark scenarios for Nova agents."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True)
    @scenario.configure()
    def list_agents(self, hypervisor=None):
        """List all builds.

        Measure the "nova agent-list" command performance.

        :param hypervisor: List agent builds on a specific hypervisor.
                           None (default value) means list for all
                           hypervisors
        """
        self._list_agents(hypervisor)
