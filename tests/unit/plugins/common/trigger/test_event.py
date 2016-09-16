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

from rally.task import trigger
from tests.unit import test


def create_config(**kwargs):
    return {"name": "event", "args": kwargs}


@ddt.ddt
class EventTriggerTestCase(test.TestCase):

    def setUp(self):
        super(EventTriggerTestCase, self).setUp()
        self.trigger = trigger.Trigger.get("event")({"unit": "iteration",
                                                     "at": [1, 4, 5]})

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
            trigger.Trigger.validate(config)
        else:
            self.assertRaises(jsonschema.ValidationError,
                              trigger.Trigger.validate, config)

    def test_get_configured_event_type(self):
        event_type = self.trigger.get_configured_event_type()
        self.assertEqual("iteration", event_type)

    @ddt.data((1, True), (4, True), (5, True),
              (0, False), (2, False), (3, False), (6, False), (7, False))
    @ddt.unpack
    def test_is_runnable(self, value, expected_result):
        result = self.trigger.is_runnable(value)
        self.assertIs(result, expected_result)
