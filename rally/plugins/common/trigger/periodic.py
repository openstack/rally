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

from rally import consts
from rally.task import trigger


@trigger.configure(name="periodic")
class PeriodicTrigger(trigger.Trigger):
    """Periodically triggers hook with specified range and step."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "oneOf": [
            {
                "properties": {
                    "unit": {"enum": ["time"]},
                    "start": {"type": "integer", "minimum": 0},
                    "end": {"type": "integer", "minimum": 1},
                    "step": {"type": "integer", "minimum": 1},
                },
                "required": ["unit", "step"],
                "additionalProperties": False,
            },
            {
                "properties": {
                    "unit": {"enum": ["iteration"]},
                    "start": {"type": "integer", "minimum": 1},
                    "end": {"type": "integer", "minimum": 1},
                    "step": {"type": "integer", "minimum": 1},
                },
                "required": ["unit", "step"],
                "additionalProperties": False,
            },
        ]
    }

    def __init__(self, context, task, hook_cls):
        super(PeriodicTrigger, self).__init__(context, task, hook_cls)
        self.config.setdefault(
            "start", 0 if self.config["unit"] == "time" else 1)
        self.config.setdefault("end", float("Inf"))

    def get_listening_event(self):
        return self.config["unit"]

    def on_event(self, event_type, value=None):
        if not (event_type == self.get_listening_event() and
                self.config["start"] <= value <= self.config["end"] and
                (value - self.config["start"]) % self.config["step"] == 0):
            # do nothing
            return
        super(PeriodicTrigger, self).on_event(event_type, value)
