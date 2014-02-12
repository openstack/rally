# Copyright 2014: Mirantis Inc.
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

import copy
import json
import os

import mako.template


def _process_main_time(result):
    pie = filter(lambda t: not t["error"], result["result"])
    stacked_area = map(
        lambda t: {"idle_time": 0, "time": 0} if t["error"] else t,
        result["result"])

    return {
        "pie": [
            {"key": "success", "value": len(pie)},
            {"key": "errors",
             "value": len(result["result"]) - len(pie)}
        ],
        "iter": [
            {
                "key": "duration",
                "values": [[i + 1, v["time"]]
                           for i, v in enumerate(stacked_area)]
            },
            {
                "key": "idle_duration",
                "values": [[i + 1, v["idle_time"]]
                           for i, v in enumerate(stacked_area)]
            }
        ]
    }


def _process_atomic_time(result):

    def avg(lst, key=None):
        lst = lst if not key else map(lambda x: x[key], lst)
        return sum(lst) / float(len(lst))

    # NOTE(boris-42): In our result["result"] we have next structure:
    #                 {"error": NoneOrDict,
    #                  "atomic_actions_time": [
    #                       {"action": String, "duration": Float},
    #                       ...
    #                   ]}
    #                 Our goal is to get next structure:
    #                 [{"key": $atomic_actions_time.action,
    #                   "values": [[order, $atomic_actions_time.duration
    #                              if not $error else 0], ...}]
    #
    #                 Order of actions in "atomic_action_time" is similiar for
    #                 all iteration. So we should take first non "error"
    #                 iteration. And get in atomitc_iter list:
    #                 [{"key": "action", "values":[]}]
    stacked_area = []
    for r in result["result"]:
        if not r["error"]:
            for action in r["atomic_actions_time"]:
                stacked_area.append({"key": action["action"], "values": []})
            break

    # NOTE(boris-42): pie is similiar to stacked_area, only difference is in
    #                 structure of values. In case of $error we shouldn't put
    #                 anything in pie. In case of non error we should put just
    #                 $atomic_actions_time.duration (without order)
    pie = []
    if stacked_area:
        pie = copy.deepcopy(stacked_area)
        for i, data in enumerate(result["result"]):
            # in case of error put (order, 0.0) to all actions of stacked area
            if data["error"]:
                for k in range(len(stacked_area)):
                    stacked_area[k]["values"].append([i + 1, 0.0])
                continue

            # in case of non error put real durations to pie and stacked area
            for j, action in enumerate(data["atomic_actions_time"]):
                pie[j]["values"].append(action["duration"])
                stacked_area[j]["values"].append([i + 1, action["duration"]])

    return {
        "iter": stacked_area,
        "pie": map(lambda x: {"key": x["key"], "value": avg(x["values"])}, pie)
    }


def _process_results(results):
    output = []
    for result in results:
        info = result["key"]
        output.append({
            "name": "%s (task #%d)" % (info["name"], info["pos"]),
            "config": info["kw"],
            "time": _process_main_time(result),
            "atomic": _process_atomic_time(result)
        })
    return output


def plot(results):
    results = _process_results(results)

    abspath = os.path.dirname(__file__)
    with open("%s/src/index.mako" % abspath) as index:
        template = mako.template.Template(index.read())
        return template.render(data=json.dumps(results),
                               tasks=map(lambda r: r["name"], results))
