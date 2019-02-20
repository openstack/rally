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
import imp
import jmespath
import dateutil.parser
import sys
from shutil import copyfile

from rally.common import logging
from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.common.exporters.monasca import client
from rally.task import exporter
from rally.plugins.common.exporters.elastic import flatten

LOG = logging.getLogger(__name__)

_PATH = os.path.realpath(__file__)
_DIR_PATH = os.path.dirname(_PATH)
_EXAMPLE_CONFIG_PATH = os.path.join(_DIR_PATH, "example_config.py")


def _hash(items):
    # hash configuration to sha512sum
    m = hashlib.sha512()
    for item in items:
        m.update(item)
    return m.hexdigest()


def _load_module(name, path):
    module = imp.load_source(name, path)
    return module


def _get_metadata(report):
    meta_keys = report["workload"]["args"]
    meta = {key: report[key] for key in
            meta_keys}
    return meta


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

    The exported data is specified in the config file. The location of this file
    can be set with the MONASCA_EXPORT_CONFIG_PATH environmental variable. If
    MONASCA_EXPORT_CONFIG_PATH  is unset, the path:
    ``~/.rally/monasca-config.py`` is used.

    The environmental variable MONASCA_EXPORT_DRY_RUN may be set to output
    a list of metrics that would be uploaded. The actual uploading of these
    metrics is skipped.

    The destination parameter, as set with:
    ``rally task --export --type monasca --destination output.txt``, currently
    has no effect.
    """

    def __init__(self, tasks_results, output_destination, api=None):
        super(MonascaExporter, self).__init__(tasks_results,
                                              output_destination,
                                              api=api)
        self._report = []
        self._client = client.MonascaClient()

        self.dry_run = False
        env_err = "There is a problem with your environmental variables: %s"
        if "MONASCA_EXPORT_DRY_RUN" in os.environ:
            self.dry_run = True

        if "MONASCA_EXPORT_CONFIG_PATH" in os.environ:
            config_path = os.environ["MONASCA_EXPORT_CONFIG_PATH"]
            if not os.path.exists(config_path):
                raise exceptions.RallyException(env_err %
                                                "MONASCA_EXPORT_CONFIG_PATH does not point to a path that exists. "
                                                "It was set to: %s" % config_path)
        else:
            home_dir = os.environ.get("HOME")
            config_path = os.path.join(home_dir, ".rally", "monasca-config.py")
            if not os.path.exists(config_path):
                copyfile(_EXAMPLE_CONFIG_PATH, config_path)

        self.config = _load_module('config', config_path)
        config = self.config
        if hasattr(config, "metrics"):
            self.action_metrics = config.metrics.get("action", [])
            self.workload_metrics = config.metrics.get("workload", [])
            self.task_metrics = config.metrics.get("task", [])

    def _get_dimension_requirements(self, metric_fqn):
        pcomponents = metric_fqn.split(".")
        # Add a dummy value at the end so that we don't have to special case
        pcomponents.append("THIS WILL NOT BE USED")
        path = pcomponents[0]
        dimensions = {}
        for component in pcomponents[1:]:
            if path in self.config.dimensions:
                # entry is a mapping of dimension name -> path in report
                entry = self.config.dimensions[path]
                if "uuid" in entry:
                    # Reserve uuid in case we want to prevent duplicate uploads
                    raise exceptions.RallyException(
                        "Error in config: Trying to use dimension uuid for "
                        "path: `%s`. The dimension, uuid is reserved for "
                        "internal use."
                        % path
                    )
                dimensions = _merge_dicts(dimensions, entry)
            path = ".".join([path, component])

        return dimensions

    def _get_dimensions(self, report, metric_fqn):
        # these might be useful to someone, but should maybe be specified as as config option
        # "deployment_uuid",  "deployment_name
        requirements = self._get_dimension_requirements(metric_fqn)
        dimensions = {}
        for dimension_name, requirement in requirements.items():
            path = requirement.get("path_in_report")
            if not path:
                err_msg = "Failed to parse config file: %s"
                raise exceptions.RallyException(
                    err_msg % "the dictionary key `path_in_report` is missing for dimension %s" % dimension_name)
            value = jmespath.search(path, report)
            if value:
                dimensions[dimension_name] = jmespath.search(path, report)
            debug = requirement.get("debug")
            if debug and debug == metric_fqn:
                if not value:
                    raise exceptions.RallyException(
                        "The jmespath: %s, did not produce a match for metric: %s" % (
                        path, metric_fqn))
                print(
                            "Dumping dimension: %s, as it is labelled with the debug flag" %
                            dimension_name)
                print(value)
                print("Exiting early due to debug request")
                sys.exit(0)

        return dimensions

    def _validate_metric(self, metric):
        err_msg = "Failed to parse config file: %s"
        name = metric.get("name")
        if not name:
            raise exceptions.RallyException(
                err_msg % "the dictionary key `name` is missing for one of your metrics")
        path = metric.get("path_in_report")
        if not path:
            raise exceptions.RallyException(
                err_msg % "the dictionary key `path_in_report` is missing for dimension %s" %
                metric["name"])

    def _lookup_metric(self, report, metric, fqn):
        path = metric.get("path_in_report")
        value = jmespath.search(path, report)
        transform = metric.get("transform")
        if transform:
            value = transform(value)
        if not value:
            raise exceptions.RallyException(
                "The jmespath: %s, did not produce a match for metric: %s" % (
                    path, fqn))
        debug = metric.get("debug")
        if debug and debug == fqn:
            print("Dumping metric: %s, as it is labelled with the debug flag" %
                  metric["name"])
            print(value)
            print("Exiting early due to debug request")
            sys.exit(0)
        return value

    def _create_workload_metric(self, report, metric):
        self._validate_metric(metric)
        metric_name_tmpl = "rally.workload.%(name)s.%(metric)s"
        title = report["workload"]["subtask_title"]
        fqn = metric_name_tmpl % {"name": title, "metric": metric["name"]}
        value = self._lookup_metric(report, metric, fqn)

        dimensions = self._get_dimensions(report, fqn)
        dimensions["uuid"] = report["workload"]["uuid"]
        metric = {
            "name": fqn,
            "value": value,
            "dimensions": dimensions,
            # "value_meta": meta, # not sure what happens to the metadata + it could cause issues
            # if it gets too long
            "timestamp": report["workload"]["started_at"]
        }

        return metric

    def _create_action_metric(self, report, metric):
        self._validate_metric(metric)
        metric_name_tmpl = "rally.action.%(name)s.%(metric)s"
        action_name = report["action"]["name"]
        fqn = metric_name_tmpl % {"name": action_name,
                                  "metric": metric["name"]}
        value = self._lookup_metric(report, metric, fqn)

        dimensions = self._get_dimensions(report, fqn)
        dimensions["uuid"] = report["action"]["uuid"]
        metric = {
            "name": fqn,
            "value": value,
            "dimensions": dimensions,
            "timestamp": report["action"]["started_at"]
        }

        return metric

    def _create_task_metric(self, report, metric):
        fqn = "rally.task.%s" % metric

        dimensions = self._get_dimensions(report, fqn)
        dimensions["uuid"] = report["task"]["uuid"]

        metric = {
            "name": "rally.task.pass_sla",
            "value": float(report["task"]["pass_sla"]),
            "dimensions": dimensions,
            "timestamp": report["task"]["created_at"]
        }

        return metric

    def _create_action_metrics(self, report):
        metrics = []
        for metric in self.action_metrics:
            metrics.append(self._create_action_metric(report, metric))
        return metrics

    def _create_workload_metrics(self, report):
        metrics = []
        for metric in self.workload_metrics:
            metrics.append(self._create_workload_metric(report, metric))
        return metrics

    def _create_task_metrics(self, report):
        metrics = []
        for metric in self.task_metrics:
            metrics.append(self._create_task_metric(report, metric))
        return metrics

    @staticmethod
    def _add_subreport(report, name, subreport):
        result = report.copy()
        result[name] = subreport
        return result

    @staticmethod
    def _make_action_report(name, uuid, report, duration,
                            started_at, finished_at, parent, error):
        # NOTE(andreykurilin): actually, this method just creates a dict object
        #   but we need to have the same format at two places, so the template
        #   transformed into a method.
        parent = parent[0] if parent else None
        action_report = {
            "uuid": uuid,
            "name": name,
            "success": not bool(error),
            "duration": duration,
            "started_at": started_at,
            "finished_at": finished_at,
            "parent": parent,
            "error": error
        }
        return MonascaExporter._add_subreport(report, "action", action_report)

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

            metrics = self._create_action_metrics(action_report)
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
            metrics = self._create_action_metrics(action_report)
            cache["metrics"].extend(metrics)
        return cache["metrics"]

    @staticmethod
    def _to_epoch_time(date_string):
        now = dateutil.parser.parse(date_string)
        epoch = dt.datetime.utcfromtimestamp(0)
        return (now - epoch).total_seconds() * 1000.0

    def _hash(self, dict):
        # could hash json output, but maybe this flatten method has a more
        # stable output
        flat_repr = flatten.transform(dict)
        # could output store hash -> json(dict) in a key value store for
        # later retrieval
        return _hash(flat_repr)

    def generate(self):

        for task in self.tasks_results:
            # TODO: check if already in monasca. I have reserved the uuid dimension
            # in case we want to query monasca to see if that metric exists.
            # However querying monasca is very slow.
            #
            # Doug says that if the value and name are identical you will get
            # a union of dimensions.
            # if self._remote:
            #     if self._client.check_document(self.TASK_INDEX, task["uuid"]):
            #         raise exceptions.RallyException(
            #             "Failed to push the task %s to the ElasticSearch "
            #             "cluster. The document with such UUID already exists" %
            #             task["uuid"])
            result = []

            if task["status"] not in [consts.TaskStatus.SLA_FAILED,
                                      consts.TaskStatus.FINISHED,
                                      consts.TaskStatus.CRASHED]:
                # We don't want to upload data for a task that is till doing work
                raise exceptions.RallyException(
                    "Refusing to upload task report for task that is running")

            # in the new task engine format where you can set title and description
            # https://github.com/openstack/rally/blob/5dfda156e39693870dcf6c6af89b317a6d57a1d2/doc/specs/implemented/new_rally_input_task_format.rst
            task_report = {
                "uuid": task["uuid"],
                "deployment_uuid": task["env_uuid"],
                "deployment_name": task["env_name"],
                "title": task["title"],
                "description": task["description"],
                "status": task["status"],
                "pass_sla": task["pass_sla"],
                # Warning: these is a 256 char limit on the monasca dimension
                # so can't support infinite number of tags.
                # flatten tags to string, would be nice to use commas, but
                # https://github.com/openstack/monasca-api/blob/master/docs/monasca-api-spec.md#dimensions
                "tags": ":".join(sorted(task["tags"])),
                # monasca requires milliseconds
                "created_at": MonascaExporter._to_epoch_time(
                    task["created_at"])
            }
            task_report = MonascaExporter._add_subreport({}, "task",
                                                         task_report)
            result.extend(self._create_task_metrics(task_report))

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
                        # monasca requires time stamp in milliseconds
                        started_at = int(started_at * 1000);

                    runner_type = {
                        "runner_type": workload["runner_type"],
                    }

                    runner_config = _merge_dicts(runner_type,
                                                 workload["runner"])

                    runner_hash = self._hash(runner_config)

                    workload_report = {
                        "uuid": workload["uuid"],
                        "task_uuid": workload["task_uuid"],
                        "subtask_uuid": workload["subtask_uuid"],
                        "subtask_title": subtask["title"],
                        "scenario_name": workload["name"],
                        "args_hash": self._hash(workload["args"]),
                        "args": workload["args"],
                        "description": workload["description"],
                        "runner_name": workload["runner_type"],
                        "runner_hash": runner_hash,
                        "contexts_hash": self._hash(workload["contexts"]),
                        "started_at": started_at,
                        "load_duration": workload["load_duration"],
                        "full_duration": workload["full_duration"],
                        "pass_sla": workload["pass_sla"],
                        "success_rate": success_rate,
                        "sla_details": [s["detail"]
                                        for s in workload["sla_results"]["sla"]
                                        if not s["success"]]}

                workload_report = MonascaExporter._add_subreport(task_report,
                                                                 "workload",
                                                                 workload_report)
                # do we need to store hooks ?!
                metrics = self._create_workload_metrics(workload_report)

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
        if self.dry_run:
            self._client.validate_metrics(result)
            print("Dumping metrics that would have been posted:")
            deduplicated = sorted({x["name"] for x in result})
            for metric in deduplicated:
                print("Would have posted: %s" % metric)
        else:
            self._client.post(result)
        msg = "Successfully exported results to Monasca"
        return {"print": msg}
