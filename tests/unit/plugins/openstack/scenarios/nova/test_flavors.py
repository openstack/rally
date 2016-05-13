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

from rally.plugins.openstack.scenarios.nova import flavors
from tests.unit import test


@ddt.ddt
class NovaFlavorsTestCase(test.TestCase):

    def test_list_flavors(self):
        scenario = flavors.NovaFlavors()
        scenario._list_flavors = mock.Mock()
        scenario.list_flavors(detailed=True, fakearg="fakearg")
        scenario._list_flavors.assert_called_once_with(True, fakearg="fakearg")

    @ddt.data({},
              {"is_public": True},
              {"is_public": False},
              {"fakeargs": "fakeargs"},
              {"is_public": False, "fakeargs": "fakeargs"})
    @ddt.unpack
    def test_create_and_list_flavor_access(self, **kwargs):
        scenario = flavors.NovaFlavors()
        scenario._create_flavor = mock.Mock()
        scenario._list_flavor_access = mock.Mock()
        scenario.create_and_list_flavor_access(ram=100, vcpus=1, disk=1,
                                               **kwargs)
        kwargs.pop("is_public", None)
        scenario._create_flavor.assert_called_once_with(100, 1, 1,
                                                        is_public=False,
                                                        **kwargs)
        scenario._list_flavor_access.assert_called_once_with(
            scenario._create_flavor.return_value.id)

    def test_create_flavor(self):
        scenario = flavors.NovaFlavors()
        scenario._create_flavor = mock.MagicMock()
        scenario.create_flavor(ram=100, vcpus=1, disk=1, fakeargs="fakeargs")
        scenario._create_flavor.assert_called_once_with(100, 1, 1,
                                                        fakeargs="fakeargs")
