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

from rally.common.i18n import _LW
from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import validation

LOG = logging.getLogger(__name__)


class NovaFlavors(utils.NovaScenario):
    """Benchmark scenarios for Nova flavors."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @scenario.configure()
    def list_flavors(self, detailed=True, **kwargs):
        """List all flavors.

        Measure the "nova flavor-list" command performance.

        :param detailed: True if the flavor listing
                         should contain detailed information

        :param kwargs: Optional additional arguments for flavor listing
        """
        self._list_flavors(detailed, **kwargs)

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["nova"]})
    def create_and_list_flavor_access(self, ram, vcpus, disk, **kwargs):
        """Create a non-public flavor and list its access rules

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation
        """
        # NOTE(pirsriva): access rules can be listed
        # only for non-public flavors
        if kwargs.get("is_public", False):
            LOG.warning(_LW("is_public cannot be set to True for listing "
                            "flavor access rules. Setting is_public to False"))
        kwargs["is_public"] = False
        flavor = self._create_flavor(ram, vcpus, disk, **kwargs)
        self._list_flavor_access(flavor.id)

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["nova"]})
    def create_flavor(self, ram, vcpus, disk, **kwargs):
        """Create a flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation
        """
        self._create_flavor(ram, vcpus, disk, **kwargs)
