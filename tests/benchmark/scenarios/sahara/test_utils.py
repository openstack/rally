# Copyright 2014: Mirantis Inc.
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

from rally.benchmark.scenarios.sahara import utils
from tests.benchmark.scenarios import test_utils
from tests import test


SAHARA_UTILS = 'rally.benchmark.scenarios.sahara.utils'


class SaharaNodeGroupTemplatesScenarioTestCase(test.TestCase):

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_list_node_group_templates(self, mock_clients):
        ngts = []
        mock_clients("sahara").node_group_templates.list.return_value = ngts

        scenario = utils.SaharaScenario()
        return_ngts_list = scenario._list_node_group_templates()

        self.assertEqual(ngts, return_ngts_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'sahara.list_node_group_templates')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario._generate_random_name',
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_create_node_group_templates(self, mock_clients, mock_random_name):

        scenario = utils.SaharaScenario()
        mock_processes = {
            "test_plugin": {
                "test_version": {
                    "master": ["p1"],
                    "worker": ["p2"]
                }
            }
        }

        scenario.NODE_PROCESSES = mock_processes

        scenario._create_master_node_group_template(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version"
        )
        scenario._create_worker_node_group_template(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version"
        )

        create_calls = [
            mock.call(
                name="random_name",
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_processes=["p1"]),
            mock.call(
                name="random_name",
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_processes=["p2"]
            )]
        mock_clients("sahara").node_group_templates.create.assert_has_calls(
            create_calls)

        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            'sahara.create_master_node_group_template')
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            'sahara.create_worker_node_group_template')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_delete_node_group_templates(self, mock_clients):

        scenario = utils.SaharaScenario()
        ng = mock.MagicMock(id=42)

        scenario._delete_node_group_template(ng)

        delete_mock = mock_clients("sahara").node_group_templates.delete
        delete_mock.assert_called_once_with(42)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'sahara.delete_node_group_template')
