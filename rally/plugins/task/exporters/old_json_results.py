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

from rally import consts
from rally import exceptions
from rally.task import exporter


def _to_old_atomic_actions_format(atomic_actions):
    """Convert atomic actions to old format. """
    old_style = collections.OrderedDict()
    for action in atomic_actions:
        duration = action["finished_at"] - action["started_at"]
        if action["name"] in old_style:
            name_template = action["name"] + " (%i)"
            i = 2
            while name_template % i in old_style:
                i += 1
            old_style[name_template % i] = duration
        else:
            old_style[action["name"]] = duration
    return old_style


@exporter.configure("old-json-results")
class OldJSONExporter(exporter.TaskExporter):
    """Generates task report in JSON format as old `rally task results`."""
    def __init__(self, *args, **kwargs):
        super(OldJSONExporter, self).__init__(*args, **kwargs)
        if len(self.tasks_results) != 1:
            raise exceptions.RallyException(
                f"'{self.get_fullname()}' task exporter can be used only for "
                f"a one task.")
        self.task = self.tasks_results[0]

    def _get_report(self):
        results = []
        for w in itertools.chain(*[s["workloads"]
                                   for s in self.task["subtasks"]]):
            for itr in w["data"]:
                itr["atomic_actions"] = _to_old_atomic_actions_format(
                    itr["atomic_actions"]
                )

            w["runner"]["type"] = w["runner_type"]

            def port_hook_cfg(h):
                h["config"] = {
                    "name": h["config"]["action"][0],
                    "args": h["config"]["action"][1],
                    "description": h["config"].get("description", ""),
                    "trigger": {"name": h["config"]["trigger"][0],
                                "args": h["config"]["trigger"][1]}
                }
                return h

            hooks = [port_hook_cfg(h) for h in w["hooks"]]

            created_at = dt.datetime.strptime(w["created_at"],
                                              "%Y-%m-%dT%H:%M:%S")
            created_at = created_at.strftime("%Y-%d-%mT%H:%M:%S")

            results.append({
                "key": {
                    "name": w["name"],
                    "description": w["description"],
                    "pos": w["position"],
                    "kw": {
                        "args": w["args"],
                        "runner": w["runner"],
                        "context": w["contexts"],
                        "sla": w["sla"],
                        "hooks": [h["config"] for h in w["hooks"]],
                    }
                },
                "result": w["data"],
                "sla": w["sla_results"].get("sla", []),
                "hooks": hooks,
                "load_duration": w["load_duration"],
                "full_duration": w["full_duration"],
                "created_at": created_at})

        return results

    def generate(self):
        if len(self.tasks_results) != 1:
            raise exceptions.RallyException(
                f"'{self.get_fullname()}' task exporter can be used only for "
                f"a one task.")

        finished_statuses = (consts.TaskStatus.FINISHED,
                             consts.TaskStatus.ABORTED)
        if self.task["status"] not in finished_statuses:
            raise exceptions.RallyException(
                f"Task status is {self.task['status']}. Results available "
                f"when it is one of {', '.join(finished_statuses)}."
            )

        results = json.dumps(self._get_report(), sort_keys=False, indent=4)

        if self.output_destination:
            return {"files": {self.output_destination: results},
                    "open": "file://" + self.output_destination}
        else:
            return {"print": results}
