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

from rally.plugins.openstack.scenarios.magnum import cluster_templates
from tests.unit import test


@ddt.ddt
class MagnumClusterTemplatesTestCase(test.TestCase):

    @ddt.data(
        {"kwargs": {}},
        {"kwargs": {"fakearg": "f"}})
    @ddt.unpack
    def test_list_cluster_templates(self, kwargs):
        scenario = cluster_templates.ListClusterTemplates()
        scenario._list_cluster_templates = mock.Mock()

        scenario.run(**kwargs)

        scenario._list_cluster_templates.assert_called_once_with(**kwargs)
