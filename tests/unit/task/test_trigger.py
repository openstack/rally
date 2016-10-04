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
import mock

from rally.task import trigger
from tests.unit import test


@trigger.configure(name="dummy_trigger")
class DummyTrigger(trigger.Trigger):
    CONFIG_SCHEMA = {"type": "array",
                     "minItems": 1,
                     "uniqueItems": True,
                     "items": {
                         "type": "integer",
                         "minimum": 0,
                     }}

    def get_listening_event(self):
        return "dummy"

    def on_event(self, event_type, value=None):
        if value not in self.config:
            return
        super(DummyTrigger, self).on_event(event_type, value)


@ddt.ddt
class TriggerTestCase(test.TestCase):

    @ddt.data(({"name": "dummy_trigger", "args": [5]}, True),
              ({"name": "dummy_trigger", "args": ["str"]}, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        if valid:
            DummyTrigger.validate(config)
        else:
            self.assertRaises(jsonschema.ValidationError,
                              DummyTrigger.validate, config)

    def test_on_event_and_get_results(self):
        # get_results requires launched hooks, so if we want to test it, we
        # need to duplicate all calls on_event. It is redundant, so let's merge
        # test_on_event and test_get_results in one test.
        right_values = [5, 7, 12, 13]

        cfg = {"trigger": {"args": right_values}}
        task = mock.MagicMock()
        hook_cls = mock.MagicMock(__name__="fake")
        dummy_trigger = DummyTrigger(cfg, task, hook_cls)
        for i in range(0, 20):
            dummy_trigger.on_event("fake", i)

        self.assertEqual(
            [mock.call(task, {}, {"event_type": "fake", "value": i})
             for i in right_values],
            hook_cls.call_args_list)
        self.assertEqual(len(right_values),
                         hook_cls.return_value.run_async.call_count)
        hook_status = hook_cls.return_value.result.return_value["status"]
        self.assertEqual(
            {"config": cfg,
             "results": [hook_cls.return_value.result.return_value] *
                len(right_values),
             "summary": {hook_status: len(right_values)}},
            dummy_trigger.get_results())
