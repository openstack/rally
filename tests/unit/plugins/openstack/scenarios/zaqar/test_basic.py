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

from rally.plugins.openstack.scenarios.zaqar import basic
from tests.unit import test

BASE = "rally.plugins.openstack.scenarios.zaqar.basic"


class ZaqarBasicTestCase(test.ScenarioTestCase):

    @mock.patch("%s.CreateQueue.generate_random_name" % BASE,
                return_value="fizbit")
    def test_create_queue(self, mock_random_name):
        scenario = basic.CreateQueue(self.context)
        scenario._queue_create = mock.MagicMock()
        scenario.run(fakearg="fake")
        scenario._queue_create.assert_called_once_with(fakearg="fake")

    @mock.patch("%s.CreateQueue.generate_random_name" % BASE,
                return_value="kitkat")
    def test_producer_consumer(self, mock_random_name):
        scenario = basic.ProducerConsumer(self.context)
        messages = [{"body": {"id": idx}, "ttl": 360} for idx
                    in range(20)]
        queue = mock.MagicMock()

        scenario._queue_create = mock.MagicMock(return_value=queue)
        scenario._messages_post = mock.MagicMock()
        scenario._messages_list = mock.MagicMock()
        scenario._queue_delete = mock.MagicMock()

        scenario.run(min_msg_count=20, max_msg_count=20, fakearg="fake")

        scenario._queue_create.assert_called_once_with(fakearg="fake")
        scenario._messages_post.assert_called_once_with(queue, messages,
                                                        20, 20)
        scenario._messages_list.assert_called_once_with(queue)
        scenario._queue_delete.assert_called_once_with(queue)
