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

import collections
import threading

from rally.common import logging


LOG = logging.getLogger(__name__)


def _consumer(consume, queue):
    """Infinity worker that consumes tasks from queue.

    :param consume: method that consumes an object removed from the queue
    :param queue: deque object to popleft() objects from
    """
    cache = {}
    while True:
        if not queue:
            break
        else:
            try:
                args = queue.popleft()
            except IndexError:
                # consumed by other thread
                continue
        try:
            consume(cache, args)
        except Exception as e:
            msg = "Failed to consume a task from the queue"
            if logging.is_debug():
                LOG.exception(msg)
            else:
                LOG.warning("%s: %s" % (msg, e))


def _publisher(publish, queue):
    """Calls a publish method that fills queue with jobs.

    :param publish: method that fills the queue
    :param queue: deque object to be filled by the publish() method
    """
    try:
        publish(queue)
    except Exception as e:
        msg = "Failed to publish a task to the queue"
        if logging.is_debug():
            LOG.exception(msg)
        else:
            LOG.warning("%s: %s" % (msg, e))


def run(publish, consume, consumers_count=1):
    """Run broker.

    publish() put to queue, consume() process one element from queue.

    When publish() is finished and elements from queue are processed process
    is finished all consumers threads are cleaned.

    :param publish: Function that puts values to the queue
    :param consume: Function that processes a single value from the queue
    :param consumers_count: Number of consumers
    """
    queue = collections.deque()
    _publisher(publish, queue)

    consumers = []
    for i in range(consumers_count):
        consumer = threading.Thread(target=_consumer, args=(consume, queue))
        consumer.start()
        consumers.append(consumer)

    for consumer in consumers:
        consumer.join()
