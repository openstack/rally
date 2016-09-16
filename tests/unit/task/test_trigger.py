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

"""Tests for Trigger base class."""

import ddt
import jsonschema

from rally.task import trigger
from tests.unit import test


@trigger.configure(name="dummy_trigger")
class DummyTrigger(trigger.Trigger):
    CONFIG_SCHEMA = {"type": "integer"}

    def get_configured_event_type(self):
        return "dummy"

    def is_runnable(self, value):
        return value == self.config


@ddt.ddt
class TriggerTestCase(test.TestCase):

    def setUp(self):
        super(TriggerTestCase, self).setUp()
        self.trigger = DummyTrigger(10)

    @ddt.data(({"name": "dummy_trigger", "args": 5}, True),
              ({"name": "dummy_trigger", "args": "str"}, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        if valid:
            trigger.Trigger.validate(config)
        else:
            self.assertRaises(jsonschema.ValidationError,
                              trigger.Trigger.validate, config)

    def test_get_configured_event_type(self):
        event_type = self.trigger.get_configured_event_type()
        self.assertEqual("dummy", event_type)

    @ddt.data((10, True), (1, False))
    @ddt.unpack
    def test_is_runnable(self, value, expected_result):
        result = self.trigger.is_runnable(value)
        self.assertIs(result, expected_result)
