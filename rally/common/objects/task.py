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
import uuid

from rally.common import db
from rally.common.i18n import _LE
from rally import consts
from rally import exceptions
from rally.task.processing import charts


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

TASK_RESULT_SCHEMA = {
    "type": "object",
    "$schema": consts.JSON_SCHEMA,
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
        "hooks": {"type": "array", "items": HOOK_RESULTS_SCHEMA},
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
                    # NOTE(amaretskiy): "scenario_output" is deprecated
                    #                   in favor of "output"
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
                    "output": OUTPUT_SCHEMA
                },
                "required": ["atomic_actions", "duration", "error",
                             "idle_duration"]
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
    "required": ["key", "sla", "result", "load_duration", "full_duration"],
    "additionalProperties": False
}


TASK_EXTENDED_RESULT_SCHEMA = {
    "type": "object",
    "$schema": consts.JSON_SCHEMA,
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
        "hooks": {"type": "array", "items": HOOK_RESULTS_SCHEMA},
        "iterations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "number"
                    },
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
                    "output": OUTPUT_SCHEMA
                },
                "required": ["atomic_actions", "duration", "error",
                             "idle_duration", "output"]
            },
            "minItems": 1
        },
        "created_at": {
            "anyOf": [
                {"type": "string", "format": "date-time"},
                {"type": "null"}
            ]
        },
        "updated_at": {
            "anyOf": [
                {"type": "string", "format": "date-time"},
                {"type": "null"}
            ]
        },
        "info": {
            "type": "object",
            "properties": {
                "atomic": {"type": "object"},
                "iterations_count": {"type": "integer"},
                "iterations_failed": {"type": "integer"},
                "min_duration": {"type": "number"},
                "max_duration": {"type": "number"},
                "tstamp_start": {"type": "number"},
                "full_duration": {"type": "number"},
                "load_duration": {"type": "number"}
            }
        }
    },
    "required": ["key", "sla", "iterations", "info"],
    "additionalProperties": False
}


