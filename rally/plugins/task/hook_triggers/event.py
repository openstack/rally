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

from __future__ import annotations

import typing as t

from rally import consts
from rally.task import hook


@hook.configure(name="event")
class EventTrigger(hook.HookTrigger):
    """Triggers hook on specified event and list of values."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "oneOf": [
            {
                "description": "Triage hook based on specified seconds after "
                               "start of workload.",
                "properties": {
                    "unit": {"enum": ["time"]},
                    "at": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {
                            "type": "integer",
                            "minimum": 0
                        }
                    },
                },
                "required": ["unit", "at"],
                "additionalProperties": False,
            },
            {
                "description": "Triage hook based on specific iterations.",
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

    def get_listening_event(self) -> str:
        return self.config["unit"]

    def on_event(self, event_type: str, value: t.Any = None) -> bool:
        if not (event_type == self.get_listening_event()
                and value in self.config["at"]):
            # do nothing
            return False
        return super(EventTrigger, self).on_event(event_type, value)
