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


"""Scenarios for Nova flavors."""


LOG = logging.getLogger(__name__)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(name="NovaFlavors.list_flavors")
class ListFlavors(utils.NovaScenario):

    def run(self, detailed=True, **kwargs):
        """List all flavors.

        Measure the "nova flavor-list" command performance.

        :param detailed: True if the flavor listing
                         should contain detailed information

        :param kwargs: Optional additional arguments for flavor listing
        """
        self._list_flavors(detailed, **kwargs)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaFlavors.create_and_list_flavor_access")
class CreateAndListFlavorAccess(utils.NovaScenario):

    def run(self, ram, vcpus, disk, **kwargs):
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
        self.assertTrue(flavor)

        self._list_flavor_access(flavor.id)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaFlavors.create_flavor_and_add_tenant_access")
class CreateFlavorAndAddTenantAccess(utils.NovaScenario):

    def run(self, ram, vcpus, disk, **kwargs):
        """Create a flavor and Add flavor access for the given tenant.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation
        """
        flavor = self._create_flavor(ram, vcpus, disk, **kwargs)
        self.assertTrue(flavor)
        self._add_tenant_access(flavor.id, self.context["tenant"]["id"])


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaFlavors.create_flavor")
class CreateFlavor(utils.NovaScenario):

    def run(self, ram, vcpus, disk, **kwargs):
        """Create a flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation
        """
        self._create_flavor(ram, vcpus, disk, **kwargs)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaFlavors.create_and_get_flavor")
class CreateAndGetFlavor(utils.NovaScenario):
    """Scenario for create and get flavor."""

    def run(self, ram, vcpus, disk, **kwargs):
        """Create flavor and get detailed information of the flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation

        """
        flavor = self._create_flavor(ram, vcpus, disk, **kwargs)
        self._get_flavor(flavor.id)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaFlavors.create_and_delete_flavor")
class CreateAndDeleteFlavor(utils.NovaScenario):
    def run(self, ram, vcpus, disk, **kwargs):
        """Create flavor and delete the flavor.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation

        """
        flavor = self._create_flavor(ram, vcpus, disk, **kwargs)
        self._delete_flavor(flavor.id)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["nova"]},
                    name="NovaFlavors.create_flavor_and_set_keys")
class CreateFlavorAndSetKeys(utils.NovaScenario):
    def run(self, ram, vcpus, disk, extra_specs, **kwargs):
        """Create flavor and set keys to the flavor.

        Measure the "nova flavor-key" command performance.
        the scenario first create a flavor,then add the extra specs to it.

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param extra_specs: additional arguments for flavor set keys
        :param kwargs: Optional additional arguments for flavor creation
        """
        flavor = self._create_flavor(ram, vcpus, disk, **kwargs)
        self._set_flavor_keys(flavor, extra_specs)
