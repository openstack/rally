# Copyright (c) 2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.openstack.scenarios.zaqar import utils
from tests.unit import fakes
from tests.unit import test

UTILS = "rally.plugins.openstack.scenarios.zaqar.utils."


class ZaqarScenarioTestCase(test.ScenarioTestCase):

    @mock.patch(UTILS + "ZaqarScenario.generate_random_name",
                return_value="kitkat")
    def test_queue_create(self, mock_generate_random_name):
        scenario = utils.ZaqarScenario(self.context)
        result = scenario._queue_create(fakearg="fakearg")

        self.assertEqual(self.clients("zaqar").queue.return_value, result)
        self.clients("zaqar").queue.assert_called_once_with("kitkat",
                                                            fakearg="fakearg")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "zaqar.create_queue")

    def test_queue_delete(self):
        queue = fakes.FakeQueue()
        queue.delete = mock.MagicMock()

        scenario = utils.ZaqarScenario(context=self.context)
        scenario._queue_delete(queue)
        queue.delete.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "zaqar.delete_queue")

    def test_messages_post(self):
        queue = fakes.FakeQueue()
        queue.post = mock.MagicMock()

        messages = [{"body": {"id": "one"}, "ttl": 100},
                    {"body": {"id": "two"}, "ttl": 120},
                    {"body": {"id": "three"}, "ttl": 140}]
        min_msg_count = max_msg_count = len(messages)

        scenario = utils.ZaqarScenario(context=self.context)
        scenario._messages_post(queue, messages, min_msg_count, max_msg_count)
        queue.post.assert_called_once_with(messages)

    def test_messages_list(self):
        queue = fakes.FakeQueue()
        queue.messages = mock.MagicMock()

        scenario = utils.ZaqarScenario(context=self.context)
        scenario._messages_list(queue)
        queue.messages.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "zaqar.list_messages")
