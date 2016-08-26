# Copyright 2015: Mirantis Inc.
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


"""Scenarios for create nova floating IP by range."""


@validation.restricted_parameters("pool")
@validation.required_parameters("start_cidr")
@validation.required_services(consts.Service.NOVA, consts.Service.NOVA_NET)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name=("NovaFloatingIpsBulk"
                          ".create_and_list_floating_ips_bulk"))
class CreateAndListFloatingIpsBulk(utils.NovaScenario):

    def run(self, start_cidr, **kwargs):
        """Create nova floating IP by range and list it.

        This scenario creates a floating IP by range and then lists all.

        :param start_cidr: Floating IP range
        :param kwargs: Optional additional arguments for range IP creation
        """

        self._create_floating_ips_bulk(start_cidr, **kwargs)
        self._list_floating_ips_bulk()


@validation.restricted_parameters("pool")
@validation.required_parameters("start_cidr")
@validation.required_services(consts.Service.NOVA, consts.Service.NOVA_NET)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name=("NovaFloatingIpsBulk"
                          ".create_and_delete_floating_ips_bulk"))
class CreateAndDeleteFloatingIpsBulk(utils.NovaScenario):

    def run(self, start_cidr, **kwargs):
        """Create nova floating IP by range and delete it.

        This scenario creates a floating IP by range and then delete it.

        :param start_cidr: Floating IP range
        :param kwargs: Optional additional arguments for range IP creation
        """

        floating_ips_bulk = self._create_floating_ips_bulk(start_cidr,
                                                           **kwargs)
        self._delete_floating_ips_bulk(floating_ips_bulk.ip_range)
