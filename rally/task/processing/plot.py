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

import collections
import json

from rally.common import objects
from rally.task.processing import charts
from rally.ui import utils as ui_utils


def _process_scenario(data, pos):
    main_area = charts.MainStackedAreaChart(data["info"])
    main_hist = charts.MainHistogramChart(data["info"])
    main_stat = charts.MainStatsTable(data["info"])
    load_profile = charts.LoadProfileChart(data["info"])
    atomic_pie = charts.AtomicAvgChart(data["info"])
    atomic_area = charts.AtomicStackedAreaChart(data["info"])
    atomic_hist = charts.AtomicHistogramChart(data["info"])
    output_area = charts.OutputStackedAreaChart(data["info"])

    errors = []
    output_errors = []
    for idx, itr in enumerate(data["iterations"]):
        if itr["error"]:
            typ, msg, trace = itr["error"]
            errors.append({"iteration": idx,
                           "type": typ, "message": msg, "traceback": trace})

        if itr["scenario_output"]["errors"]:
            output_errors.append((idx, itr["scenario_output"]["errors"]))

        for chart in (main_area, main_hist, main_stat, load_profile,
                      atomic_pie, atomic_area, atomic_hist, output_area):
            chart.add_iteration(itr)

    kw = data["key"]["kw"]
    cls, method = data["key"]["name"].split(".")

    return {
        "cls": cls,
        "met": method,
        "pos": str(pos),
        "name": method + (pos and " [%d]" % (pos + 1) or ""),
        "runner": kw["runner"]["type"],
        "config": json.dumps({data["key"]["name"]: [kw]}, indent=2),
        "iterations": {
            "iter": main_area.render(),
            "pie": [("success", (data["info"]["iterations_count"]
                                 - len(errors))),
                    ("errors", len(errors))],
            "histogram": main_hist.render()[0]},
        "load_profile": load_profile.render(),
        "atomic": {"histogram": atomic_hist.render(),
                   "iter": atomic_area.render(),
                   "pie": atomic_pie.render()},
        "table": main_stat.render(),
        "output": output_area.render(),
        "output_errors": output_errors,
        "errors": errors,
        "load_duration": data["info"]["load_duration"],
        "full_duration": data["info"]["full_duration"],
        "sla": data["sla"],
        "sla_success": all([s["success"] for s in data["sla"]]),
        "iterations_count": data["info"]["iterations_count"],
    }


def _process_tasks(tasks_results):
    tasks = []
    source_dict = collections.defaultdict(list)
    position = collections.defaultdict(lambda: -1)

    for scenario in tasks_results:
        name = scenario["key"]["name"]
        position[name] += 1
        source_dict[name].append(scenario["key"]["kw"])
        tasks.append(_process_scenario(scenario, position[name]))

    source = json.dumps(source_dict, indent=2, sort_keys=True)
    return source, sorted(tasks, key=lambda r: r["cls"] + r["name"])


def plot(tasks_results):
    # NOTE(amaretskiy): Transform generic results into extended
    #   results, so they can be processed by charts classes
    extended_results = []
    for result in tasks_results:
        generic = {
            "id": None,
            "task_uuid": None,
            "key": result["key"],
            "data": {
                "sla": result["sla"],
                "raw": result["result"],
                "full_duration": result[
                    "full_duration"],
                "load_duration": result[
                    "load_duration"]},
            "created_at": None,
            "updated_at": None}
        extended_results.extend(
            objects.Task.extend_results([generic]))

    template = ui_utils.get_template("task/report.mako")
    source, data = _process_tasks(extended_results)
    return template.render(source=json.dumps(source), data=json.dumps(data))
