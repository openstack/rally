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

import mock

from rally import exceptions
from rally.plugins.openstack.scenarios.ceilometer import resources
from tests.unit import test


class CeilometerResourcesTestCase(test.ScenarioTestCase):
    def test_list_resources(self):
        scenario = resources.CeilometerResource(self.context)
        scenario._list_resources = mock.MagicMock()
        scenario.list_resources()
        scenario._list_resources.assert_called_once_with()

    def test_get_tenant_resources(self):
        scenario = resources.CeilometerResource(self.context)
        resource_list = ["id1", "id2", "id3", "id4"]
        context = {"user": {"tenant_id": "fake"},
                   "tenant": {"id": "fake", "resources": resource_list}}
        scenario.context = context
        scenario._get_resource = mock.MagicMock()
        scenario.get_tenant_resources()
        for resource_id in resource_list:
            scenario._get_resource.assert_any_call(resource_id)

    def test_get_tenant_resources_with_exception(self):
        scenario = resources.CeilometerResource(self.context)
        resource_list = []
        context = {"user": {"tenant_id": "fake"},
                   "tenant": {"id": "fake", "resources": resource_list}}
        scenario.context = context
        self.assertRaises(exceptions.NotFoundException,
                          scenario.get_tenant_resources)
