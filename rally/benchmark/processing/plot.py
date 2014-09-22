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


def _prepare_data(data, reduce_rows=1000):
    """Prepare data to be displayed.

      * replace errors with zero values
      * reduce number of rows if necessary
      * count errors
    """

    def _append(d1, d2):
        for k, v in d1.iteritems():
            v.append(d2[k])

    def _merge(d1, d2):
        for k, v in d1.iteritems():
            v[-1] = (v[-1] + d2[k]) / 2.0

    atomic_action_names = (data["result"][0]["atomic_actions"].keys()
                           if data["result"] else [])
    zero_atomic_actions = dict([(a, 0) for a in atomic_action_names])

    total_durations = {"duration": [], "idle_duration": []}
    atomic_durations = dict([(a, []) for a in zero_atomic_actions])
    num_errors = 0

    # For determining which rows should be merged we are using "factor"
    # e.g if we have 100 rows and should reduce it to 75 then we should
    # delete (merge with previous) every 4th row.
    # If we increment "store" to 0.25 in each iteration then we
    # get store >= 1 every 4th iteration.

    data_size = len(data["result"])
    factor = (data_size - reduce_rows + 1) / float(data_size)
    if factor < 0:
        factor = 0.0
    store = 0.0

    for row in data["result"]:
        row.setdefault("atomic_actions", zero_atomic_actions)
        if row["error"]:
            new_row_total = {"duration": 0, "idle_duration": 0}
            new_row_atomic = zero_atomic_actions
            num_errors += 1
        else:
            new_row_total = {
                "duration": row["duration"],
                "idle_duration": row["idle_duration"],
            }
            new_row_atomic = {}
            for k, v in row["atomic_actions"].iteritems():
                new_row_atomic[k] = v if v else 0
        if store < 1:
            _append(total_durations, new_row_total)
            _append(atomic_durations, new_row_atomic)
        else:
            _merge(total_durations, new_row_total)
            _merge(atomic_durations, new_row_atomic)
            store -= 1
        store += factor

    return {
        "total_durations": total_durations,
        "atomic_durations": atomic_durations,
        "num_errors": num_errors,
    }


def _process_main_duration(result, data):
    histogram_data = [r["duration"] for r in result["result"]
                      if not r["error"]]
    histograms = []
    if histogram_data:
        hvariety = histo.hvariety(histogram_data)
        for i in range(len(hvariety)):
            histograms.append(histo.Histogram(histogram_data,
                                              hvariety[i]['number_of_bins'],
                                              hvariety[i]['method']))

    stacked_area = []
    for key in "duration", "idle_duration":
        stacked_area.append({
            "key": key,
            "values": list(enumerate([round(d, 2) for d in
                                      data["total_durations"][key]], start=1)),
        })

    return {
        "pie": [
            {"key": "success", "value": len(histogram_data)},
            {"key": "errors", "value": data["num_errors"]},
        ],
        "iter": stacked_area,
        "histogram": [
            {
                "key": "task",
                "method": histogram.method,
                "values": [{"x": round(x, 2), "y": y}
                           for x, y in zip(histogram.x_axis, histogram.y_axis)]
            } for histogram in histograms
        ],
    }


def _process_atomic(result, data):

    def avg(lst, key=None):
        lst = lst if not key else map(lambda x: x[key], lst)
        return utils.mean(lst)

    # NOTE(boris-42): In our result["result"] we have next structure:
    #                 {"error": NoneOrDict,
    #                  "atomic_actions": {
    #                       "action1": <duration>,
    #                       "action2": <duration>
    #                   }
    #                 }
    #                 Our goal is to get next structure:
    #                 [{"key": $atomic_actions.action,
    #                   "values": [[order, $atomic_actions.duration
    #                              if not $error else 0], ...}]
    #
    #                 Order of actions in "atomic_action" is similiar for
    #                 all iteration. So we should take first non "error"
    #                 iteration. And get in atomitc_iter list:
    #                 [{"key": "action", "values":[]}]
    stacked_area = ([{"key": a, "values": []}
                     for a in result["result"][0]["atomic_actions"]]
                    if result["result"] else [])

    # NOTE(boris-42): pie is similiar to stacked_area, only difference is in
    #                 structure of values. In case of $error we shouldn't put
    #                 anything in pie. In case of non error we should put just
    #                 $atomic_actions.duration (without order)
    pie = []
    histogram_data = []
    if stacked_area:
        pie = copy.deepcopy(stacked_area)
        histogram_data = copy.deepcopy(stacked_area)
        for i, res in enumerate(result["result"]):
            # in case of error put (order, 0.0) to all actions of stacked area
            if res["error"]:
                for k in range(len(stacked_area)):
                    stacked_area[k]["values"].append([i + 1, 0.0])
                continue

            # in case of non error put real durations to pie and stacked area
            for j, action in enumerate(res["atomic_actions"].keys()):
                # in case any single atomic action failed, put 0
                action_duration = res["atomic_actions"][action] or 0.0
                pie[j]["values"].append(action_duration)
                histogram_data[j]["values"].append(action_duration)

    # filter out empty action lists in pie / histogram to avoid errors
    pie = filter(lambda x: x["values"], pie)
    histogram_data = filter(lambda x: x["values"], histogram_data)

    histograms = [[] for atomic_action in range(len(histogram_data))]
    for i, atomic_action in enumerate(histogram_data):
        hvariety = histo.hvariety(atomic_action['values'])
        for v in range(len(hvariety)):
            histograms[i].append(histo.Histogram(atomic_action['values'],
                                                 hvariety[v]['number_of_bins'],
                                                 hvariety[v]['method'],
                                                 atomic_action['key']))
    stacked_area = []
    for name, durations in data["atomic_durations"].iteritems():
        stacked_area.append({
            "key": name,
            "values": list(enumerate([round(d, 2) for d in durations],
                           start=1)),
        })

    return {
        "histogram": [[
            {
                "key": action.key,
                "disabled": i,
                "method": action.method,
                "values": [{"x": round(x, 2), "y": y}
                           for x, y in zip(action.x_axis, action.y_axis)]
            } for action in atomic_action_list]
            for i, atomic_action_list in enumerate(histograms)
        ],
        "iter": stacked_area,
        "pie": map(lambda x: {"key": x["key"], "value": avg(x["values"])}, pie)
    }


def _get_atomic_action_durations(result):
    raw = result.get('result', [])
    actions_data = utils.get_atomic_actions_data(raw)
    table = []
    for action in actions_data:
        durations = actions_data[action]
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
        data = _prepare_data(result)
        output.append({
            "name": "%s (task #%d)" % (info["name"], info["pos"]),
            "config": config,
            "duration": _process_main_duration(result, data),
            "atomic": _process_atomic(result, data),
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
