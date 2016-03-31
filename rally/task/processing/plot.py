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
from rally.common.plugin import plugin
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

    errors = []
    output_errors = []
    additive_output_charts = []
    complete_output = []
    for idx, itr in enumerate(data["iterations"]):
        if itr["error"]:
            typ, msg, trace = itr["error"]
            errors.append({"iteration": idx,
                           "type": typ, "message": msg, "traceback": trace})

        for i, additive in enumerate(itr["output"]["additive"]):
            try:
                additive_output_charts[i].add_iteration(additive["data"])
            except IndexError:
                chart_cls = plugin.Plugin.get(additive["chart_plugin"])
                chart = chart_cls(
                    data["info"], title=additive["title"],
                    description=additive.get("description", ""),
                    label=additive.get("label", ""),
                    axis_label=additive.get("axis_label",
                                            "Iteration sequence number"))
                chart.add_iteration(additive["data"])
                additive_output_charts.append(chart)

        complete_charts = []
        for complete in itr["output"]["complete"]:
            complete_chart = dict(complete)
            chart_cls = plugin.Plugin.get(complete_chart.pop("chart_plugin"))
            complete_chart["widget"] = chart_cls.widget
            complete_charts.append(complete_chart)
        complete_output.append(complete_charts)

        for chart in (main_area, main_hist, main_stat, load_profile,
                      atomic_pie, atomic_area, atomic_hist):
            chart.add_iteration(itr)

    kw = data["key"]["kw"]
    cls, method = data["key"]["name"].split(".")
    additive_output = [chart.render() for chart in additive_output_charts]
    iterations_count = data["info"]["iterations_count"]
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
            "histogram": main_hist.render()},
        "load_profile": load_profile.render(),
        "atomic": {"histogram": atomic_hist.render(),
                   "iter": atomic_area.render(),
                   "pie": atomic_pie.render()},
        "table": main_stat.render(),
        "additive_output": additive_output,
        "complete_output": complete_output,
        "output_errors": output_errors,
        "errors": errors,
        "load_duration": data["info"]["load_duration"],
        "full_duration": data["info"]["full_duration"],
        "sla": data["sla"],
        "sla_success": all([s["success"] for s in data["sla"]]),
        "iterations_count": iterations_count,
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
    return source, sorted(tasks, key=lambda r: (r["cls"], r["met"],
                                                int(r["pos"])))


def _extend_results(results):
    """Transform tasks results into extended format.

    This is a temporary workaround adapter that allows
    working with task results using new schema, until
    database refactoring actually comes.

    :param results: tasks results list in old format
    :returns: tasks results list in new format
    """
    extended_results = []
    for result in results:
        generic = {"id": None,
                   "task_uuid": None,
                   "key": result["key"],
                   "data": {"sla": result["sla"],
                            "raw": result["result"],
                            "full_duration": result["full_duration"],
                            "load_duration": result["load_duration"]},
                   "created_at": None,
                   "updated_at": None}
        extended_results.extend(
            objects.Task.extend_results([generic]))
    return extended_results


def plot(tasks_results, include_libs=False):
    extended_results = _extend_results(tasks_results)
    template = ui_utils.get_template("task/report.html")
    source, data = _process_tasks(extended_results)
    return template.render(source=json.dumps(source), data=json.dumps(data),
                           include_libs=include_libs)
