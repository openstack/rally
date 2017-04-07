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

    @mock.patch("%s.utils.wait_for_status" % IRONIC_UTILS)
    def test__create_node(self, mock_wait_for_status):
        self.admin_clients("ironic").node.create.return_value = "fake_node"
        scenario = utils.IronicScenario(self.context)
        scenario.generate_random_name = mock.Mock()

        scenario._create_node(driver="fake", properties="fake_prop",
                              fake_param="foo")

        self.admin_clients("ironic").node.create.assert_called_once_with(
            driver="fake", properties="fake_prop", fake_param="foo",
            name=scenario.generate_random_name.return_value)
        self.assertTrue(mock_wait_for_status.called)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "ironic.create_node")

    @mock.patch("%s.utils.wait_for_status" % IRONIC_UTILS)
    def test__delete_node(self, mock_wait_for_status):
        mock_node_delete = mock.Mock()
        self.admin_clients("ironic").node.delete = mock_node_delete
        scenario = utils.IronicScenario(self.context)
        scenario._delete_node(mock.Mock(uuid="fake_id"))
        self.assertTrue(mock_wait_for_status.called)

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
            "detail": True,
            "maintenance": "foo5"
        }
        return_nodes_list = scenario._list_nodes(**fake_params)
        self.assertEqual(["fake"], return_nodes_list)
        self.admin_clients("ironic").node.list.assert_called_once_with(
            sort_dir="foo1", associated="foo2", detail=True,
            maintenance="foo5")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "ironic.list_nodes")
