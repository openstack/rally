# Copyright 2015: Inc.
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


class NovaFlavors(utils.NovaScenario):
    """Benchmark scenarios for Nova flavors."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova"]})
    def list_flavors(self, detailed=True, **kwargs):
        """List all flavors.

        Measure the "nova flavor-list" command performance.

        :param detailed: True if the flavor listing
                         should contain detailed information

        :param kwargs: Optional additional arguments for flavor listing
        """
        self._list_flavors(detailed, **kwargs)
