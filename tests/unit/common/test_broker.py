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

import mock

from rally.common import broker
from tests.unit import test


class BrokerTestCase(test.TestCase):

    def test__publisher(self):
        mock_publish = mock.MagicMock()
        queue = collections.deque()
        broker._publisher(mock_publish, queue)
        mock_publish.assert_called_once_with(queue)

    def test__publisher_fails(self):
        mock_publish = mock.MagicMock(side_effect=Exception())
        queue = collections.deque()
        broker._publisher(mock_publish, queue)

    def test__consumer(self):
        queue = collections.deque([1, 2, 3])
        mock_consume = mock.MagicMock()
        broker._consumer(mock_consume, queue)
        self.assertEqual(3, mock_consume.call_count)
        self.assertEqual(0, len(queue))

    def test__consumer_cache(self):
        cache_keys_history = []

        def consume(cache, item):
            cache[item] = True
            cache_keys_history.append(list(cache))

        queue = collections.deque([1, 2, 3])
        broker._consumer(consume, queue)
        self.assertEqual([[1], [1, 2], [1, 2, 3]], cache_keys_history)

    def test__consumer_fails(self):
        queue = collections.deque([1, 2, 3])
        mock_consume = mock.MagicMock(side_effect=Exception())
        broker._consumer(mock_consume, queue)
        self.assertEqual(0, len(queue))

    @mock.patch("rally.common.broker.LOG")
    def test__consumer_indexerror(self, mock_log):
        consume = mock.Mock()
        consume.side_effect = IndexError()
        queue = collections.deque([1, 2, 3])
        broker._consumer(consume, queue)
        self.assertTrue(mock_log.warning.called)
        self.assertFalse(queue)
        expected = [mock.call({}, 1), mock.call({}, 2), mock.call({}, 3)]
        self.assertEqual(expected, consume.mock_calls)

    def test_run(self):

        def publish(queue):
            queue.append(1)
            queue.append(2)
            queue.append(3)

        consumed = set()

        def consume(cache, item):
            consumed.add(item)

        consumer_count = 2
        broker.run(publish, consume, consumer_count)
        self.assertEqual(set([1, 2, 3]), consumed)
