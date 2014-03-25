# Copyright 2013: Mirantis Inc.
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

from rally.benchmark.scenarios.cinder import utils
from tests.benchmark.scenarios import test_utils
from tests import test

CINDER_UTILS = "rally.benchmark.scenarios.cinder.utils"


class CinderScenarioTestCase(test.TestCase):

    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions_time, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(CINDER_UTILS + '.CinderScenario.clients')
    def test__list_volumes(self, mock_clients):
        volumes_list = mock.Mock()
        mock_clients("cinder").volumes.list.return_value = volumes_list
        scenario = utils.CinderScenario()
        return_volumes_list = scenario._list_volumes()
        self.assertEqual(volumes_list, return_volumes_list)
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'cinder.list_volumes')
