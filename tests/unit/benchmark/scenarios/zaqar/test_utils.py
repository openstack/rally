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

from rally.benchmark.scenarios.zaqar import utils
from tests.unit import fakes
from tests.unit import test

UTILS = "rally.benchmark.scenarios.zaqar.utils."


class ZaqarScenarioTestCase(test.TestCase):

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = atomic_actions.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(UTILS + "ZaqarScenario._generate_random_name")
    def test_queue_create(self, mock_gen_name):
        name = "kitkat"
        mock_gen_name.return_value = name

        queue = {}
        fake_zaqar = fakes.FakeZaqarClient()
        fake_zaqar.queue = mock.MagicMock(return_value=queue)

        fake_clients = fakes.FakeClients()
        fake_clients._zaqar = fake_zaqar
        scenario = utils.ZaqarScenario(clients=fake_clients)

        result = scenario._queue_create(name_length=10)

        self.assertEqual(queue, result)

        fake_zaqar.queue.assert_called_once_with("kitkat")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'zaqar.create_queue')