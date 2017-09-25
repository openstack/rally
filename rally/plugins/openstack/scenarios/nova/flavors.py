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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import validation


"""Scenarios for Nova flavors."""


LOG = logging.getLogger(__name__)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="NovaFlavors.list_flavors", platform="openstack")
class ListFlavors(utils.NovaScenario):

    def run(self, detailed=True, is_public=True, marker=None, min_disk=None,
            min_ram=None, limit=None, sort_key=None, sort_dir=None):
        """List all flavors.

        Measure the "nova flavor-list" command performance.

        :param detailed: Whether flavor needs to be return with details
                         (optional).
        :param is_public: Filter flavors with provided access type (optional).
                          None means give all flavors and only admin has query
                          access to all flavor types.
        :param marker: Begin returning flavors that appear later in the flavor
                       list than that represented by this flavor id (optional).
        :param min_disk: Filters the flavors by a minimum disk space, in GiB.
        :param min_ram: Filters the flavors by a minimum RAM, in MB.
        :param limit: maximum number of flavors to return (optional).
        :param sort_key: Flavors list sort key (optional).
        :param sort_dir: Flavors list sort direction (optional).
        """
        self._list_flavors(detailed=detailed, is_public=is_public,
                           marker=marker, min_disk=min_disk, min_ram=min_ram,
                           limit=limit, sort_key=sort_key, sort_dir=sort_dir)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["nova"]},
                    name="NovaFlavors.create_and_list_flavor_access",
                    platform="openstack")
class CreateAndListFlavorAccess(utils.NovaScenario):

    def run(self, ram, vcpus, disk, flavorid="auto",
            ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
        """Create a non-public flavor and list its access rules

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param flavorid: ID for the flavor (optional). You can use the reserved
                         value ``"auto"`` to have Nova generate a UUID for the
                         flavor in cases where you cannot simply pass ``None``.
        :param ephemeral: Ephemeral space size in GB (default 0).
        :param swap: Swap space in MB
        :param rxtx_factor: RX/TX factor
        :param is_public: Make flavor accessible to the public (default true).
        """
        # NOTE(pirsriva): access rules can be listed
        # only for non-public flavors
        if is_public:
            LOG.warning("is_public cannot be set to True for listing "
                        "flavor access rules. Setting is_public to False")
        is_public = False
        flavor = self._create_flavor(ram, vcpus, disk, flavorid=flavorid,
                                     ephemeral=ephemeral, swap=swap,
                                     rxtx_factor=rxtx_factor,
                                     is_public=is_public)
        self.assertTrue(flavor)

        self._list_flavor_access(flavor.id)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["nova"]},
                    name="NovaFlavors.create_flavor_and_add_tenant_access",
                    platform="openstack")
class CreateFlavorAndAddTenantAccess(utils.NovaScenario):

    def run(self, ram, vcpus, disk, flavorid="auto",
            ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
        """Create a flavor and Add flavor access for the given tenant.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param flavorid: ID for the flavor (optional). You can use the reserved
                         value ``"auto"`` to have Nova generate a UUID for the
                         flavor in cases where you cannot simply pass ``None``.
        :param ephemeral: Ephemeral space size in GB (default 0).
        :param swap: Swap space in MB
        :param rxtx_factor: RX/TX factor
        :param is_public: Make flavor accessible to the public (default true).
        """
        flavor = self._create_flavor(ram, vcpus, disk, flavorid=flavorid,
                                     ephemeral=ephemeral, swap=swap,
                                     rxtx_factor=rxtx_factor,
                                     is_public=is_public)
        self.assertTrue(flavor)
        self._add_tenant_access(flavor.id, self.context["tenant"]["id"])


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["nova"]},
                    name="NovaFlavors.create_flavor", platform="openstack")
class CreateFlavor(utils.NovaScenario):

    def run(self, ram, vcpus, disk, flavorid="auto",
            ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
        """Create a flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param flavorid: ID for the flavor (optional). You can use the reserved
                         value ``"auto"`` to have Nova generate a UUID for the
                         flavor in cases where you cannot simply pass ``None``.
        :param ephemeral: Ephemeral space size in GB (default 0).
        :param swap: Swap space in MB
        :param rxtx_factor: RX/TX factor
        :param is_public: Make flavor accessible to the public (default true).
        """
        self._create_flavor(ram, vcpus, disk, flavorid=flavorid,
                            ephemeral=ephemeral, swap=swap,
                            rxtx_factor=rxtx_factor,
                            is_public=is_public)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["nova"]},
                    name="NovaFlavors.create_and_get_flavor",
                    platform="openstack")
class CreateAndGetFlavor(utils.NovaScenario):
    """Scenario for create and get flavor."""

    def run(self, ram, vcpus, disk, flavorid="auto",
            ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
        """Create flavor and get detailed information of the flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param flavorid: ID for the flavor (optional). You can use the reserved
                         value ``"auto"`` to have Nova generate a UUID for the
                         flavor in cases where you cannot simply pass ``None``.
        :param ephemeral: Ephemeral space size in GB (default 0).
        :param swap: Swap space in MB
        :param rxtx_factor: RX/TX factor
        :param is_public: Make flavor accessible to the public (default true).
        """
        flavor = self._create_flavor(ram, vcpus, disk, flavorid=flavorid,
                                     ephemeral=ephemeral, swap=swap,
                                     rxtx_factor=rxtx_factor,
                                     is_public=is_public)
        self._get_flavor(flavor.id)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["nova"]},
                    name="NovaFlavors.create_and_delete_flavor",
                    platform="openstack")
class CreateAndDeleteFlavor(utils.NovaScenario):
    def run(self, ram, vcpus, disk, flavorid="auto",
            ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
        """Create flavor and delete the flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param flavorid: ID for the flavor (optional). You can use the reserved
                         value ``"auto"`` to have Nova generate a UUID for the
                         flavor in cases where you cannot simply pass ``None``.
        :param ephemeral: Ephemeral space size in GB (default 0).
        :param swap: Swap space in MB
        :param rxtx_factor: RX/TX factor
        :param is_public: Make flavor accessible to the public (default true).
        """
        flavor = self._create_flavor(ram, vcpus, disk, flavorid=flavorid,
                                     ephemeral=ephemeral, swap=swap,
                                     rxtx_factor=rxtx_factor,
                                     is_public=is_public)
        self._delete_flavor(flavor.id)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["nova"]},
                    name="NovaFlavors.create_flavor_and_set_keys",
                    platform="openstack")
class CreateFlavorAndSetKeys(utils.NovaScenario):
    def run(self, ram, vcpus, disk, extra_specs, flavorid="auto",
            ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
        """Create flavor and set keys to the flavor.

        Measure the "nova flavor-key" command performance.
        the scenario first create a flavor,then add the extra specs to it.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param extra_specs: additional arguments for flavor set keys
        :param flavorid: ID for the flavor (optional). You can use the reserved
                         value ``"auto"`` to have Nova generate a UUID for the
                         flavor in cases where you cannot simply pass ``None``.
        :param ephemeral: Ephemeral space size in GB (default 0).
        :param swap: Swap space in MB
        :param rxtx_factor: RX/TX factor
        :param is_public: Make flavor accessible to the public (default true).
        """
        flavor = self._create_flavor(ram, vcpus, disk, flavorid=flavorid,
                                     ephemeral=ephemeral, swap=swap,
                                     rxtx_factor=rxtx_factor,
                                     is_public=is_public)
        self._set_flavor_keys(flavor, extra_specs)
