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
import uuid

from rally.common import db
from rally.common.i18n import _LE
from rally.common import logging
from rally import consts
from rally import exceptions


LOG = logging.getLogger(__name__)


OUTPUT_SCHEMA = {
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
                                      "items": {"type": "array",
                                                "items": [{"type": "number"},
                                                          {"type": "number"}]
                                                }},
                                     {"type": "number"}]}]}},
                        {"type": "object",
                         "properties": {
                             "cols": {"type": "array",
                                      "items": {"type": "string"}},
                             "rows": {
                                 "type": "array",
                                 "items": {
                                     "type": "array",
                                     "items": {"anyOf": [{"type": "string"},
                                                         {"type": "number"}]}}
                             }
                         },
                         "required": ["cols", "rows"],
                         "additionalProperties": False},
                        {"type": "array", "items": {"type": "string"}},
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

HOOK_RUN_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "started_at": {"type": "number"},
        "finished_at": {"type": "number"},
        "triggered_by": {
            "type": "object",
            "properties": {"event_type": {"type": "string"},
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
        "output": OUTPUT_SCHEMA,
    },
    "required": ["finished_at", "triggered_by", "status"],
    "additionalProperties": False
}

HOOK_RESULTS_SCHEMA = {
    "type": "object",
    "properties": {
        "config": {"type": "object"},
        "results": {"type": "array",
                    "items": HOOK_RUN_RESULT_SCHEMA},
        "summary": {"type": "object"}
    },
    "required": ["config", "results", "summary"],
    "additionalProperties": False,
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
        deployment_name = db.deployment_get(
            self.task["deployment_uuid"])["name"]
        db_task["deployment_name"] = deployment_name
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
            status, deployment=deployment, tags=tags)]

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

    def add_subtask(self, title, description=None, context=None):
        return Subtask(self.task["uuid"], title=title, description=description,
                       context=context)

    def delete(self, status=None):
        db.task_delete(self.task["uuid"], status=status)

    def abort(self, soft=False):
        current_status = self.get_status(self.task["uuid"])

        if current_status in self.NOT_IMPLEMENTED_STAGES_FOR_ABORT:
            raise exceptions.RallyException(
                _LE("Failed to abort task '%(uuid)s'. It doesn't implemented "
                    "for '%(stages)s' stages. Current task status is "
                    "'%(status)s'.") %
                {"uuid": self.task["uuid"], "status": current_status,
                 "stages": ", ".join(self.NOT_IMPLEMENTED_STAGES_FOR_ABORT)})
        elif current_status in [consts.TaskStatus.FINISHED,
                                consts.TaskStatus.CRASHED,
                                consts.TaskStatus.ABORTED]:
            raise exceptions.RallyException(
                _LE("Failed to abort task '%s', since it already "
                    "finished.") % self.task["uuid"])

        new_status = (consts.TaskStatus.SOFT_ABORTING
                      if soft else consts.TaskStatus.ABORTING)
        self.update_status(new_status, allowed_statuses=(
            consts.TaskStatus.RUNNING, consts.TaskStatus.SOFT_ABORTING))


class Subtask(object):
    """Represents a subtask object."""

    def __init__(self, task_uuid, title, description=None, context=None):
        self.subtask = db.subtask_create(task_uuid,
                                         title=title,
                                         description=description,
                                         context=context)

    def __getitem__(self, key):
        return self.subtask[key]

    def _update(self, values):
        self.subtask = db.subtask_update(self.subtask["uuid"], values)

    def update_status(self, status):
        self._update({"status": status})

    def add_workload(self, name, description, position, runner, context, hooks,
                     sla, args):
        return Workload(task_uuid=self.subtask["task_uuid"],
                        subtask_uuid=self.subtask["uuid"], name=name,
                        description=description, position=position,
                        runner=runner, hooks=hooks, context=context, sla=sla,
                        args=args)


class Workload(object):
    """Represents a workload object."""

    def __init__(self, task_uuid, subtask_uuid, name, description, position,
                 runner, hooks, context, sla, args):
        self.workload = db.workload_create(
            task_uuid=task_uuid, subtask_uuid=subtask_uuid, name=name,
            description=description, position=position, runner=runner,
            runner_type=runner["type"], hooks=hooks, context=context, sla=sla,
            args=args)

    def __getitem__(self, key):
        return self.workload[key]

    def add_workload_data(self, chunk_order, workload_data):
        db.workload_data_create(self.workload["task_uuid"],
                                self.workload["uuid"], chunk_order,
                                workload_data)

    def set_results(self, load_duration, full_duration, start_time,
                    sla_results, hooks_results=None):
        db.workload_set_results(workload_uuid=self.workload["uuid"],
                                subtask_uuid=self.workload["subtask_uuid"],
                                task_uuid=self.workload["task_uuid"],
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results,
                                hooks_results=hooks_results)

    @classmethod
    def to_task(cls, workload):
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
        subtask["contexts"] = workload["context"]
        runner = copy.copy(workload["runner"])
        subtask["runner"] = {runner.pop("type"): runner}
        subtask["hooks"] = [h["config"] for h in workload["hooks"]]
        subtask["sla"] = workload["sla"]
        return task
