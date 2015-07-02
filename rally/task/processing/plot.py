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

import six

from rally.task.processing.charts import histogram as histo
from rally.task.processing import utils
from rally.ui import utils as ui_utils


def _prepare_data(data):
    durations = []
    idle_durations = []
    atomic_durations = {}
    output = {}
    output_errors = []
    output_stacked = []
    errors = []

    # NOTE(maretskiy): We need this extra iteration
    # to determine something that we should know about the data
    # before starting its processing.
    atomic_names = set()
    output_names = set()
    for r in data["result"]:
        atomic_names.update(r["atomic_actions"].keys())
        output_names.update(r["scenario_output"]["data"].keys())

    for idx, r in enumerate(data["result"]):
        # NOTE(maretskiy): Sometimes we miss iteration data.
        # So we care about data integrity by setting zero values
        if len(r["atomic_actions"]) < len(atomic_names):
            for atomic_name in atomic_names:
                r["atomic_actions"].setdefault(atomic_name, 0)

        if len(r["scenario_output"]["data"]) < len(output_names):
            for output_name in output_names:
                r["scenario_output"]["data"].setdefault(output_name, 0)

        if r["scenario_output"]["errors"]:
            output_errors.append((idx, r["scenario_output"]["errors"]))

        for param, value in r["scenario_output"]["data"].items():
            try:
                output[param].append(value)
            except KeyError:
                output[param] = [value]

        if r["error"]:
            type_, message, traceback = r["error"]
            errors.append({"iteration": idx,
                           "type": type_,
                           "message": message,
                           "traceback": traceback})

            # NOTE(maretskiy): Reset failed durations (no sense to display)
            r["duration"] = 0
            r["idle_duration"] = 0

        durations.append(r["duration"])
        idle_durations.append(r["idle_duration"])

        for met, duration in r["atomic_actions"].items():
            try:
                atomic_durations[met].append(duration)
            except KeyError:
                atomic_durations[met] = [duration]

    for k, v in six.iteritems(output):
        output_stacked.append({"key": k, "values": utils.compress(v)})

    for k, v in six.iteritems(atomic_durations):
        atomic_durations[k] = utils.compress(v)

    return {
        "total_durations": {
            "duration": utils.compress(durations),
            "idle_duration": utils.compress(idle_durations)},
        "atomic_durations": atomic_durations,
        "output": output_stacked,
        "output_errors": output_errors,
        "errors": errors,
        "sla": data["sla"],
        "load_duration": data["load_duration"],
        "full_duration": data["full_duration"],
    }


def _process_main_duration(result, data):
    histogram_data = [r["duration"] for r in result["result"]
                      if not r["error"]]
    histograms = []
    if histogram_data:
        hvariety = histo.hvariety(histogram_data)
        for i in range(len(hvariety)):
            histograms.append(histo.Histogram(histogram_data,
                                              hvariety[i]["number_of_bins"],
                                              hvariety[i]["method"]))

    stacked_area = []
    for key in "duration", "idle_duration":
        stacked_area.append({
            "key": key,
            "values": [(i, round(d, 2))
                       for i, d in data["total_durations"][key]],
        })

    return {
        "pie": [
            {"key": "success", "value": len(histogram_data)},
            {"key": "errors", "value": len(data["errors"])},
        ],
        "iter": stacked_area,
        "histogram": [
            {
                "key": "task",
                "method": histogram.method,
                "values": [{"x": round(x, 2), "y": float(y)}
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
    #                 Order of actions in "atomic_action" is similar for
    #                 all iteration. So we should take first non "error"
    #                 iteration. And get in atomitc_iter list:
    #                 [{"key": "action", "values":[]}]
    stacked_area = []
    for row in result["result"]:
        if not row["error"] and "atomic_actions" in row:
            stacked_area = [{"key": a, "values": []}
                            for a in row["atomic_actions"]]
            break

    # NOTE(boris-42): pie is similar to stacked_area, only difference is in
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
    histogram_data = [x for x in histogram_data if x["values"]]

    histograms = [[] for atomic_action in range(len(histogram_data))]
    for i, atomic_action in enumerate(histogram_data):
        hvariety = histo.hvariety(atomic_action["values"])
        for v in range(len(hvariety)):
            histograms[i].append(histo.Histogram(atomic_action["values"],
                                                 hvariety[v]["number_of_bins"],
                                                 hvariety[v]["method"],
                                                 atomic_action["key"]))
    stacked_area = []
    for name, durations in six.iteritems(data["atomic_durations"]):
        stacked_area.append({
            "key": name,
            "values": [(i, round(d, 2)) for i, d in durations],
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
        "pie": [{"key": x["key"], "value": avg(x["values"])} for x in pie]
    }


def _get_atomic_action_durations(result):
    raw = result.get("result", [])
    actions_data = utils.get_atomic_actions_data(raw)
    table = []
    total = []
    for action in actions_data:
        durations = actions_data[action]
        if durations:
            data = [action,
                    round(min(durations), 3),
                    round(utils.median(durations), 3),
                    round(utils.percentile(durations, 0.90), 3),
                    round(utils.percentile(durations, 0.95), 3),
                    round(max(durations), 3),
                    round(utils.mean(durations), 3),
                    "%.1f%%" % (len(durations) * 100.0 / len(raw)),
                    len(raw)]
        else:
            data = [action, None, None, None, None, None, None, 0, len(raw)]

        # Save 'total' - it must be appended last
        if action == "total":
            total = data
            continue
        table.append(data)

    if total:
        table.append(total)

    return table


def _process_results(results):
    output = []
    source_dict = {}
    for result in results:
        table_cols = ["Action",
                      "Min (sec)",
                      "Median (sec)",
                      "90%ile (sec)",
                      "95%ile (sec)",
                      "Max (sec)",
                      "Avg (sec)",
                      "Success",
                      "Count"]
        table_rows = _get_atomic_action_durations(result)
        scenario_name, kw, pos = (result["key"]["name"],
                                  result["key"]["kw"], result["key"]["pos"])
        data = _prepare_data(result)
        cls = scenario_name.split(".")[0]
        met = scenario_name.split(".")[1]
        name = "%s%s" % (met, (pos and " [%d]" % (int(pos) + 1) or ""))

        try:
            source_dict[scenario_name].append(kw)
        except KeyError:
            source_dict[scenario_name] = [kw]
        output.append({
            "cls": cls,
            "met": met,
            "pos": int(pos),
            "name": name,
            "runner": kw["runner"]["type"],
            "config": json.dumps({scenario_name: [kw]}, indent=2),
            "iterations": _process_main_duration(result, data),
            "atomic": _process_atomic(result, data),
            "table_cols": table_cols,
            "table_rows": table_rows,
            "output": data["output"],
            "output_errors": data["output_errors"],
            "errors": data["errors"],
            "load_duration": data["load_duration"],
            "full_duration": data["full_duration"],
            "sla": data["sla"],
            "sla_success": all([sla["success"] for sla in data["sla"]]),
            "iterations_num": len(result["result"]),
        })
    source = json.dumps(source_dict, indent=2, sort_keys=True)
    scenarios = sorted(output, key=lambda r: "%s%s" % (r["cls"], r["name"]))
    return source, scenarios


def plot(results):
    template = ui_utils.get_template("task/report.mako")
    source, scenarios = _process_results(results)
    return template.render(data=json.dumps(scenarios),
                           source=json.dumps(source))
