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

from rally.common import logging
from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.common.exporters.elastic import client
from rally.task import exporter

LOG = logging.getLogger(__name__)


@validation.configure("es_exporter_destination")
class Validator(validation.Validator):
    """Validates the destination for ElasticSearch exporter.

    In case when the destination is ElasticSearch cluster, the version of it
    should be 2.* or 5.*
    """
    def validate(self, context, config, plugin_cls, plugin_cfg):
        destination = plugin_cfg["destination"]
        if destination and (not destination.startswith("http://")
                            and not destination.startswith("https://")):
            # it is a path to a local file
            return
        es = client.ElasticSearchClient(destination)
        try:
            version = es.version()
        except exceptions.RallyException as e:
            # re-raise a proper exception to hide redundant traceback
            self.fail(e.format_message())
        if not (version.startswith("2.")
                or version.startswith("5.")
                or version.startswith("6.")):
            self.fail("The unsupported version detected %s." % version)


@validation.add("es_exporter_destination")
@exporter.configure("elastic")
class ElasticSearchExporter(exporter.TaskExporter):
    """Exports task results to the ElasticSearch 2.x, 5.x or 6.x clusters.

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

    TASK_INDEX = "rally_task_data_v1"
    WORKLOAD_INDEX = "rally_workload_data_v1"
    AA_INDEX = "rally_atomic_action_data_v1"
    INDEX_SCHEMAS = {
        TASK_INDEX: {
            "task_uuid": {"type": "keyword"},
            "deployment_uuid": {"type": "keyword"},
            "deployment_name": {"type": "keyword"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "status": {"type": "keyword"},
            "pass_sla": {"type": "boolean"},
            "tags": {"type": "keyword"}
        },
        WORKLOAD_INDEX: {
            "deployment_uuid": {"type": "keyword"},
            "deployment_name": {"type": "keyword"},
            "scenario_name": {"type": "keyword"},
            "scenario_cfg": {"type": "keyword"},
            "description": {"type": "text"},
            "runner_name": {"type": "keyword"},
            "runner_cfg": {"type": "keyword"},
            "contexts": {"type": "keyword"},
            "task_uuid": {"type": "keyword"},
            "subtask_uuid": {"type": "keyword"},
            "started_at": {"type": "date"},
            "load_duration": {"type": "long"},
            "full_duration": {"type": "long"},
            "pass_sla": {"type": "boolean"},
            "success_rate": {"type": "float"},
            "sla_details": {"type": "text"}
        },
        AA_INDEX: {
            "deployment_uuid": {"type": "keyword"},
            "deployment_name": {"type": "keyword"},
            "action_name": {"type": "keyword"},
            "workload_uuid": {"type": "keyword"},
            "scenario_cfg": {"type": "keyword"},
            "contexts": {"type": "keyword"},
            "runner_name": {"type": "keyword"},
            "runner_cfg": {"type": "keyword"},
            "success": {"type": "boolean"},
            "duration": {"type": "float"},
            "started_at": {"type": "date"},
            "finished_at": {"type": "date"},
            "parent": {"type": "keyword"},
            "error": {"type": "keyword"}
        }
    }

    def __init__(self, tasks_results, output_destination, api=None):
        super(ElasticSearchExporter, self).__init__(tasks_results,
                                                    output_destination,
                                                    api=api)
        self._report = []
        self._remote = (
            output_destination is None or (
                output_destination.startswith("http://")
                or self.output_destination.startswith("https://")))
        if self._remote:
            self._client = client.ElasticSearchClient(self.output_destination)

    @staticmethod
    def _pack(obj):

        import morph

        return sorted(["%s=%s" % (k, v)
                       for k, v in morph.flatten(obj).items()])

    def _add_index(self, index, body, doc_id=None, doc_type="data"):
        """Create a document for the specified index with specified id.

        :param index: The name of the index
        :param body: The document. Here is the report of (sla,
            scenario, iteration and atomic action)
        :param doc_id: Document ID. Here we use task/subtask/workload uuid
        :param doc_type: The type of document

        """
        self._report.append(
            json.dumps(
                # use OrderedDict to make the report more unified
                {"index": collections.OrderedDict([
                    ("_index", index),
                    ("_type", doc_type),
                    ("_id", doc_id)])},
                sort_keys=False))
        self._report.append(json.dumps(body))

    def _ensure_indices(self):
        """Check available indices and create require ones if they missed."""
        available_index = set(self._client.list_indices())
        missed_index = {self.TASK_INDEX, self.WORKLOAD_INDEX,
                        self.AA_INDEX} - available_index
        for index in missed_index:
            LOG.debug("Creating '%s' index." % index)
            self._client.create_index(index, doc_type="data",
                                      properties=self.INDEX_SCHEMAS[index])

    @staticmethod
    def _make_action_report(name, workload_id, workload, duration,
                            started_at, finished_at, parent, error):
        # NOTE(andreykurilin): actually, this method just creates a dict object
        #   but we need to have the same format at two places, so the template
        #   transformed into a method.
        parent = parent[0] if parent else None
        return {
            "deployment_uuid": workload["deployment_uuid"],
            "deployment_name": workload["deployment_name"],
            "action_name": name,
            "workload_uuid": workload_id,
            "scenario_cfg": workload["scenario_cfg"],
            "contexts": workload["contexts"],
            "runner_name": workload["runner_name"],
            "runner_cfg": workload["runner_cfg"],
            "success": not bool(error),
            "duration": duration,
            "started_at": started_at,
            "finished_at": finished_at,
            "parent": parent,
            "error": error
        }

    def _process_atomic_actions(self, itr, workload, workload_id,
                                atomic_actions=None, _parent=None, _depth=0,
                                _cache=None):
        """Process atomic actions of an iteration

        :param atomic_actions: A list with an atomic actions
        :param itr: The iteration data
        :param workload: The workload report
        :param workload_id: The workload UUID
        :param _parent: An inner parameter which is used for pointing to the
            parent atomic action
        :param _depth: An inner parameter which is used to mark the level of
            depth while parsing atomic action children
        :param _cache: An inner parameter which is used to avoid conflicts in
            IDs of atomic actions of a single iteration.
        """

        if _depth >= 3:
            return
        cache = _cache or {}

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

            started_at = dt.datetime.utcfromtimestamp(action["started_at"])
            finished_at = dt.datetime.utcfromtimestamp(action["finished_at"])
            started_at = started_at.strftime(consts.TimeFormat.ISO8601)
            finished_at = finished_at.strftime(consts.TimeFormat.ISO8601)

            action_report = self._make_action_report(
                name=action["name"],
                workload_id=workload_id,
                workload=workload,
                duration=(action["finished_at"] - action["started_at"]),
                started_at=started_at,
                finished_at=finished_at,
                parent=_parent,
                error=(itr["error"] if action.get("failed", False) else None)
            )

            self._add_index(self.AA_INDEX, action_report,
                            doc_id=act_id)

            self._process_atomic_actions(
                atomic_actions=action["children"],
                itr=itr,
                workload=workload,
                workload_id=workload_id,
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
                "num": 0}

            # Since the action had not be wrapped by AtomicTimer, we cannot
            # make any assumption about it's duration (start_time) so let's use
            # finished_at timestamp of iteration with 0 duration
            timestamp = (itr["timestamp"] + itr["duration"] +
                         itr["idle_duration"])
            timestamp = dt.datetime.utcfromtimestamp(timestamp)
            timestamp = timestamp.strftime(consts.TimeFormat.ISO8601)
            action_report = self._make_action_report(
                name="no-name-action",
                workload_id=workload_id,
                workload=workload,
                duration=0,
                started_at=timestamp,
                finished_at=timestamp,
                parent=_parent,
                error=itr["error"]
            )
            self._add_index(self.AA_INDEX, action_report, doc_id=act_id)

    def generate(self):
        if self._remote:
            self._ensure_indices()

        for task in self.tasks_results:
            if self._remote:
                if self._client.check_document(self.TASK_INDEX, task["uuid"]):
                    raise exceptions.RallyException(
                        "Failed to push the task %s to the ElasticSearch "
                        "cluster. The document with such UUID already exists" %
                        task["uuid"])

            task_report = {
                "task_uuid": task["uuid"],
                "deployment_uuid": task["env_uuid"],
                "deployment_name": task["env_name"],
                "title": task["title"],
                "description": task["description"],
                "status": task["status"],
                "pass_sla": task["pass_sla"],
                "tags": task["tags"]
            }
            self._add_index(self.TASK_INDEX, task_report,
                            doc_id=task["uuid"])

            # NOTE(andreykurilin): The subtasks do not have much logic now, so
            #   there is no reason to save the info about them.
            for workload in itertools.chain(
                    *[s["workloads"] for s in task["subtasks"]]):

                durations = workload["statistics"]["durations"]
                success_rate = durations["total"]["data"]["success"]
                if success_rate == "n/a":
                    success_rate = 0.0
                else:
                    # cut the % char and transform to the float value
                    success_rate = float(success_rate[:-1]) / 100.0

                started_at = workload["start_time"]
                if started_at:
                    started_at = dt.datetime.utcfromtimestamp(started_at)
                    started_at = started_at.strftime(consts.TimeFormat.ISO8601)
                workload_report = {
                    "task_uuid": workload["task_uuid"],
                    "subtask_uuid": workload["subtask_uuid"],
                    "deployment_uuid": task["env_uuid"],
                    "deployment_name": task["env_name"],
                    "scenario_name": workload["name"],
                    "scenario_cfg": self._pack(workload["args"]),
                    "description": workload["description"],
                    "runner_name": workload["runner_type"],
                    "runner_cfg": self._pack(workload["runner"]),
                    "contexts": self._pack(workload["contexts"]),
                    "started_at": started_at,
                    "load_duration": workload["load_duration"],
                    "full_duration": workload["full_duration"],
                    "pass_sla": workload["pass_sla"],
                    "success_rate": success_rate,
                    "sla_details": [s["detail"]
                                    for s in workload["sla_results"]["sla"]
                                    if not s["success"]]}

                # do we need to store hooks ?!
                self._add_index(self.WORKLOAD_INDEX, workload_report,
                                doc_id=workload["uuid"])

                # Iterations
                for idx, itr in enumerate(workload.get("data", []), 1):
                    itr["id"] = "%(uuid)s_iter_%(num)s" % {
                        "uuid": workload["uuid"],
                        "num": str(idx)}

                    self._process_atomic_actions(
                        itr=itr,
                        workload=workload_report,
                        workload_id=workload["uuid"])
        if self._remote:
            LOG.debug("The info of ElasticSearch cluster to which the results "
                      "will be exported: %s" % self._client.info())
            self._client.push_documents(self._report)

            msg = ("Successfully exported results to ElasticSearch at url "
                   "'%s'" % self.output_destination)
            return {"print": msg}
        else:
            # a new line is required in the end of the file.
            report = "\n".join(self._report) + "\n"
            return {"files": {self.output_destination: report},
                    "open": "file://" + os.path.abspath(
                        self.output_destination)}
