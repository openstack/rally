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

import copy

import jsonschema

from rally.common import cfg
from rally.common import logging
from rally import consts
from rally import exceptions
from rally.task import scenario


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class TaskConfig(object):
    """Version-aware wrapper around task config."""

    CONFIG_SCHEMA_V1 = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "patternProperties": {
            ".*": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "args": {"type": "object"},
                        "description": {
                            "type": "string"
                        },
                        "runner": {
                            "type": "object",
                            "properties": {"type": {"type": "string"}},
                            "required": ["type"]
                        },
                        "context": {"type": "object"},
                        "sla": {"type": "object"},
                        "hooks": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/hook"},
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        "definitions": {
            "hook": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "args": {},
                    "trigger": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "args": {},
                        },
                        "required": ["name", "args"],
                        "additionalProperties": False,
                    }
                },
                "required": ["name", "args", "trigger"],
                "additionalProperties": False,
            }
        }
    }

    CONFIG_SCHEMA_V2 = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "version": {"type": "number"},
            "title": {"type": "string", "maxLength": 128},
            "description": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },

            "subtasks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "oneOf": [
                        {"$ref": "#/definitions/subtask-workload"},
                        {"$ref": "#/definitions/subtask-workloads"}
                    ]
                }
            }
        },
        "additionalProperties": False,
        "required": ["title", "subtasks"],
        "definitions": {
            "singleEntity": {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 1,
                "patternProperties": {
                    ".*": {"type": "object"}
                }
            },
            "subtask-workload": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "maxLength": 128},
                    "group": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 255}
                    },
                    "scenario": {"$ref": "#/definitions/singleEntity"},
                    "runner": {"$ref": "#/definitions/singleEntity"},
                    "sla": {"type": "object"},
                    "hooks": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/hook"},
                    },
                    "contexts": {"type": "object"}
                },
                "additionalProperties": False,
                "required": ["title", "scenario", "runner"]
            },
            "subtask-workloads": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "group": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 255}
                    },
                    "run_in_parallel": {"type": "boolean"},
                    "workloads": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "scenario": {
                                    "$ref": "#/definitions/singleEntity"},
                                "description": {"type": "string"},
                                "runner": {
                                    "$ref": "#/definitions/singleEntity"},
                                "sla": {"type": "object"},
                                "hooks": {
                                    "type": "array",
                                    "items": {"$ref": "#/definitions/hook"},
                                },
                                "contexts": {"type": "object"}
                            },
                            "additionalProperties": False,
                            "required": ["scenario"]
                        }
                    }
                },
                "additionalProperties": False,
                "required": ["title", "workloads"]
            },
            "hook": {
                "type": "object",
                "oneOf": [
                    {
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "args": {},
                            "trigger": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "args": {},
                                },
                                "required": ["name", "args"],
                                "additionalProperties": False,
                            }
                        },
                        "required": ["name", "args", "trigger"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "action": {
                                "type": "object",
                                "minProperties": 1,
                                "maxProperties": 1,
                                "patternProperties": {".*": {}}
                            },
                            "trigger": {"$ref": "#/definitions/singleEntity"},
                            "description": {"type": "string"},
                        },
                        "required": ["action", "trigger"],
                        "additionalProperties": False
                    },
                ]
            }
        }
    }

    CONFIG_SCHEMAS = {1: CONFIG_SCHEMA_V1, 2: CONFIG_SCHEMA_V2}

    def __init__(self, config):
        """TaskConfig constructor.

        Validates and represents different versions of task configuration in
        unified form.

        :param config: Dict with configuration of specified task
        :raises Exception: in case of validation error. (This gets reraised as
            InvalidTaskException. if we raise it here as InvalidTaskException,
            then "Task config is invalid: " gets prepended to the message twice
        """
        if config is None:
            raise Exception("Input task is empty")

        self.version = self._get_version(config)
        self._validate_version()
        self._validate_json(config)

        if self.version == 1:
            config = self._adopt_task_format_v1(config)

        self.title = config.get("title", "Task")
        self.tags = config.get("tags", [])
        self.description = config.get("description")

        self.subtasks = []
        for sconf in config["subtasks"]:
            sconf = copy.deepcopy(sconf)

            # fill all missed properties of a SubTask
            sconf.setdefault("tags", [])
            sconf.setdefault("description", "")

            # port the subtask to a single format before validating
            if "workloads" not in sconf and "scenario" in sconf:
                workload = sconf
                sconf = {"title": workload.pop("title"),
                         "description": workload.pop("description"),
                         "tags": workload.pop("tags"),
                         "workloads": [workload]}

            # it is not supported feature yet, but the code expects this
            # variable
            sconf.setdefault("contexts", {})

            workloads = []
            for position, wconf in enumerate(sconf["workloads"]):
                # fill all missed properties of a Workload

                wconf["name"], wconf["args"] = list(
                    wconf["scenario"].items())[0]
                del wconf["scenario"]

                wconf["position"] = position

                if not wconf.get("description", ""):
                    try:
                        wconf["description"] = scenario.Scenario.get(
                            wconf["name"]).get_info()["title"]
                    except (exceptions.PluginNotFound,
                            exceptions.MultiplePluginsFound):
                        # let's fail an issue with loading plugin at a
                        # validation step
                        pass

                wconf.setdefault("contexts", {})

                if "runner" in wconf:
                    runner = list(wconf["runner"].items())[0]
                    wconf["runner_type"], wconf["runner"] = runner
                else:
                    wconf["runner_type"] = "serial"
                    wconf["runner"] = {}

                wconf.setdefault("sla", {"failure_rate": {"max": 0}})

                hooks = wconf.get("hooks", [])
                wconf["hooks"] = []
                for hook_cfg in hooks:
                    if "name" in hook_cfg:
                        LOG.warning("The deprecated format of hook is found. "
                                    "Check task format documentation for more "
                                    "details.")
                        trigger_cfg = hook_cfg["trigger"]
                        wconf["hooks"].append({
                            "description": hook_cfg["description"],
                            "action": (hook_cfg["name"], hook_cfg["args"]),
                            "trigger": (
                                trigger_cfg["name"], trigger_cfg["args"])})
                    else:
                        hook_cfg["action"] = list(
                            hook_cfg["action"].items())[0]
                        hook_cfg["trigger"] = list(
                            hook_cfg["trigger"].items())[0]
                        wconf["hooks"].append(hook_cfg)

                workloads.append(wconf)
            sconf["workloads"] = workloads
            self.subtasks.append(sconf)

        # if self.version == 1:
        # TODO(ikhudoshyn): Warn user about deprecated format

    @staticmethod
    def _get_version(config):
        return config.get("version", 1)

    def _validate_version(self):
        if self.version not in self.CONFIG_SCHEMAS:
            allowed = ", ".join([str(k) for k in self.CONFIG_SCHEMAS])
            msg = ("Task configuration version %s is not supported. "
                   "Supported versions: %s") % (self.version, allowed)
            raise exceptions.InvalidTaskException(msg)

    def _validate_json(self, config):
        try:
            jsonschema.validate(config, self.CONFIG_SCHEMAS[self.version])
        except Exception as e:
            raise exceptions.InvalidTaskException(str(e))

    @staticmethod
    def _adopt_task_format_v1(config):
        subtasks = []
        for name, v1_workloads in config.items():
            for v1_workload in v1_workloads:
                subtask = copy.deepcopy(v1_workload)
                subtask["scenario"] = {name: subtask.pop("args", {})}
                subtask["contexts"] = subtask.pop("context", {})
                subtask["title"] = name
                if "runner" in subtask:
                    runner_type = subtask["runner"].pop("type")
                    subtask["runner"] = {runner_type: subtask["runner"]}
                if "hooks" in subtask:
                    hooks = subtask["hooks"]
                    subtask["hooks"] = []
                    for hook_cfg in hooks:
                        trigger_cfg = hook_cfg["trigger"]
                        subtask["hooks"].append(
                            {"description": hook_cfg.get("description"),
                             "action": {
                                 hook_cfg["name"]: hook_cfg["args"]},
                             "trigger": {
                                 trigger_cfg["name"]: trigger_cfg["args"]}}
                        )
                subtasks.append(subtask)
        return {"title": "Task (adopted from task format v1)",
                "subtasks": subtasks}
