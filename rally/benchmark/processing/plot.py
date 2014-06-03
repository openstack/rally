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

from rally.benchmark.processing.charts import histogram as histo
from rally.benchmark.processing import utils


def _process_main_duration(result):

    pie = filter(lambda t: not t["error"], result["result"])
    num_successful_iterations = len(pie)
    stacked_area = map(
        lambda t: {"idle_duration": 0, "duration": 0} if t["error"] else t,
        result["result"])
    histogram_data = filter(None, map(
        lambda t: t["duration"] if not t["error"] else None,
        result["result"]))

    histograms = []
    if num_successful_iterations > 0:
        hvariety = histo.hvariety(histogram_data)
        for i in range(len(hvariety)):
            histograms.append(histo.Histogram(histogram_data,
                                              hvariety[i]['number_of_bins'],
                                              hvariety[i]['method']))

    return {
        "pie": [
            {"key": "success", "value": len(pie)},
            {"key": "errors",
             "value": len(result["result"]) - len(pie)}
        ],
        "iter": [
            {
                "key": "duration",
                "values": [[i + 1, v["duration"]]
                           for i, v in enumerate(stacked_area)]
            },
            {
                "key": "idle_duration",
                "values": [[i + 1, v["idle_duration"]]
                           for i, v in enumerate(stacked_area)]
            }
        ],
        "histogram": [
            {
                "key": "task",
                "method": histogram.method,
                "values": [{"x": x, "y": y}
                           for x, y in zip(histogram.x_axis, histogram.y_axis)]
            } for histogram in histograms
        ],
    }


def _process_atomic(result):

    def avg(lst, key=None):
        lst = lst if not key else map(lambda x: x[key], lst)
        return utils.mean(lst)

    # NOTE(boris-42): In our result["result"] we have next structure:
    #                 {"error": NoneOrDict,
    #                  "atomic_actions": [
    #                       {"action": String, "duration": Float},
    #                       ...
    #                   ]}
    #                 Our goal is to get next structure:
    #                 [{"key": $atomic_actions.action,
    #                   "values": [[order, $atomic_actions.duration
    #                              if not $error else 0], ...}]
    #
    #                 Order of actions in "atomic_action" is similiar for
    #                 all iteration. So we should take first non "error"
    #                 iteration. And get in atomitc_iter list:
    #                 [{"key": "action", "values":[]}]
    stacked_area = []
    for r in result["result"]:
        if not r["error"]:
            for action in r["atomic_actions"]:
                stacked_area.append({"key": action["action"], "values": []})
            break

    # NOTE(boris-42): pie is similiar to stacked_area, only difference is in
    #                 structure of values. In case of $error we shouldn't put
    #                 anything in pie. In case of non error we should put just
    #                 $atomic_actions.duration (without order)
    pie = []
    histogram_data = []
    if stacked_area:
        pie = copy.deepcopy(stacked_area)
        histogram_data = copy.deepcopy(stacked_area)
        for i, data in enumerate(result["result"]):
            # in case of error put (order, 0.0) to all actions of stacked area
            if data["error"]:
                for k in range(len(stacked_area)):
                    stacked_area[k]["values"].append([i + 1, 0.0])
                continue

            # in case of non error put real durations to pie and stacked area
            for j, action in enumerate(data["atomic_actions"]):
                pie[j]["values"].append(action["duration"])
                stacked_area[j]["values"].append([i + 1, action["duration"]])
                histogram_data[j]["values"].append(action["duration"])

    histograms = [[] for atomic_action in range(len(histogram_data))]
    for i, atomic_action in enumerate(histogram_data):
        hvariety = histo.hvariety(atomic_action['values'])
        for v in range(len(hvariety)):
            histograms[i].append(histo.Histogram(atomic_action['values'],
                                                 hvariety[v]['number_of_bins'],
                                                 hvariety[v]['method'],
                                                 atomic_action['key']))
    return {
        "histogram": [[
            {
                "key": action.key,
                "disabled": i,
                "method": action.method,
                "values": [{"x": x, "y": y}
                           for x, y in zip(action.x_axis, action.y_axis)]
            } for action in atomic_action_list]
            for i, atomic_action_list in enumerate(histograms)
        ],
        "iter": stacked_area,
        "pie": map(lambda x: {"key": x["key"], "value": avg(x["values"])}, pie)
    }


def _get_atomic_action_durations(result):
    raw = result.get('result', [])
    atomic_actions_names = []
    for r in raw:
        if 'atomic_actions' in r:
            for a in r['atomic_actions']:
                atomic_actions_names.append(a["action"])
            break
    action_durations = {}
    for atomic_action in atomic_actions_names:
        action_durations[atomic_action] = utils.get_durations(
            raw,
            lambda r: next(a["duration"] for a in r["atomic_actions"]
                           if a["action"] == atomic_action),
            lambda r: any((a["action"] == atomic_action)
                          for a in r["atomic_actions"]))

    table = []
    actions_list = action_durations.keys()
    action_durations["total"] = utils.get_durations(
            raw, lambda x: x["duration"], lambda r: not r["error"])
    actions_list.append("total")
    for action in actions_list:
        durations = action_durations[action]
        if durations:
            data = [action,
                    round(min(durations), 3),
                    round(utils.mean(durations), 3),
                    round(max(durations), 3),
                    round(utils.percentile(durations, 0.90), 3),
                    round(utils.percentile(durations, 0.95), 3),
                    "%.1f%%" % (len(durations) * 100.0 / len(raw)),
                    len(raw)]
        else:
            data = [action, None, None, None, None, None, 0, len(raw)]
        table.append(data)

    return table


def _process_results(results):
    output = []
    for result in results:
        table_cols = [
                {"title": "action", "class": "center"},
                {"title": "min (sec)", "class": "center"},
                {"title": "avg (sec)", "class": "center"},
                {"title": "max (sec)", "class": "center"},
                {"title": "90 percentile", "class": "center"},
                {"title": "95 percentile", "class": "center"},
                {"title": "success", "class": "center"},
                {"title": "count", "class": "center"}]
        table_rows = _get_atomic_action_durations(result)
        info = result["key"]
        config = {}
        config[info["name"]] = [info["kw"]]
        output.append({
            "name": "%s (task #%d)" % (info["name"], info["pos"]),
            "config": config,
            "duration": _process_main_duration(result),
            "atomic": _process_atomic(result),
            "table_rows": table_rows,
            "table_cols": table_cols
        })
    output = sorted(output, key=lambda r: r["name"])
    return output


def plot(results):
    results = _process_results(results)

    abspath = os.path.dirname(__file__)
    with open("%s/src/index.mako" % abspath) as index:
        template = mako.template.Template(index.read())
        return template.render(data=json.dumps(results),
                               tasks=map(lambda r: r["name"], results))
