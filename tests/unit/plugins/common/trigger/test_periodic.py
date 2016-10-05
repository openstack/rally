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

from rally.plugins.common.trigger import periodic
from tests.unit import test


def create_config(**kwargs):
    return {"name": "periodic", "args": kwargs}


@ddt.ddt
class PeriodicTriggerTestCase(test.TestCase):

    def setUp(self):
        super(PeriodicTriggerTestCase, self).setUp()
        self.hook_cls = mock.MagicMock(__name__="name")
        self.trigger = periodic.PeriodicTrigger(
            {"trigger": {"name": "periodic",
                         "args": {"unit": "iteration", "step": 2}}},
            mock.MagicMock(), self.hook_cls)

    @ddt.data((create_config(unit="time", step=1), True),
              (create_config(unit="time", step=0), False),
              (create_config(unit="time", step=1, start=0), True),
              (create_config(unit="time", step=1, start=-1), False),
              (create_config(unit="time", step=1, start=0, end=1), True),
              (create_config(unit="time", step=1, start=0, end=0), False),
              (create_config(unit="time", wrong_prop=None), False),
              (create_config(unit="time"), False),
              (create_config(unit="iteration", step=1), True),
              (create_config(unit="iteration", step=0), False),
              (create_config(unit="iteration", step=1, start=1), True),
              (create_config(unit="iteration", step=1, start=0), False),
              (create_config(unit="iteration", step=1, start=1, end=1), True),
              (create_config(unit="iteration", step=1, start=1, end=0), False),
              (create_config(unit="iteration", wrong_prop=None), False),
              (create_config(unit="iteration"), False),
              (create_config(unit="wrong-unit", step=1), False),
              (create_config(step=1), False))
    @ddt.unpack
    def test_config_schema(self, config, valid):
        if valid:
            periodic.PeriodicTrigger.validate(config)
        else:
            self.assertRaises(jsonschema.ValidationError,
                              periodic.PeriodicTrigger.validate, config)

    def test_get_listening_event(self):
        event_type = self.trigger.get_listening_event()
        self.assertEqual("iteration", event_type)

    @ddt.data((1, True), (2, False), (3, True), (4, False), (5, True),
              (6, False), (7, True), (8, False), (9, True), (10, False))
    @ddt.unpack
    def test_on_event(self, value, should_call):
        self.trigger.on_event("iteration", value)
        self.assertEqual(should_call, self.hook_cls.called)

    @ddt.data((0, False), (1, False), (2, True), (3, False), (4, False),
              (5, True), (6, False), (7, False), (8, True), (9, False))
    @ddt.unpack
    def test_on_event_start_end(self, value, should_call):
        trigger = periodic.PeriodicTrigger(
            {"trigger": {"name": "periodic",
                         "args": {"unit": "time",
                                  "step": 3, "start": 2, "end": 9}}},
            mock.MagicMock(), self.hook_cls)
        trigger.on_event("time", value)
        self.assertEqual(should_call, self.hook_cls.called)
