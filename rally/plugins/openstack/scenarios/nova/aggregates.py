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


"""Scenarios for Nova aggregates."""


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(name="NovaAggregates.list_aggregates")
class ListAggregates(utils.NovaScenario):

    def run(self):
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


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaAggregates.create_and_delete_aggregate")
class CreateAndDeleteAggregate(utils.NovaScenario):
    """Scenario for create and delete aggregate."""

    def run(self, availability_zone):
        """Create an aggregate and then delete it.

        This scenario first creates an aggregate and then delete it.
        """
        aggregate = self._create_aggregate(availability_zone)
        self._delete_aggregate(aggregate)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaAggregates.create_and_update_aggregate")
class CreateAndUpdateAggregate(utils.NovaScenario):
    """Scenario for create and update aggregate."""

    def run(self, availability_zone):
        """Create an aggregate and then update its name and availability_zone

        This scenario first creates an aggregate and then update its name and
        availability_zone
        :param availability_zone: The availability zone of the aggregate
        """
        aggregate = self._create_aggregate(availability_zone)
        self._update_aggregate(aggregate)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaAggregates.create_aggregate_add_and_remove_host")
class CreateAggregateAddAndRemoveHost(utils.NovaScenario):
    """Scenario for add a host to and remove the host from an aggregate."""

    def run(self, availability_zone):
        """Create an aggregate, add a host to and remove the host from it

        Measure "nova aggregate-add-host" and "nova aggregate-remove-host"
        command performance.
        """
        aggregate = self._create_aggregate(availability_zone)
        hosts = self._list_hosts(zone=None)
        host_name = hosts[0].host_name
        self._aggregate_add_host(aggregate, host_name)
        self._aggregate_remove_host(aggregate, host_name)
