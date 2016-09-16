# Copyright 2016: Mirantis Inc.
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

import ddt
import jsonschema
import mock

from rally.plugins.common.trigger import event
from tests.unit import test


def create_config(**kwargs):
    return {"name": "event", "args": kwargs}


@ddt.ddt
class EventTriggerTestCase(test.TestCase):

    def setUp(self):
        super(EventTriggerTestCase, self).setUp()
        self.hook_cls = mock.MagicMock(__name__="name")
        self.trigger = event.EventTrigger(
            {"trigger": {"name": "event",
                         "args": {"unit": "iteration", "at": [1, 4, 5]}}},
            mock.MagicMock(), self.hook_cls)

    @ddt.data((create_config(unit="time", at=[0, 3, 5]), True),
              (create_config(unit="time", at=[2, 2]), False),
              (create_config(unit="time", at=[-1]), False),
              (create_config(unit="time", at=[1.5]), False),
              (create_config(unit="time", at=[]), False),
              (create_config(unit="time", wrong_prop=None), False),
              (create_config(unit="time"), False),
              (create_config(unit="iteration", at=[1, 5, 13]), True),
              (create_config(unit="iteration", at=[1, 1]), False),
              (create_config(unit="iteration", at=[0]), False),
              (create_config(unit="iteration", at=[-1]), False),
              (create_config(unit="iteration", at=[1.5]), False),
              (create_config(unit="iteration", at=[]), False),
              (create_config(unit="iteration", wrong_prop=None), False),
              (create_config(unit="iteration"), False),
              (create_config(unit="wrong-unit", at=[1, 2, 3]), False),
              (create_config(at=[1, 2, 3]), False))
    @ddt.unpack
    def test_config_schema(self, config, valid):
        if valid:
            event.EventTrigger.validate(config)
        else:
            self.assertRaises(jsonschema.ValidationError,
                              event.EventTrigger.validate, config)

    def test_get_listening_event(self):
        event_type = self.trigger.get_listening_event()
        self.assertEqual("iteration", event_type)

    @ddt.data((1, True), (4, True), (5, True),
              (0, False), (2, False), (3, False), (6, False), (7, False))
    @ddt.unpack
    def test_on_event(self, value, should_call):
        self.trigger.on_event("iteration", value)
        self.assertEqual(should_call, self.hook_cls.called)
