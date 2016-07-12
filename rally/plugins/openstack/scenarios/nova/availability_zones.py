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


class NovaAvailabilityZones(utils.NovaScenario):
    """Benchmark scenarios for Nova availability-zones."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True)
    @scenario.configure()
    def list_availability_zones(self, detailed=True):
        """List all availability zones.

        Measure the "nova availability-zone-list" command performance.

        :param detailed: True if the availability-zone listing should contain
                         detailed information about all of them
        """
        self._list_availability_zones(detailed)
