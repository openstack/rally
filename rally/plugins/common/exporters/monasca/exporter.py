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
import datetime as dt
import itertools
import json
import os
import time
import hashlib
import re

from rally.common import logging
from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.common.exporters.monasca import client
from rally.task import exporter
from rally.plugins.common.exporters.elastic import flatten

LOG = logging.getLogger(__name__)


def _hash(items):
    # hash configuration to sha512sum
    m = hashlib.sha512()
    for item in items:
        m.update(item)
    return m.hexdigest()


def _get_dimensions(report):
        # these might be useful to someone, but should maybe be specified as as config option
    # "deployment_uuid",  "deployment_name
    dimension_keys = ["uuid", "task_uuid", "subtask_uuid", "args_hash",
                      "runner_hash", "contexts_hash", "tags"]
    dimensions = {key: report[key] for key in
                     dimension_keys if key in report and report[key]}
    return dimensions

def _get_metadata(report):
    meta_keys = ["args"]
    meta = {key: report[key] for key in
                     meta_keys}

def _create_workload_metric(report, field, convert = lambda x: x):
    metric_name_tmpl = "rally.workload.%(name)s.%(metric)s"
    title = report["subtask_title"]

    dimensions = _get_dimensions(report)
    meta = _get_metadata(report)

    metric = {
        "name": metric_name_tmpl % {"name": title, "metric": field},
        "value": convert(report[field]),
        "dimensions": dimensions,
        #"value_meta": meta, # not sure what happens to the metadata + it could cause issues
        # if it gets too long
        "timestamp": report["started_at"]
    }

    return metric

def _create_action_metric(report, field, convert = lambda x: x):
    metric_name_tmpl = "rally.action.%(name)s.%(metric)s"

    action_name = report["action_name"]

    # strip the leading action_ prefix, eg. action_duration becomes duration
    metric = re.sub(r"^action_", "", field)
    dimensions = _get_dimensions(report)
    metric = {
        "name": metric_name_tmpl % {"name": action_name, "metric": metric},
        "value": convert(report[field]),
        "dimensions": dimensions,
        "timestamp": report["action_started_at"]
    }

    return metric

def _create_task_metric(report):

    dimensions = _get_dimensions(report)

    metric = {
        "name": "rally.task.pass_sla",
        "value": float(report["pass_sla"]),
        "dimensions": dimensions,
        "timestamp": int(time.time() * 1000)
    }

    return metric

def _create_action_metrics(report):
    metrics = []

    metrics.append(_create_action_metric(report, "action_success", float))
    metrics.append(_create_action_metric(report, "action_duration"))

    return metrics

def _create_workload_metrics(report):
    metrics = []

    metrics.append(_create_workload_metric(report, "load_duration"))
    metrics.append(_create_workload_metric(report, "success_rate"))
    metrics.append(_create_workload_metric(report, "pass_sla", float))

    return metrics

def _merge_dicts(x, *args):
    x = x.copy()
    for y in args:
      x.update(y)
    return x

@validation.configure("monasca_exporter_destination")
class Validator(validation.Validator):
    """Validates the destination for ElasticSearch exporter.

    In case when the destination is ElasticSearch cluster, the version of it
    should be 2.* or 5.*
    """
    def validate(self, context, config, plugin_cls, plugin_cfg):
        destination = plugin_cfg["destination"]
        # TODO: support destination? This could be a cloud in clouds.yaml
        version = "2_0"
        if version and not version == "2_0":
            self.fail("The unsupported version detected %s." % version)


