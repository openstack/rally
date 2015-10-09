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

from rally.plugins.openstack.scenarios.fuel import nodes
from tests.unit import test


class FuelNodesTestCase(test.TestCase):

    context = {"fuel": {"environments": ["1"]}}

    def test_add_and_remove_node(self):
        scenario = nodes.FuelNodes(self.context)
        scenario._list_node_ids = mock.Mock(return_value=["1"])
        scenario._node_is_assigned = mock.Mock(return_value=False)
        scenario._add_node = mock.Mock()
        scenario._remove_node = mock.Mock()

        scenario.add_and_remove_node(node_roles="some_role")

        scenario._list_node_ids.assert_called_once_with()
        scenario._node_is_assigned.assert_called_once_with("1")
        scenario._add_node.assert_called_once_with("1", ["1"], "some_role")
        scenario._remove_node.assert_called_once_with("1", "1")

    def test_add_and_remove_nodes_error(self):
        scenario = nodes.FuelNodes(self.context)
        scenario._list_node_ids = mock.Mock(return_value=["1"])
        scenario._node_is_assigned = mock.Mock(return_value=True)
        scenario._add_node = mock.Mock()
        scenario._remove_node = mock.Mock()

        self.assertRaises(RuntimeError,
                          scenario.add_and_remove_node,
                          node_roles="some_role")