class Task(object):
    """Represents a task object."""

    # NOTE(andreykurilin): The following stages doesn't contain check for
    #   current status of task. We should add it in the future, since "abort"
    #   cmd should work everywhere.
    # TODO(andreykurilin): allow abort for each state.
    NOT_IMPLEMENTED_STAGES_FOR_ABORT = [consts.TaskStatus.VERIFYING,
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

    def to_dict(self):
        db_task = self.task
        deployment_name = db.deployment_get(
            self.task["deployment_uuid"])["name"]
        db_task["deployment_name"] = deployment_name
        return db_task

    @staticmethod
    def get_detailed(task_id):
        return db.api.task_get_detailed(task_id)

    @staticmethod
    def get(uuid):
        return Task(db.task_get(uuid))

    @staticmethod
    def get_status(uuid):
        return db.task_get_status(uuid)

    @staticmethod
    def list(status=None, deployment=None):
        return [Task(db_task) for db_task in db.task_list(status, deployment)]

    @staticmethod
    def delete_by_uuid(uuid, status=None):
        db.task_delete(uuid, status=status)

    def _update(self, values):
        if not self.is_temporary:
            self.task = db.task_update(self.task["uuid"], values)

    def update_status(self, status, allowed_statuses=None):
        if allowed_statuses:
            db.task_update_status(self.task["uuid"], status, allowed_statuses)
        else:
            self._update({"status": status})

    def update_verification_log(self, log):
        self._update({"validation_result": log})

    def set_failed(self, etype, msg, etraceback):
        self._update({"status": consts.TaskStatus.FAILED,
                      "validation_result": {
                          "etype": etype, "msg": msg, "trace": etraceback}})

    def add_subtask(self, **subtask):
        return Subtask(self.task["uuid"], **subtask)

    def get_results(self):
        return db.task_result_get_all_by_uuid(self.task["uuid"])

    @classmethod
    def extend_results(cls, results, serializable=False):
        """Modify and extend results with aggregated data.

        This is a workaround method that tries to adapt task results
        to schema of planned DB refactoring, so this method is expected
        to be simplified after DB refactoring since all the data should
        be taken as-is directly from the database.

        Each scenario results have extra `info' with aggregated data,
        and iterations data is represented by iterator - this simplifies
        its future implementation as generator and gives ability to process
        arbitrary number of iterations with low memory usage.

        :param results: list of db.sqlalchemy.models.TaskResult
        :param serializable: bool, whether to convert json non-serializable
                             types (like datetime) to serializable ones
        :returns: list of dicts, each dict represents scenario results:
                  key - dict, scenario input data
                  sla - list, SLA results
                  iterations - if serializable, then iterator with
                               iterations data, otherwise a list
                  created_at - if serializable, then str datetime,
                               otherwise absent
                  updated_at - if serializable, then str datetime,
                               otherwise absent
                  info:
                      atomic - dict where key is one of atomic action names
                               and value is dict {min_duration: number,
                                                  max_duration: number}
                      iterations_count - int number of iterations
                      iterations_failed - int number of iterations with errors
                      min_duration - float minimum iteration duration
                      max_duration - float maximum iteration duration
                      tstamp_start - float timestamp of the first iteration
                      full_duration - float full scenario duration
                      load_duration - float load scenario duration
        """
        extended = []
        for scenario_result in results:
            scenario = dict(scenario_result)
            tstamp_start = 0
            min_duration = 0
            max_duration = 0
            iterations_failed = 0
            atomic = collections.OrderedDict()

            for itr in scenario["data"]["raw"]:
                for atomic_name, duration in itr["atomic_actions"].items():
                    duration = duration or 0
                    if atomic_name not in atomic:
                        atomic[atomic_name] = {"min_duration": duration,
                                               "max_duration": duration}
                    elif duration < atomic[atomic_name]["min_duration"]:
                        atomic[atomic_name]["min_duration"] = duration
                    elif duration > atomic[atomic_name]["max_duration"]:
                        atomic[atomic_name]["max_duration"] = duration

                if not tstamp_start or itr["timestamp"] < tstamp_start:
                    tstamp_start = itr["timestamp"]

                if "output" not in itr:
                    itr["output"] = {"additive": [], "complete": []}

                    # NOTE(amaretskiy): Deprecated "scenario_output"
                    #     is supported for backward compatibility
                    if ("scenario_output" in itr
                            and itr["scenario_output"]["data"]):
                        itr["output"]["additive"].append(
                            {"items": itr["scenario_output"]["data"].items(),
                             "title": "Scenario output",
                             "description": "",
                             "chart": "OutputStackedAreaChart"})
                        del itr["scenario_output"]

                if itr["error"]:
                    iterations_failed += 1
                else:
                    duration = itr["duration"] or 0
                    if not min_duration or duration < min_duration:
                        min_duration = duration
                    if not max_duration or duration > max_duration:
                        max_duration = duration

            for k in "created_at", "updated_at":
                if serializable:
                    # NOTE(amaretskiy): convert datetime to str,
                    #     because json.dumps() does not like datetime
                    if scenario[k]:
                        scenario[k] = scenario[k].strftime("%Y-%d-%mT%H:%M:%S")
                else:
                    del scenario[k]

            durations_stat = charts.MainStatsTable(
                {"iterations_count": len(scenario["data"]["raw"]),
                 "atomic": atomic})

            for itr in scenario["data"]["raw"]:
                durations_stat.add_iteration(itr)

            scenario["info"] = {
                "stat": durations_stat.render(),
                "atomic": atomic,
                "iterations_count": len(scenario["data"]["raw"]),
                "iterations_failed": iterations_failed,
                "min_duration": min_duration,
                "max_duration": max_duration,
                "tstamp_start": tstamp_start,
                "full_duration": scenario["data"]["full_duration"],
                "load_duration": scenario["data"]["load_duration"]}
            iterations = sorted(scenario["data"]["raw"],
                                key=lambda itr: itr["timestamp"])
            if serializable:
                scenario["iterations"] = list(iterations)
            else:
                scenario["iterations"] = iter(iterations)
            scenario["sla"] = scenario["data"]["sla"]
            scenario["hooks"] = scenario["data"].get("hooks", [])
            del scenario["data"]
            del scenario["task_uuid"]
            del scenario["id"]
            extended.append(scenario)
        return extended

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
                                consts.TaskStatus.FAILED,
                                consts.TaskStatus.ABORTED]:
            raise exceptions.RallyException(
                _LE("Failed to abort task '%s', since it already "
                    "finished.") % self.task.uuid)

        new_status = (consts.TaskStatus.SOFT_ABORTING
                      if soft else consts.TaskStatus.ABORTING)
        self.update_status(new_status, allowed_statuses=(
            consts.TaskStatus.RUNNING, consts.TaskStatus.SOFT_ABORTING))


class Subtask(object):
    """Represents a subtask object."""

    def __init__(self, task_uuid, **attributes):
        self.subtask = db.subtask_create(task_uuid, **attributes)

    def __getitem__(self, key):
        return self.subtask[key]

    def add_workload(self, key):
        return Workload(self.subtask["task_uuid"],
                        self.subtask["uuid"], key)


class Workload(object):
    """Represents a workload object."""

    def __init__(self, task_uuid, subtask_uuid, key):
        self.workload = db.workload_create(task_uuid, subtask_uuid, key)

    def __getitem__(self, key):
        return self.workload[key]

    def add_workload_data(self, chunk_order, workload_data):
        db.workload_data_create(self.workload["task_uuid"],
                                self.workload["uuid"], chunk_order,
                                workload_data)

    def set_results(self, data):
        db.workload_set_results(self.workload["uuid"], data)
