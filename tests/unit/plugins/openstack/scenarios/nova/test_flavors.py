# Copyright: 2015.
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

import ddt
import mock

from rally import exceptions
from rally.plugins.openstack.scenarios.nova import flavors
from tests.unit import test


@ddt.ddt
class NovaFlavorsTestCase(test.TestCase):

    def test_list_flavors(self):
        scenario = flavors.ListFlavors()
        scenario._list_flavors = mock.Mock()
        scenario.run(detailed=True, is_public=True, limit=None, marker=None,
                     min_disk=None, min_ram=None, sort_dir=None, sort_key=None)
        scenario._list_flavors.assert_called_once_with(
            detailed=True, is_public=True, limit=None, marker=None,
            min_disk=None, min_ram=None, sort_dir=None, sort_key=None)

    def test_create_and_list_flavor_access(self):
        # Common parameters
        ram = 100
        vcpus = 1
        disk = 1

        scenario = flavors.CreateAndListFlavorAccess()
        scenario._create_flavor = mock.Mock()
        scenario._list_flavor_access = mock.Mock()

        # Positive case:
        scenario.run(
            ram, vcpus, disk, ephemeral=0, flavorid="auto",
            is_public=False, rxtx_factor=1.0, swap=0)
        scenario._create_flavor.assert_called_once_with(
            ram, vcpus, disk, ephemeral=0, flavorid="auto",
            is_public=False, rxtx_factor=1.0, swap=0)
        scenario._list_flavor_access.assert_called_once_with(
            scenario._create_flavor.return_value.id)

        # Negative case1: flavor wasn't created
        scenario._create_flavor.return_value = None
        self.assertRaises(exceptions.RallyAssertionError, scenario.run,
                          ram, vcpus, disk, ephemeral=0, flavorid="auto",
                          is_public=False, rxtx_factor=1.0, swap=0)
        scenario._create_flavor.assert_called_with(
            ram, vcpus, disk, ephemeral=0, flavorid="auto",
            is_public=False, rxtx_factor=1.0, swap=0)

    def test_create_flavor_add_tenant_access(self):
        flavor = mock.MagicMock()
        context = {"user": {"tenant_id": "fake"},
                   "tenant": {"id": "fake"}}
        scenario = flavors.CreateFlavorAndAddTenantAccess()
        scenario.context = context
        scenario.generate_random_name = mock.MagicMock()
        scenario._create_flavor = mock.MagicMock(return_value=flavor)
        scenario._add_tenant_access = mock.MagicMock()

        # Positive case:
        scenario.run(ram=100, vcpus=1, disk=1, ephemeral=0,
                     flavorid="auto", is_public=True, rxtx_factor=1.0, swap=0)

        scenario._create_flavor.assert_called_once_with(
            100, 1, 1, ephemeral=0, flavorid="auto", is_public=True,
            rxtx_factor=1.0, swap=0)
        scenario._add_tenant_access.assert_called_once_with(flavor.id,
                                                            "fake")

        # Negative case1: flavor wasn't created
        scenario._create_flavor.return_value = None
        self.assertRaises(exceptions.RallyAssertionError, scenario.run,
                          100, 1, 1, ephemeral=0, flavorid="auto",
                          is_public=True, rxtx_factor=1.0, swap=0)
        scenario._create_flavor.assert_called_with(
            100, 1, 1, ephemeral=0, flavorid="auto", is_public=True,
            rxtx_factor=1.0, swap=0)

    def test_create_flavor(self):
        scenario = flavors.CreateFlavor()
        scenario._create_flavor = mock.MagicMock()
        scenario.run(ram=100, vcpus=1, disk=1, ephemeral=0, flavorid="auto",
                     is_public=True, rxtx_factor=1.0, swap=0)
        scenario._create_flavor.assert_called_once_with(
            100, 1, 1, ephemeral=0,
            flavorid="auto", is_public=True, rxtx_factor=1.0, swap=0)

    def test_create_and_get_flavor(self, **kwargs):
        scenario = flavors.CreateAndGetFlavor()
        scenario._create_flavor = mock.Mock()
        scenario._get_flavor = mock.Mock()
        scenario.run(ram=100, vcpus=1, disk=1, ephemeral=0, flavorid="auto",
                     is_public=True, rxtx_factor=1.0, swap=0)

        scenario._create_flavor.assert_called_once_with(
            100, 1, 1, ephemeral=0, flavorid="auto", is_public=True,
            rxtx_factor=1.0, swap=0)
        scenario._get_flavor.assert_called_once_with(
            scenario._create_flavor.return_value.id)

    def test_create_and_delete_flavor(self):
        scenario = flavors.CreateAndDeleteFlavor()
        scenario._create_flavor = mock.Mock()
        scenario._delete_flavor = mock.Mock()
        scenario.run(ram=100, vcpus=1, disk=1, ephemeral=0, flavorid="auto",
                     is_public=True, rxtx_factor=1.0, swap=0)

        scenario._create_flavor.assert_called_once_with(
            100, 1, 1, ephemeral=0, flavorid="auto", is_public=True,
            rxtx_factor=1.0, swap=0)
        scenario._delete_flavor.assert_called_once_with(
            scenario._create_flavor.return_value.id)

    def test_create_flavor_and_set_keys(self):
        scenario = flavors.CreateFlavorAndSetKeys()
        scenario._create_flavor = mock.MagicMock()
        scenario._set_flavor_keys = mock.MagicMock()
        specs_args = {"fakeargs": "foo"}
        scenario.run(
            ram=100, vcpus=1, disk=1, extra_specs=specs_args,
            ephemeral=0, flavorid="auto", is_public=True,
            rxtx_factor=1.0, swap=0)

        scenario._create_flavor.assert_called_once_with(
            100, 1, 1, ephemeral=0, flavorid="auto",
            is_public=True, rxtx_factor=1.0, swap=0)
        scenario._set_flavor_keys.assert_called_once_with(
            scenario._create_flavor.return_value, specs_args)
