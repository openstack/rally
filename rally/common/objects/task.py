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

import collections
import copy
import datetime as dt
import six
import uuid

from rally.common import db
from rally.common import logging
from rally import consts
from rally import exceptions
from rally.task.processing import charts


LOG = logging.getLogger(__name__)


TASK_SCHEMA = {
    "type": "object",
    "$schema": consts.JSON_SCHEMA,
    "properties": {
        "uuid": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "number"},
        "status": {"type": "string"},
        "tags": {"type": "array"},
        "env_name": {"type": "string"},
        "env_uuid": {"type": "string"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
        "pass_sla": {"type": "boolean"},
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "uuid": {"type": "string"},
                    "task_uuid": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string"},
                    "pass_sla": {"type": "boolean"},
                    "run_in_parallel": {"type": "boolean"},
                    "created_at": {"type": "string"},
                    "updated_at": {"type": "string"},
                    "sla": {"type": "object"},
                    "workloads": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/workload"}
                    }
                },
                "required": ["workloads"],
                "additionalProperties": False
            }
        }
    },
    "required": ["subtasks"],
    "additionalProperties": False,
    "definitions": {
        "number-or-null": {"oneOf": [
            {"type": "number", "description": "There was a load."},
            {"type": "null", "description": "The load was not started"}]},
        "workload": {
            "type": "object",
            "properties": {
                "uuid": {"type": "string"},
                "task_uuid": {"type": "string"},
                "subtask_uuid": {"type": "string"},
                "description": {"type": "string"},
                "scenario": {
                    "type": "object",
                    "minProperties": 1,
                    "maxProperties": 1,
                    "patternProperties": {
                        ".*": {"type": "object"}
                    }
                },
                "args": {"type": "object"},
                "runner": {"type": "object"},
                "runner_type": {"type": "string"},
                "hooks": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/hook_result"}
                },
                "min_duration": {"$ref": "#/definitions/number-or-null"},
                "max_duration": {"$ref": "#/definitions/number-or-null"},
                "start_time": {"$ref": "#/definitions/number-or-null"},
                "load_duration": {"type": "number"},
                "full_duration": {"type": "number"},
                "statistics": {
                    "type": "object",
                    "properties": {
                        "durations": {"type": "object"},
                        "atomics": {"type": "object"}
                    }
                },
                "data": {"type": "array"},
                "failed_iteration_count": {"type": "integer"},
                "total_iteration_count": {"type": "integer"},
                "created_at": {"type": "string"},
                "updated_at": {"type": "string"},
                "contexts": {"type": "object"},
                "contexts_results": {"type": "array"},
                "position": {"type": "integer"},
                "pass_sla": {"type": "boolean"},
                "sla_results": {
                    "type": "object",
                    "properties": {
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
                        }
                    }
                },
                "sla": {"type": "object"}
            },
            "required": ["pass_sla", "sla_results", "sla", "statistics",
                         "contexts", "data", "runner", "scenario",
                         "full_duration", "load_duration",
                         "total_iteration_count", "failed_iteration_count",
                         "position"],
            "additionalProperties": False
        },
        "hook_result": {
            "type": "object",
            "properties": {
                "config": {"type": "object"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "started_at": {"type": "number"},
                            "finished_at": {"type": "number"},
                            "triggered_by": {
                                "type": "object",
                                "properties": {
                                    "event_type": {"type": "string"},
                                    "value": {}},
                                "required": ["event_type", "value"],
                                "additionalProperties": False
                            },
                            "status": {"type": "string"},
                            "error": {
                                "type": "array",
                                "minItems": 3,
                                "maxItems": 3,
                                "items": {"type": "string"},
                            },
                            "output": {"$ref": "#/definitions/output"},
                        },
                        "required": ["finished_at", "triggered_by", "status"],
                        "additionalProperties": False
                    }
                },
                "summary": {"type": "object"}
            },
            "required": ["config", "results", "summary"],
            "additionalProperties": False,
        },
        "output": {
            "type": "object",
            "properties": {
                "additive": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "chart_plugin": {"type": "string"},
                            "data": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": [{"type": "string"},
                                              {"type": "number"}],
                                    "additionalItems": False}},
                            "label": {"type": "string"},
                            "axis_label": {"type": "string"}},
                        "required": ["title", "chart_plugin", "data"],
                        "additionalProperties": False
                    }
                },
                "complete": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "chart_plugin": {"type": "string"},
                            "data": {"anyOf": [
                                {"type": "array",
                                 "items": {
                                     "type": "array",
                                     "items": [
                                         {"type": "string"},
                                         {"anyOf": [
                                             {"type": "array",
                                              "items": {
                                                  "type": "array",
                                                  "items": [
                                                      {"type": "number"},
                                                      {"type": "number"}]
                                              }},
                                             {"type": "number"}]
                                          }]
                                 }},
                                {"type": "object",
                                 "properties": {
                                     "cols": {"type": "array",
                                              "items": {"type": "string"}},
                                     "rows": {
                                         "type": "array",
                                         "items": {
                                             "type": "array",
                                             "items": {
                                                 "anyOf": [{"type": "string"},
                                                           {"type": "number"}]
                                             }
                                         }
                                     }
                                 },
                                 "required": ["cols", "rows"],
                                 "additionalProperties": False},
                                {"type": "array",
                                 "items": {"type": "string"}},
                            ]},
                            "label": {"type": "string"},
                            "axis_label": {"type": "string"}
                        },
                        "required": ["title", "chart_plugin", "data"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["additive", "complete"],
            "additionalProperties": False
        }
    }
}


