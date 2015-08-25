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

from rally.common import costilius
from rally.task import atomic
from tests.unit import test


class ActionTimerMixinTestCase(test.TestCase):

    def test_atomic_actions(self):
        inst = atomic.ActionTimerMixin()
        self.assertEqual(inst._atomic_actions, inst.atomic_actions())


class AtomicActionTestCase(test.TestCase):

    @mock.patch("time.time", side_effect=[1, 3, 6, 10, 15, 21])
    def test_action_timer_context(self, mock_time):
        inst = atomic.ActionTimerMixin()

        with atomic.ActionTimer(inst, "test"):
            with atomic.ActionTimer(inst, "test"):
                with atomic.ActionTimer(inst, "some"):
                    pass

        expected = [("test", 20), ("test (2)", 12), ("some", 4)]
        self.assertEqual(costilius.OrderedDict(expected),
                         inst.atomic_actions())

    @mock.patch("time.time", side_effect=[1, 3])
    def test_action_timer_decorator(self, mock_time):

        class Some(atomic.ActionTimerMixin):

            @atomic.action_timer("some")
            def some_func(self, a, b):
                return a + b

        inst = Some()
        self.assertEqual(5, inst.some_func(2, 3))
        self.assertEqual(costilius.OrderedDict({"some": 2}),
                         inst.atomic_actions())
