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

from rally.plugins.openstack import scenario
from rally.task import atomic


class ZaqarScenario(scenario.OpenStackScenario):
    """Base class for Zaqar scenarios with basic atomic actions."""

    @atomic.action_timer("zaqar.create_queue")
    def _queue_create(self, **kwargs):
        """Create a Zaqar queue with random name.

        :param kwargs: other optional parameters to create queues like
                       "metadata"
        :returns: Zaqar queue instance
        """
        name = self.generate_random_name()
        return self.clients("zaqar").queue(name, **kwargs)

    @atomic.action_timer("zaqar.delete_queue")
    def _queue_delete(self, queue):
        """Removes a Zaqar queue.

        :param queue: queue to remove
        """

        queue.delete()

    def _messages_post(self, queue, messages, min_msg_count, max_msg_count):
        """Post a list of messages to a given Zaqar queue.

        :param queue: post the messages to queue
        :param messages: messages to post
        :param min_msg_count: minimum number of messages
        :param max_msg_count: maximum number of messages
        """
        with atomic.ActionTimer(self, "zaqar.post_between_%s_and_%s_messages" %
                                (min_msg_count, max_msg_count)):
            queue.post(messages)

    @atomic.action_timer("zaqar.list_messages")
    def _messages_list(self, queue):
        """Gets messages from a given Zaqar queue.

        :param queue: get messages from queue
        :returns: messages iterator
        """

        return queue.messages()
