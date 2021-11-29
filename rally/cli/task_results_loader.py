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

import datetime as dt
import json
import os

import jsonschema

from rally import api
from rally import consts
from rally import exceptions
from rally.task.processing import charts


OLD_TASK_RESULT_SCHEMA = {
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
        "hooks": {"type": "array"},
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
                    "output": {"type": "object"}
                },
                "required": ["atomic_actions", "duration", "error",
                             "idle_duration"]
            },
            "minItems": 0
        },
        "load_duration": {
            "type": "number",
        },
        "full_duration": {
            "type": "number",
        },
        "created_at": {
            "type": "string"
        }
    },
    "required": ["key", "sla", "result", "load_duration", "full_duration"],
    "additionalProperties": False
}


class FailedToLoadResults(exceptions.RallyException):
    error_code = 225
    msg_fmt = "ERROR: Invalid task result format in %(source)s\n\n\t%(msg)s"


def _update_atomic_actions(atomic_actions, started_at):
    """Convert atomic actions in old format to latest one."""
    new = []
    for name, duration in atomic_actions.items():
        finished_at = started_at + duration
        new.append({
            "name": name,
            "started_at": started_at,
            "finished_at": finished_at,
            "children": []}
        )
        started_at = finished_at
    return new


def _update_old_results(tasks_results, path):
    """Converts tasks results in old format to latest one."""
    task = {"version": 2,
            "title": "Task loaded from a file.",
            "description": "Auto-ported from task format V1.",
            "uuid": "n/a",
            "env_name": "n/a",
            "env_uuid": "n/a",
            "tags": [],
            "status": consts.TaskStatus.FINISHED,
            "subtasks": []}

    start_time = None

    for result in tasks_results:
        try:
            jsonschema.validate(
                result, OLD_TASK_RESULT_SCHEMA)
        except jsonschema.ValidationError as e:
            raise FailedToLoadResults(source=path,
                                      msg=str(e))

        iter_count = 0
        failed_iter_count = 0
        min_duration = None
        max_duration = None

        for itr in result["result"]:
            if start_time is None or itr["timestamp"] < start_time:
                start_time = itr["timestamp"]
            # NOTE(chenhb): back compatible for atomic_actions
            itr["atomic_actions"] = _update_atomic_actions(
                itr["atomic_actions"], started_at=itr["timestamp"])

            iter_count += 1
            if itr.get("error"):
                failed_iter_count += 1

            duration = itr.get("duration", 0)

            if max_duration is None or duration > max_duration:
                max_duration = duration

            if min_duration is None or min_duration > duration:
                min_duration = duration

        durations_stat = charts.MainStatsTable(
            {"total_iteration_count": iter_count})

        for itr in result["result"]:
            durations_stat.add_iteration(itr)

        created_at = dt.datetime.strptime(result["created_at"],
                                          "%Y-%d-%mT%H:%M:%S")
        updated_at = created_at + dt.timedelta(
            seconds=result["full_duration"])
        created_at = created_at.strftime(consts.TimeFormat.ISO8601)
        updated_at = updated_at.strftime(consts.TimeFormat.ISO8601)
        pass_sla = all(s.get("success") for s in result["sla"])
        runner_type = result["key"]["kw"]["runner"].pop("type")
        for h in result["hooks"]:
            trigger = h["config"]["trigger"]
            h["config"] = {
                "description": h["config"].get("description"),
                "action": (h["config"]["name"], h["config"]["args"]),
                "trigger": (trigger["name"], trigger["args"])}
        workload = {"uuid": "n/a",
                    "name": result["key"]["name"],
                    "position": result["key"]["pos"],
                    "description": result["key"].get("description",
                                                     ""),
                    "full_duration": result["full_duration"],
                    "load_duration": result["load_duration"],
                    "total_iteration_count": iter_count,
                    "failed_iteration_count": failed_iter_count,
                    "min_duration": min_duration,
                    "max_duration": max_duration,
                    "start_time": start_time,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "args": result["key"]["kw"]["args"],
                    "runner_type": runner_type,
                    "runner": result["key"]["kw"]["runner"],
                    "hooks": result["hooks"],
                    "sla": result["key"]["kw"]["sla"],
                    "sla_results": {"sla": result["sla"]},
                    "pass_sla": pass_sla,
                    "contexts": result["key"]["kw"]["context"],
                    "contexts_results": [],
                    "data": sorted(result["result"],
                                   key=lambda x: x["timestamp"]),
                    "statistics": {
                        "durations": durations_stat.to_dict()},
                    }
        task["subtasks"].append(
            {"title": "A SubTask",
             "description": "",
             "workloads": [workload]})
    return [task]


def _update_new_results(tasks_results):
    for task_result in tasks_results["tasks"]:
        try:
            jsonschema.validate(task_result, api._Task.TASK_SCHEMA)
        except jsonschema.ValidationError as e:
            raise exceptions.RallyException(
                "ERROR: Invalid task result format\n\n\t%s" % str(e)) from None
        task_result.setdefault("env_name", "n/a")
        task_result.setdefault("env_uuid", "n/a")
        for subtask in task_result["subtasks"]:
            for workload in subtask["workloads"]:
                workload.setdefault("contexts_results", [])
                workload["runner_type"], workload["runner"] = list(
                    workload["runner"].items())[0]
                workload["name"], workload["args"] = list(
                    workload.pop("scenario").items())[0]

    return tasks_results["tasks"]


def load(path):
    with open(os.path.expanduser(path)) as f:
        raw_tasks_results = f.read()

    try:
        tasks_results = json.loads(raw_tasks_results)
    except ValueError:
        raise FailedToLoadResults(
            source=path, msg="error while loading JSON.") from None

    if isinstance(tasks_results, list):
        return _update_old_results(tasks_results, path)
    elif isinstance(tasks_results, dict) and "tasks" in tasks_results:
        return _update_new_results(tasks_results)
    else:
        raise FailedToLoadResults(
            source=path, msg="Wrong format")
