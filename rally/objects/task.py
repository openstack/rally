# Copyright 2013: Mirantis Inc.
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

import json

from rally.common import utils as rutils
from rally import consts
from rally import db


TASK_RESULT_SCHEMA = {
    "type": "object",
    "$schema": rutils.JSON_SCHEMA,
    "properties": {
        "key": {
            "type": "object",
            "properties": {
                "kw": {
                    "type": "object"
                },
                "name": {
                    "type": "string"
                },
                "pos": {
                    "type": "integer"
                },
            },
            "required": ["kw", "name", "pos"]
        },
        "sla": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {
                        "type": "string"
                    },
                    "detail": {
                        "type": "string"
                    },
                    "success": {
                        "type": "boolean"
                    }
                }
            }
        },
        "result": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "atomic_actions": {
                        "type": "object"
                    },
                    "duration": {
                        "type": "number"
                    },
                    "error": {
                        "type": "array"
                    },
                    "idle_duration": {
                        "type": "number"
                    },
                    "scenario_output": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object"
                            },
                            "errors": {
                                "type": "string"
                            },
                        },
                        "required": ["data", "errors"]
                    },
                },
                "required": ["atomic_actions", "duration", "error",
                             "idle_duration", "scenario_output"]
            },
            "minItems": 1
        },
        "load_duration": {
            "type": "number",
        },
        "full_duration": {
            "type": "number",
        },
    },
    "required": ["key", "sla", "result", "load_duration",
                 "full_duration"],
    "additionalProperties": False
}


class Task(object):
    """Represents a task object."""

    def __init__(self, task=None, **attributes):
        if task:
            self.task = task
        else:
            self.task = db.task_create(attributes)

    def __getitem__(self, key):
        return self.task[key]

    def to_dict(self):
        db_task = self.task
        deployment_name = db.deployment_get(self.task.deployment_uuid)["name"]
        db_task["deployment_name"] = deployment_name
        return db_task

    @staticmethod
    def get(uuid):
        return Task(db.task_get(uuid))

    @staticmethod
    def list(status=None, deployment=None):
        return [Task(db_task) for db_task in db.task_list(status, deployment)]

    @staticmethod
    def delete_by_uuid(uuid, status=None):
        db.task_delete(uuid, status=status)

    def _update(self, values):
        self.task = db.task_update(self.task['uuid'], values)

    def update_status(self, status):
        self._update({'status': status})

    def update_verification_log(self, log):
        self._update({'verification_log': json.dumps(log)})

    def set_failed(self, log=""):
        self._update({'failed': True,
                      'status': consts.TaskStatus.FAILED,
                      'verification_log': json.dumps(log)})

    def get_results(self):
        return db.task_result_get_all_by_uuid(self.task["uuid"])

    def append_results(self, key, value):
        db.task_result_create(self.task['uuid'], key, value)

    def delete(self, status=None):
        db.task_delete(self.task['uuid'], status=status)
