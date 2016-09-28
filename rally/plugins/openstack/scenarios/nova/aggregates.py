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


class NovaAggregates(utils.NovaScenario):
    """Benchmark scenarios for Nova aggregates."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True)
    @scenario.configure()
    def list_aggregates(self):
        """List all nova aggregates.

        Measure the "nova aggregate-list" command performance.
        """
        self._list_aggregates()


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaAggregates.create_and_list_aggregates")
class CreateAndListAggregates(utils.NovaScenario):
    """scenario for create and list aggregate."""

    def run(self, availability_zone):
        """Create a aggregate and then list all aggregates.

        This scenario creates a aggregate and then lists all aggregates.
        :param availability_zone: The availability zone of the aggregate
        """
        self._create_aggregate(availability_zone)
        self._list_aggregates()
