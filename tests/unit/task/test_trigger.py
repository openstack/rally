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

import mock

from rally.task import trigger
from tests.unit import test


class TriggerTestCase(test.TestCase):

    def setUp(self):
        super(TriggerTestCase, self).setUp()

        @trigger.hook.configure(self.id())
        class DummyTrigger(trigger.Trigger):
            def get_listening_event(self):
                return "dummy"

        self.addCleanup(DummyTrigger.unregister)
        self.DummyTrigger = DummyTrigger

    @mock.patch("rally.task.trigger.LOG.warning")
    def test_warning(self, mock_log_warning):
        self.DummyTrigger({"trigger": (self.id(), {})}, None, None)

        mock_log_warning.assert_called_once_with(
            "Please contact Rally plugin maintainer. The plugin '%s'"
            " inherits the deprecated base class(Trigger), "
            "`rally.task.hook.HookTrigger` should be used instead." %
            self.id())

    def test_context(self):
        action_name = "mega_action"
        action_cfg = {"action_arg": "action_value"}
        trigger_name = self.id()
        trigger_cfg = {"trigger_arg": "trigger_value"}
        descr = "descr"

        trigger_obj = self.DummyTrigger({
            "trigger": (trigger_name, trigger_cfg),
            "action": (action_name, action_cfg),
            "description": descr}, None, None)

        self.assertEqual(
            {"name": action_name,
             "args": action_cfg,
             "trigger": {"name": trigger_name,
                         "args": trigger_cfg},
             "description": descr}, trigger_obj.context)
