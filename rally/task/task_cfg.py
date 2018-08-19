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

import collections
import copy

import jsonschema
import six

from rally.common import cfg
from rally.common import logging
from rally import consts
from rally import exceptions
from rally.task import scenario


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class TaskConfig(object):
    """Version-aware wrapper around task config."""

    def __init__(self, config):
        """TaskConfig constructor.

        Validates and represents different versions of task configuration in
        unified form.

        :param config: Dict with configuration of specified task
        :raises InvalidTaskException: in case of validation error
        :raises Exception: in case of some unexpected things
        """
        if config is None:
            raise exceptions.InvalidTaskException("It is empty")
        elif not isinstance(config, dict):
            raise exceptions.InvalidTaskException("It is not a dict")

        self.version = str(config.get("version", 1))

        processors = {}
        for name in dir(self):
            if not name.startswith("_process_"):
                continue
            method = getattr(self, name)
            if callable(method):
                version = name[9:].replace("_", ".")
                processors[version] = method

        if self.version not in processors:
            msg = ("Task configuration version %s is not supported. "
                   "Supported versions: %s" %
                   (self.version, ", ".join(processors)))
            raise exceptions.InvalidTaskException(msg)

        config = processors[self.version](config)

        self.title = config.get("title", "Task")
        self.tags = config.get("tags", [])
        self.description = config.get("description", "")

        self.subtasks = []
        for sconf in config["subtasks"]:
            sconf = copy.deepcopy(sconf)

            # fill all missed properties of a SubTask
            sconf.setdefault("tags", [])
            sconf.setdefault("description", "")

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
                    hook_cfg["action"] = list(hook_cfg["action"].items())[0]
                    hook_cfg["trigger"] = list(hook_cfg["trigger"].items())[0]
                    wconf["hooks"].append(hook_cfg)

                workloads.append(wconf)
            sconf["workloads"] = workloads
            self.subtasks.append(sconf)

    def to_dict(self):
        """Returns a valid task config dictionary of the latest version."""
        task = collections.OrderedDict({"version": 2})
        task["title"] = self.title
        task["description"] = self.description
        task["tags"] = self.tags
        task["subtasks"] = []
        for subtask in self.subtasks:
            subtask = copy.deepcopy(subtask)
            # we do not allow to setup this property yet
            del subtask["contexts"]
            for w in subtask["workloads"]:
                # it is inner field, hope we will remove it someday
                del w["position"]

                w["scenario"] = {w.pop("name"): w.pop("args")}
                w["runner"] = {w.pop("runner_type"): w["runner"]}
                w["hooks"] = [{"description": h.get("description", ""),
                               "action": dict([h["action"]]),
                               "trigger": dict([h["trigger"]])}
                              for h in w["hooks"]]
            task["subtasks"].append(subtask)
        return task

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

    def _process_1(self, config):
        try:
            jsonschema.validate(config, self.CONFIG_SCHEMA_V1)
        except jsonschema.ValidationError as e:
            raise exceptions.InvalidTaskException(str(e))

        subtasks = []
        for name, v1_workloads in config.items():
            workloads = []
            for v1_workload in v1_workloads:
                v2_workload = copy.deepcopy(v1_workload)
                v2_workload["scenario"] = {name: v2_workload.pop("args", {})}
                v2_workload["contexts"] = v2_workload.pop("context", {})
                if "runner" in v2_workload:
                    runner_type = v2_workload["runner"].pop("type")
                    v2_workload["runner"] = {
                        runner_type: v2_workload["runner"]}
                if "hooks" in v2_workload:
                    hooks = v2_workload["hooks"]
                    v2_workload["hooks"] = []
                    for hook_cfg in hooks:
                        trigger_cfg = hook_cfg["trigger"]
                        v2_workload["hooks"].append(
                            {"description": hook_cfg.get("description"),
                             "action": {
                                 hook_cfg["name"]: hook_cfg["args"]},
                             "trigger": {
                                 trigger_cfg["name"]: trigger_cfg["args"]}}
                        )
                workloads.append(v2_workload)
            subtasks.append({
                "title": name,
                "workloads": workloads,
            })

        return {"title": "Task (adopted from task format v1)",
                "subtasks": subtasks}

    CONFIG_SCHEMA_V2_SINGLE_ENTITY = {
        "type": "object",
        "description": "An object with a single property.",
        "minProperties": 1,
        "maxProperties": 1,
        "patternProperties": {
            ".*": {"type": "object"}
        }
    }

    CONFIG_SCHEMA_V2_HOOK = {
        "type": "object",
        "properties": {
            "action": {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 1,
                "patternProperties": {".*": {}}
            },
            "trigger": CONFIG_SCHEMA_V2_SINGLE_ENTITY,
            "description": {"type": "string"},
        },
        "required": ["action", "trigger"],
        "additionalProperties": False
    }

    CONFIG_SCHEMA_V2_SUBTASK_SIMPLE = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "title": {"type": "string", "maxLength": 128},
            "group": {"type": "string"},
            "description": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string", "maxLength": 255}
            },
            "scenario": CONFIG_SCHEMA_V2_SINGLE_ENTITY,
            "runner": CONFIG_SCHEMA_V2_SINGLE_ENTITY,
            "sla": {"type": "object"},
            "hooks": {
                "type": "array",
                "items": CONFIG_SCHEMA_V2_HOOK,
            },
            "contexts": {"type": "object"}
        },
        "additionalProperties": False,
        "required": ["title", "scenario"],
    }

    CONFIG_SCHEMA_V2_SUBTASK_COMPLEX = {
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
                        "scenario": CONFIG_SCHEMA_V2_SINGLE_ENTITY,
                        "description": {"type": "string"},
                        "runner": CONFIG_SCHEMA_V2_SINGLE_ENTITY,
                        "sla": {"type": "object"},
                        "hooks": {
                            "type": "array",
                            "items": CONFIG_SCHEMA_V2_HOOK,
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
    }

    V2_TOP_ALLOWED_KEYS = [
        "title", "version", "description", "tags", "subtasks"]
    V2_TOP_REQUIRED_KEYS = ["title", "version", "subtasks"]

    @staticmethod
    def _check_title(title, identifier=None):
        identifier = " of %s" % identifier if identifier else ""
        if not isinstance(title, (six.text_type, six.string_types)):
            raise exceptions.InvalidTaskException(
                "Title%s should be a string, but '%s' is found." %
                (identifier, type(title).__name__))

        if len(title) > 255:
            raise exceptions.InvalidTaskException(
                "Title%s should not be longer then 254 char. Use 'description'"
                " field for longer text."
                % identifier)

    @staticmethod
    def _check_tags(tags, identifier=None):
        identifier = " of %s" % identifier if identifier else ""
        if not isinstance(tags, list):
            raise exceptions.InvalidTaskException(
                "Tags%s should be an array(list) of strings, but '%s' is "
                "found."
                % (identifier, type(tags).__name__))

        for tag in tags:
            if not isinstance(tag, (six.text_type, six.string_types)):
                raise exceptions.InvalidTaskException(
                    "Tag '%s'%s should be a string, but '%s' is found." %
                    (tag, identifier, type(tag).__name__))

            if len(tag) > 255:
                raise exceptions.InvalidTaskException(
                    "Tag '%s'%s should not be longer then 254 char."
                    % (tag, identifier))

    def _process_2(self, config):
        # task format v2 is quite complex. To increase UX we need to
        # validate it by steps

        top_keys = set(config.keys())
        missed = set(self.V2_TOP_REQUIRED_KEYS) - top_keys
        if missed:
            if len(missed) > 1:
                raise exceptions.InvalidTaskException(
                    "'%s' are required properties, but they are missed." %
                    "', '".join(sorted(missed)))

            raise exceptions.InvalidTaskException(
                "'%s' is a required property, but it is missed." % missed.pop()
            )

        redundant = top_keys - set(self.V2_TOP_ALLOWED_KEYS)
        if redundant:
            raise exceptions.InvalidTaskException(
                "Additional properties are not allowed ('%s' %s unexpected)." %
                ("', '".join(sorted(redundant)),
                 "were" if len(redundant) > 1 else "was"))

        self._check_title(config["title"])
        self._check_tags(config.get("tags", []))

        if not isinstance(config["subtasks"], list):
            raise exceptions.InvalidTaskException(
                "Property 'subtasks' should be an array(list), but '%s' is "
                "found." % type(config["subtasks"]).__name__)

        for i, subtask in enumerate(config["subtasks"]):
            try:
                if "workloads" not in subtask:
                    jsonschema.validate(
                        subtask, self.CONFIG_SCHEMA_V2_SUBTASK_SIMPLE)
                else:
                    jsonschema.validate(
                        subtask, self.CONFIG_SCHEMA_V2_SUBTASK_COMPLEX)
            except jsonschema.ValidationError as e:
                raise exceptions.InvalidTaskException(
                    "Subtask #%s. %s" % (i + 1, e))

            if "workloads" not in subtask:
                workload = copy.deepcopy(subtask)
                subtask = {"title": workload.pop("title"),
                           "description": workload.pop("description", ""),
                           "tags": workload.pop("tags", []),
                           "workloads": [workload]}
                config["subtasks"][i] = subtask
        return config