@validation.add("monasca_exporter_destination")
@exporter.configure("monasca")
class MonascaExporter(exporter.TaskExporter):
    """Exports task results to the Monasca.

    The exported data includes:

    * Task basic information such as title, description, status,
      deployment uuid, etc.
      See rally_task_v1_data index.

    * Workload information such as scenario name and configuration, runner
      type and configuration, time of the start load, success rate, sla
      details in case of errors, etc.
      See rally_workload_v1_data index.

    * Separate documents for all atomic actions.
      See rally_atomic_action_data_v1 index.

    The destination can be a remote server. In this case specify it like:

        https://elastic:changeme@example.com

    Or we can dump documents to the file. The destination should look like:

        /home/foo/bar.txt

    In case of an empty destination, the http://localhost:9200 destination
    will be used.
    """
    def __init__(self, tasks_results, output_destination, api=None):
        super(MonascaExporter, self).__init__(tasks_results,
                                              output_destination,
                                              api=api)
        self._report = []
        self._client = client.MonascaClient()


    @staticmethod
    def _make_action_report(name, uuid, report, duration,
                            started_at, finished_at, parent, error):
        # NOTE(andreykurilin): actually, this method just creates a dict object
        #   but we need to have the same format at two places, so the template
        #   transformed into a method.
        parent = parent[0] if parent else None
        action_report = {
            "uuid": uuid,
            "action_name": name,
            "action_success": not bool(error),
            "action_duration": duration,
            "action_started_at": started_at,
            "action_finished_at": finished_at,
            "action_parent": parent,
            "action_error": error
        }
        return _merge_dicts(report, action_report)

    def _process_atomic_actions(self, itr, report,
                                atomic_actions=None, _parent=None, _depth=0,
                                _cache=None):
        """Process atomic actions of an iteration

        :param atomic_actions: A list with an atomic actions
        :param itr: The iteration data
        :param report: The workload report
        :param _parent: An inner parameter which is used for pointing to the
            parent atomic action
        :param _depth: An inner parameter which is used to mark the level of
            depth while parsing atomic action children
        :param _cache: An inner parameter which is used to avoid conflicts in
            IDs of atomic actions of a single iteration.
        """

        if _depth >= 3:
            return _cache["metrics"]
        cache = _cache or {}
        cache["metrics"] = [] if "metrics" not in cache else cache["metrics"]

        if atomic_actions is None:
            atomic_actions = itr["atomic_actions"]

        act_id_tmpl = "%(itr_id)s_action_%(action_name)s_%(num)s"
        for i, action in enumerate(atomic_actions, 1):
            cache.setdefault(action["name"], 0)
            act_id = act_id_tmpl % {
                "itr_id": itr["id"],
                "action_name": action["name"],
                "num": cache[action["name"]]}
            cache[action["name"]] += 1

            # monasca timestamps are in milliseconds
            started_at = action["started_at"] * 1000
            finished_at = action["finished_at"] * 1000

            action_report = self._make_action_report(
                name=action["name"],
                uuid=act_id,
                report=report,
                duration=(action["finished_at"] - action["started_at"]),
                started_at=started_at,
                finished_at=finished_at,
                parent=_parent,
                error=(itr["error"] if action.get("failed", False) else None)
            )

            metrics = _create_action_metrics(action_report)
            cache["metrics"].extend(metrics)

            self._process_atomic_actions(
                atomic_actions=action["children"],
                itr=itr,
                report=report,
                _parent=(act_id, action_report),
                _depth=(_depth + 1),
                _cache=cache)

        if itr["error"] and (
                # the case when it is a top level of the scenario and the
                #   first fails the item which is not wrapped by AtomicTimer
                (not _parent and not atomic_actions) or
                # the case when it is a top level of the scenario and and
                # the item fails after some atomic actions completed
                (not _parent and atomic_actions and
                    not atomic_actions[-1].get("failed", False))):
            act_id = act_id_tmpl % {
                "itr_id": itr["id"],
                "action_name": "no-name-action",
                "num": 0
            }

            # Since the action had not be wrapped by AtomicTimer, we cannot
            # make any assumption about it's duration (start_time) so let's use
            # finished_at timestamp of iteration with 0 duration
            timestamp = (itr["timestamp"] + itr["duration"] +
                         itr["idle_duration"])
            timestamp *= 1000
            action_report = self._make_action_report(
                name="no-name-action",
                uuid=act_id,
                report=report,
                duration=0,
                started_at=timestamp,
                finished_at=timestamp,
                parent=_parent,
                error=itr["error"]
            )
            metrics = _create_action_metrics(action_report)
            cache["metrics"].extend(metrics)
        return cache["metrics"]

    def generate(self):

        for task in self.tasks_results:
            # TODO: check if already in monasca
            # if self._remote:
            #     if self._client.check_document(self.TASK_INDEX, task["uuid"]):
            #         raise exceptions.RallyException(
            #             "Failed to push the task %s to the ElasticSearch "
            #             "cluster. The document with such UUID already exists" %
            #             task["uuid"])

            result = []

            if task["status"] not in [consts.TaskStatus.SLA_FAILED, consts.TaskStatus.FINISHED,
                                      consts.TaskStatus.CRASHED]:
              # We don't want to upload data for a task that is till doing work
              raise exceptions.RallyException("Refusing to upload task report for task that is running")

            # in the new task engine format where you can set title and description
            # https://github.com/openstack/rally/blob/5dfda156e39693870dcf6c6af89b317a6d57a1d2/doc/specs/implemented/new_rally_input_task_format.rst
            task_report = {
                 "task_uuid": task["uuid"],
                 "deployment_uuid": task["env_uuid"],
                 "deployment_name": task["env_name"],
                 "title": task["title"],
                 "description": task["description"],
                 "status": task["status"],
                 "pass_sla": task["pass_sla"],
                 "tags": ":".join(task["tags"]),
            }
            metric = _create_task_metric(task_report)
            result.append(metric)

            # NOTE(andreykurilin): The subtasks do not have much logic now, so
            #   there is no reason to save the info about them.
            for subtask in task["subtasks"]:
                for workload in subtask["workloads"]:

                    durations = workload["statistics"]["durations"]
                    success_rate = durations["total"]["data"]["success"]
                    if success_rate == "n/a":
                        success_rate = 0.0
                    else:
                        # cut the % char and transform to the float value
                        success_rate = float(success_rate[:-1]) / 100.0

                    started_at = workload["start_time"]
                    if started_at:
                        print(started_at)
                        # monasca requires time stamp in milliseconds
                        started_at = int(started_at * 1000);

                    runner_hash = _hash([workload["runner_type"]] +
                        flatten.transform(workload["runner"])
                    )

                    workload_report = {
                        # Warning: these is a 256 char limit on the monasca dimension
                        # so can't support infinite number of tags
                        # flatten tags to string, would be nice to use commas, but
                        # https://github.com/openstack/monasca-api/blob/master/docs/monasca-api-spec.md#dimensions
                        "uuid": workload["uuid"],
                        "task_uuid": workload["task_uuid"],
                        "subtask_uuid": workload["subtask_uuid"],
                        "subtask_title": subtask["title"],
                        "scenario_name": workload["name"],
                        "args_hash": _hash(flatten.transform(workload["args"])),
                        "args": workload["args"],
                        "description": workload["description"],
                        "runner_name": workload["runner_type"],
                        "runner_hash": runner_hash,
                        "contexts_hash": _hash(flatten.transform(workload["contexts"])),
                        "started_at": started_at,
                        "load_duration": workload["load_duration"],
                        "full_duration": workload["full_duration"],
                        "pass_sla": workload["pass_sla"],
                        "success_rate": success_rate,
                        "sla_details": [s["detail"]
                                        for s in workload["sla_results"]["sla"]
                                        if not s["success"]]}

                # keep data from task_report
                # TODO: do we want to override overides?
                workload_report = _merge_dicts(task_report, workload_report)
                # do we need to store hooks ?!
                metrics = _create_workload_metrics(workload_report)

                result.extend(metrics)

                # Iterations
                for idx, itr in enumerate(workload.get("data", []), 1):
                    itr["id"] = "%(uuid)s_iter_%(num)s" % {
                        "uuid": workload["uuid"],
                        "num": str(idx)}

                    metrics = self._process_atomic_actions(
                        itr=itr,
                        report=workload_report)
                    result.extend(metrics)
        self._client.post(result)
        msg = "Successfully exported results to Monasca"
        return {"print": msg}