class Task(object):
    """Represents a task object.

    Task states graph

    INIT -> VALIDATING |-> VALIDATION_FAILED
                       |-> ABORTING -> ABORTED
                       |-> SOFT_ABORTING -> ABORTED
                       |-> CRASHED
                       |-> VALIDATED |-> RUNNING |-> FINISHED
                                                 |-> ABORTING -> ABORTED
                                                 |-> SOFT_ABORTING -> ABORTED
                                                 |-> CRASHED
    """

    # NOTE(andreykurilin): The following stages doesn't contain check for
    #   current status of task. We should add it in the future, since "abort"
    #   cmd should work everywhere.
    # TODO(andreykurilin): allow abort for each state.
    NOT_IMPLEMENTED_STAGES_FOR_ABORT = [consts.TaskStatus.VALIDATING,
                                        consts.TaskStatus.INIT]

    def __init__(self, task=None, temporary=False, **attributes):
        """Task object init

        :param task: dictionary like object, that represents a task
        :param temporary: whenever this param is True the task will be created
            with a random UUID and no database record. Used for special
            purposes, like task config validation.
        """

        self.is_temporary = temporary

        if self.is_temporary:
            self.task = task or {"uuid": str(uuid.uuid4())}
            self.task.update(attributes)
        else:
            self.task = task or db.task_create(attributes)

    def __getitem__(self, key):
        if key == "deployment_uuid":
            key = "env_uuid"
        return self.task[key]

    @staticmethod
    def _serialize_dt(obj):
        if isinstance(obj["created_at"], dt.datetime):
            obj["created_at"] = obj["created_at"].strftime(
                consts.TimeFormat.ISO8601)
            obj["updated_at"] = obj["updated_at"].strftime(
                consts.TimeFormat.ISO8601)

    def to_dict(self):
        db_task = self.task
        env_name = db.env_get(self.task["env_uuid"])["name"]
        db_task["env_name"] = env_name
        db_task["deployment_name"] = env_name
        db_task["deployment_uuid"] = db_task["env_uuid"]
        self._serialize_dt(db_task)
        for subtask in db_task.get("subtasks", []):
            self._serialize_dt(subtask)
            for workload in subtask["workloads"]:
                self._serialize_dt(workload)
        return db_task

    @classmethod
    def get(cls, uuid, detailed=False):
        return cls(db.api.task_get(uuid, detailed=detailed))

    @staticmethod
    def get_status(uuid):
        return db.task_get_status(uuid)

    @staticmethod
    def list(status=None, deployment=None, tags=None):
        return [Task(db_task) for db_task in db.task_list(
            status, env=deployment, tags=tags)]

    @staticmethod
    def delete_by_uuid(uuid, status=None):
        db.task_delete(uuid, status=status)

    def _update(self, values):
        if not self.is_temporary:
            self.task = db.task_update(self.task["uuid"], values)
        else:
            self.task.update(values)

    def update_status(self, status, allowed_statuses=None):
        if allowed_statuses:
            db.task_update_status(self.task["uuid"], status, allowed_statuses)
        else:
            self._update({"status": status})

    def set_validation_failed(self, log):
        self._update({"status": consts.TaskStatus.VALIDATION_FAILED,
                      "validation_result": log})

    def set_failed(self, etype, msg, etraceback):
        self._update({"status": consts.TaskStatus.CRASHED,
                      "validation_result": {
                          "etype": etype, "msg": msg, "trace": etraceback}})

    def add_subtask(self, title, description=None, contexts=None):
        return Subtask(self.task["uuid"], title=title, description=description,
                       contexts=contexts)

    def delete(self, status=None):
        db.task_delete(self.task["uuid"], status=status)

    def abort(self, soft=False):
        current_status = self.get_status(self.task["uuid"])

        if current_status in self.NOT_IMPLEMENTED_STAGES_FOR_ABORT:
            raise exceptions.RallyException(
                "Failed to abort task '%(uuid)s'. It doesn't implemented "
                "for '%(stages)s' stages. Current task status is '%(status)s'."
                % {"uuid": self.task["uuid"], "status": current_status,
                   "stages": ", ".join(self.NOT_IMPLEMENTED_STAGES_FOR_ABORT)})
        elif current_status in [consts.TaskStatus.FINISHED,
                                consts.TaskStatus.CRASHED,
                                consts.TaskStatus.ABORTED]:
            raise exceptions.RallyException(
                "Failed to abort task '%s', since it already finished."
                % self.task["uuid"])

        new_status = (consts.TaskStatus.SOFT_ABORTING
                      if soft else consts.TaskStatus.ABORTING)
        self.update_status(new_status, allowed_statuses=(
            consts.TaskStatus.RUNNING, consts.TaskStatus.SOFT_ABORTING))

    def result_has_valid_schema(self, result):
        """Check whatever result has valid schema or not."""
        # NOTE(boris-42): We can't use here jsonschema, this method is called
        #                 to check every iteration result schema. And this
        #                 method works 200 times faster then jsonschema
        #                 which totally makes sense.
        _RESULT_SCHEMA = {
            "fields": [("duration", float), ("timestamp", float),
                       ("idle_duration", float), ("output", dict),
                       ("atomic_actions", list), ("error", list)]
        }
        for key, proper_type in _RESULT_SCHEMA["fields"]:
            if key not in result:
                LOG.warning("'%s' is not result" % key)
                return False
            if not isinstance(result[key], proper_type):
                LOG.warning(
                    "Task %(uuid)s | result['%(key)s'] has wrong type "
                    "'%(actual_type)s', should be '%(proper_type)s'"
                    % {"uuid": self.task["uuid"],
                       "key": key,
                       "actual_type": type(result[key]),
                       "proper_type": proper_type.__name__})
                return False

        actions_list = copy.deepcopy(result["atomic_actions"])
        for action in actions_list:
            for key in ("name", "started_at", "finished_at", "children"):
                if key not in action:
                    LOG.warning(
                        "Task %(uuid)s | Atomic action %(action)s "
                        "missing key '%(key)s'"
                        % {"uuid": self.task["uuid"],
                           "action": action,
                           "key": key})
                    return False
            for key in ("started_at", "finished_at"):
                if not isinstance(action[key], float):
                    LOG.warning(
                        "Task %(uuid)s | Atomic action %(action)s has "
                        "wrong type '%(type)s', should be 'float'"
                        % {"uuid": self.task["uuid"],
                           "action": action,
                           "type": type(action[key])})
                    return False
            if action["children"]:
                actions_list.extend(action["children"])

        for e in result["error"]:
            if not isinstance(e, (six.string_types, six.text_type)):
                LOG.warning("error value has wrong type '%s', should be 'str'"
                            % type(e))
                return False

        for key in ("additive", "complete"):
            if key not in result["output"]:
                LOG.warning("Task %(uuid)s | Output missing key '%(key)s'"
                            % {"uuid": self.task["uuid"], "key": key})
                return False

            type_ = type(result["output"][key])
            if type_ != list:
                LOG.warning(
                    "Task %(uuid)s | Value of result['output']['%(key)s'] "
                    "has wrong type '%(type)s', must be 'list'"
                    % {"uuid": self.task["uuid"],
                       "key": key, "type": type_.__name__})
                return False

        for key in result["output"]:
            for output_data in result["output"][key]:
                message = charts.validate_output(key, output_data)
                if message:
                    LOG.warning("Task %(uuid)s | %(message)s"
                                % {"uuid": self.task["uuid"],
                                   "message": message})
                    return False

        return True


