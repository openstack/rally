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
import json

from rally.common import version as rally_version
from rally.task import exporter

TIMEFORMAT = "%Y-%m-%dT%H:%M:%S"


@exporter.configure("json")
class JSONExporter(exporter.TaskExporter):
    """Generates task report in JSON format."""

    # Revisions:
    #    1.0 - the json report v1
    #    1.1 - add `contexts_results` key with contexts execution results of
    #          workloads.
    #    1.2 - add `env_uuid` and `env_uuid` which represent environment name
    #          and UUID where task was executed
    REVISION = "1.2"

    def _generate_tasks(self):
        tasks = []
        for task in self.tasks_results:
            subtasks = []
            for subtask in task["subtasks"]:
                workloads = []
                for workload in subtask["workloads"]:
                    hooks = [{
                        "config": {"action": dict([h["config"]["action"]]),
                                   "trigger": dict([h["config"]["trigger"]]),
                                   "description": h["config"]["description"]},
                        "results": h["results"],
                        "summary": h["summary"], } for h in workload["hooks"]]
                    workloads.append(
                        collections.OrderedDict(
                            [("uuid", workload["uuid"]),
                             ("description", workload["description"]),
                             ("runner", {
                                 workload["runner_type"]: workload["runner"]}),
                             ("hooks", hooks),
                             ("scenario", {
                                 workload["name"]: workload["args"]}),
                             ("min_duration", workload["min_duration"]),
                             ("max_duration", workload["max_duration"]),
                             ("start_time", workload["start_time"]),
                             ("load_duration", workload["load_duration"]),
                             ("full_duration", workload["full_duration"]),
                             ("statistics", workload["statistics"]),
                             ("data", workload["data"]),
                             ("failed_iteration_count",
                              workload["failed_iteration_count"]),
                             ("total_iteration_count",
                              workload["total_iteration_count"]),
                             ("created_at", workload["created_at"]),
                             ("updated_at", workload["updated_at"]),
                             ("contexts", workload["contexts"]),
                             ("contexts_results",
                              workload["contexts_results"]),
                             ("position", workload["position"]),
                             ("pass_sla", workload["pass_sla"]),
                             ("sla_results", workload["sla_results"]),
                             ("sla", workload["sla"])]
                        )
                    )
                subtasks.append(
                    collections.OrderedDict(
                        [("uuid", subtask["uuid"]),
                         ("title", subtask["title"]),
                         ("description", subtask["description"]),
                         ("status", subtask["status"]),
                         ("created_at", subtask["created_at"]),
                         ("updated_at", subtask["updated_at"]),
                         ("sla", subtask["sla"]),
                         ("workloads", workloads)]
                    )
                )
            tasks.append(
                collections.OrderedDict(
                    [("uuid", task["uuid"]),
                     ("title", task["title"]),
                     ("description", task["description"]),
                     ("status", task["status"]),
                     ("tags", task["tags"]),
                     ("env_uuid", task.get("env_uuid", "n\a")),
                     ("env_name", task.get("env_name", "n\a")),
                     ("created_at", task["created_at"]),
                     ("updated_at", task["updated_at"]),
                     ("pass_sla", task["pass_sla"]),
                     ("subtasks", subtasks)]
                )
            )
        return tasks

    def generate(self):
        results = {"info": {"rally_version": rally_version.version_string(),
                            "generated_at": dt.datetime.strftime(
                                dt.datetime.utcnow(), TIMEFORMAT),
                            "format_version": self.REVISION},
                   "tasks": self._generate_tasks()}

        results = json.dumps(results, sort_keys=False, indent=4)

        if self.output_destination:
            return {"files": {self.output_destination: results},
                    "open": "file://" + self.output_destination}
        else:
            return {"print": results}
