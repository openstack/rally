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

import random

from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.zaqar import utils as zutils
from rally.task import validation


class ZaqarBasic(zutils.ZaqarScenario):
    """Benchmark scenarios for Zaqar."""

    @validation.number("name_length", minval=10)
    @scenario.configure(context={"cleanup": ["zaqar"]})
    def create_queue(self, name_length=10, **kwargs):
        """Create a Zaqar queue with a random name.

        :param name_length: length of generated (random) part of name
        :param kwargs: other optional parameters to create queues like
                       "metadata"
        """
        self._queue_create(name_length=name_length, **kwargs)

    @validation.number("name_length", minval=10)
    @scenario.configure(context={"cleanup": ["zaqar"]})
    def producer_consumer(self, name_length=10,
                          min_msg_count=50, max_msg_count=200, **kwargs):
        """Serial message producer/consumer.

        Creates a Zaqar queue with random name, sends a set of messages
        and then retrieves an iterator containing those.

        :param name_length: length of generated (random) part of name
        :param min_msg_count: min number of messages to be posted
        :param max_msg_count: max number of messages to be posted
        :param kwargs: other optional parameters to create queues like
                       "metadata"
        """

        queue = self._queue_create(name_length=name_length, **kwargs)
        msg_count = random.randint(min_msg_count, max_msg_count)
        messages = [{"body": {"id": idx}, "ttl": 360} for idx
                    in range(msg_count)]
        self._messages_post(queue, messages, min_msg_count, max_msg_count)
        self._messages_list(queue)
        self._queue_delete(queue)
