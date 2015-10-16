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

import mock

from rally.plugins.openstack.scenarios.ironic import utils
from tests.unit import test

IRONIC_UTILS = "rally.plugins.openstack.scenarios.ironic.utils"


class IronicScenarioTestCase(test.ScenarioTestCase):

    def test__create_node(self):
        self.admin_clients("ironic").node.create.return_value = "fake_node"
        scenario = utils.IronicScenario(self.context)
        scenario.generate_random_name = mock.Mock()

        create_node = scenario._create_node(fake_param="foo")

        self.assertEqual("fake_node", create_node)
        self.admin_clients("ironic").node.create.assert_called_once_with(
            fake_param="foo", name=scenario.generate_random_name.return_value)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "ironic.create_node")

    def test__delete_node(self):
        mock_node_delete = mock.Mock()
        self.admin_clients("ironic").node.delete = mock_node_delete
        scenario = utils.IronicScenario(self.context)
        scenario._delete_node("fake_id")

        self.admin_clients("ironic").node.delete.assert_called_once_with(
            "fake_id")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "ironic.delete_node")

    def test__list_nodes(self):
        self.admin_clients("ironic").node.list.return_value = ["fake"]
        scenario = utils.IronicScenario(self.context)
        fake_params = {
            "sort_dir": "foo1",
            "associated": "foo2",
            "sort_key": "foo3",
            "detail": True,
            "limit": "foo4",
            "maintenance": "foo5",
            "marker": "foo6"
        }
        return_nodes_list = scenario._list_nodes(**fake_params)
        self.assertEqual(["fake"], return_nodes_list)
        self.admin_clients("ironic").node.list.assert_called_once_with(
            sort_dir="foo1", associated="foo2", sort_key="foo3", detail=True,
            limit="foo4", maintenance="foo5", marker="foo6")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "ironic.list_nodes")