class Subtask(object):
    """Represents a subtask object."""

    def __init__(self, task_uuid, title, description=None, contexts=None):
        self.subtask = db.subtask_create(task_uuid,
                                         title=title,
                                         description=description,
                                         contexts=contexts)

    def __getitem__(self, key):
        return self.subtask[key]

    def _update(self, values):
        self.subtask = db.subtask_update(self.subtask["uuid"], values)

    def update_status(self, status):
        self._update({"status": status})

    def add_workload(self, name, description, position, runner, runner_type,
                     contexts, hooks, sla, args):
        # store hooks config as it will look after adding results
        if hooks:
            hooks = [{"config": hook} for hook in hooks]
        return Workload(task_uuid=self.subtask["task_uuid"],
                        subtask_uuid=self.subtask["uuid"], name=name,
                        description=description, position=position,
                        runner=runner, runner_type=runner_type, hooks=hooks,
                        contexts=contexts, sla=sla, args=args)


class Workload(object):
    """Represents a workload object."""

    def __init__(self, task_uuid, subtask_uuid, name, description, position,
                 runner, runner_type, hooks, contexts, sla, args):
        self.workload = db.workload_create(
            task_uuid=task_uuid, subtask_uuid=subtask_uuid, name=name,
            description=description, position=position, runner=runner,
            runner_type=runner_type, hooks=hooks, contexts=contexts, sla=sla,
            args=args)

    def __getitem__(self, key):
        return self.workload[key]

    def add_workload_data(self, chunk_order, workload_data):
        db.workload_data_create(self.workload["task_uuid"],
                                self.workload["uuid"], chunk_order,
                                workload_data)

    def set_results(self, load_duration, full_duration, start_time,
                    sla_results, contexts_results, hooks_results=None):
        db.workload_set_results(workload_uuid=self.workload["uuid"],
                                subtask_uuid=self.workload["subtask_uuid"],
                                task_uuid=self.workload["task_uuid"],
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results,
                                hooks_results=hooks_results,
                                contexts_results=contexts_results)

    @classmethod
    def to_task(cls, workload):
        """Format a single workload as a full Task to launch.

        :param workload: A workload config as it stores in database or like in
            input file (the difference in hook format).
        """
        task = collections.OrderedDict()
        task["version"] = 2
        task["title"] = "A cropped version of a bigger task."
        task["description"] = "Auto-generated task from a single workload"
        if "uuid" in workload:
            task["description"] += " (uuid=%s)" % workload["uuid"]
        task["subtasks"] = [collections.OrderedDict()]
        subtask = task["subtasks"][0]
        subtask["title"] = workload["name"]
        subtask["description"] = workload["description"]
        subtask["scenario"] = {workload["name"]: workload["args"]}
        subtask["contexts"] = workload["contexts"]
        subtask["runner"] = {workload["runner_type"]: workload["runner"]}
        subtask["hooks"] = []
        for hook in workload["hooks"]:
            if "config" in hook:
                # it is an object from database
                hook = hook["config"]
            subtask["hooks"].append({
                "description": hook.get("description"),
                "action": dict([hook["action"]]),
                "trigger": dict([hook["trigger"]])})
        subtask["sla"] = workload["sla"]
        return task
