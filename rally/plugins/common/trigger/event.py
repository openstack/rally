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


@trigger.configure(name="event")
class EventTrigger(trigger.Trigger):
    """Triggers hook on specified event and list of values."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "oneOf": [
            {
                "properties": {
                    "unit": {"enum": ["time"]},
                    "at": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {
                            "type": "integer",
                            "minimum": 0,
                        }
                    },
                },
                "required": ["unit", "at"],
                "additionalProperties": False,
            },
            {
                "properties": {
                    "unit": {"enum": ["iteration"]},
                    "at": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {
                            "type": "integer",
                            "minimum": 1,
                        }
                    },
                },
                "required": ["unit", "at"],
                "additionalProperties": False,
            },
        ]
    }

    def get_listening_event(self):
        return self.config["unit"]

    def on_event(self, event_type, value=None):
        if not (event_type == self.get_listening_event()
                and value in self.config["at"]):
            # do nothing
            return
        super(EventTrigger, self).on_event(event_type, value)
