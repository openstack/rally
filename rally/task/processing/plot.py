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
import datetime as dt
import hashlib
import itertools
import json

import six

from rally.common import objects
from rally.common.plugin import plugin
from rally.common import version
from rally import exceptions
from rally.task.processing import charts
from rally.task import scenario
from rally.ui import utils as ui_utils


def _process_hooks(hooks):
    """Prepare hooks data for report."""
    hooks_ctx = []
    for hook in hooks:
        hook_ctx = {"name": hook["config"]["action"][0],
                    "desc": hook["config"].get("description", ""),
                    "additive": [], "complete": []}

        for res in hook["results"]:
            started_at = dt.datetime.utcfromtimestamp(res["started_at"])
            finished_at = dt.datetime.utcfromtimestamp(res["finished_at"])
            triggered_by = "%(event_type)s: %(value)s" % res["triggered_by"]

            for i, data in enumerate(
                    res.get("output", {}).get("additive", [])):
                try:
                    hook_ctx["additive"][i]
                except IndexError:
                    chart_cls = plugin.Plugin.get(data["chart_plugin"])
                    hook_ctx["additive"].append([chart_cls])
                hook_ctx["additive"][i].append(data)

            complete_charts = []
            for data in res.get("output", {}).get("complete", []):
                chart_cls = plugin.Plugin.get(data.pop("chart_plugin"))
                data["widget"] = chart_cls.widget
                complete_charts.append(data)

            if complete_charts:
                hook_ctx["complete"].append(
                    {"triggered_by": triggered_by,
                     "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
                     "finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S"),
                     "status": res["status"],
                     "charts": complete_charts})

        for i in range(len(hook_ctx["additive"])):
            chart_cls = hook_ctx["additive"][i].pop(0)
            iters_count = len(hook_ctx["additive"][i])
            first = hook_ctx["additive"][i][0]
            descr = first.get("description", "")
            axis_label = first.get("axis_label", "")
            chart = chart_cls({"total_iteration_count": iters_count},
                              title=first["title"],
                              description=descr,
                              label=first.get("label", ""),
                              axis_label=axis_label)
            for data in hook_ctx["additive"][i]:
                chart.add_iteration(data["data"])
            hook_ctx["additive"][i] = chart.render()

        if hook_ctx["additive"] or hook_ctx["complete"]:
            hooks_ctx.append(hook_ctx)
    return hooks_ctx


def _process_workload(workload, workload_cfg, pos):
    main_area = charts.MainStackedAreaChart(workload)
    main_hist = charts.MainHistogramChart(workload)
    main_stat = charts.MainStatsTable(workload)
    load_profile = charts.LoadProfileChart(workload)
    atomic_pie = charts.AtomicAvgChart(workload)
    atomic_area = charts.AtomicStackedAreaChart(workload)
    atomic_hist = charts.AtomicHistogramChart(workload)

    errors = []
    output_errors = []
    additive_output_charts = []
    complete_output = []
    for idx, itr in enumerate(workload["data"], 1):
        if itr["error"]:
            typ, msg, trace = itr["error"]
            timestamp = dt.datetime.fromtimestamp(
                itr["timestamp"]).isoformat(sep="\n")
            errors.append({"iteration": idx, "timestamp": timestamp,
                           "type": typ, "message": msg, "traceback": trace})

        for i, additive in enumerate(itr["output"]["additive"]):
            try:
                additive_output_charts[i].add_iteration(additive["data"])
            except IndexError:
                chart_cls = plugin.Plugin.get(additive["chart_plugin"])
                chart = chart_cls(
                    workload, title=additive["title"],
                    description=additive.get("description", ""),
                    label=additive.get("label", ""),
                    axis_label=additive.get("axis_label",
                                            "Iteration sequence number"))
                chart.add_iteration(additive["data"])
                additive_output_charts.append(chart)

        complete_charts = []
        for complete in itr["output"]["complete"]:
            chart_cls = plugin.Plugin.get(complete["chart_plugin"])
            complete["widget"] = chart_cls.widget
            complete_charts.append(chart_cls.render_complete_data(complete))
        complete_output.append(complete_charts)

        for chart in (main_area, main_hist, main_stat, load_profile,
                      atomic_pie, atomic_area, atomic_hist):
            chart.add_iteration(itr)

    cls, method = workload["name"].split(".")
    additive_output = [chart.render() for chart in additive_output_charts]

    return {
        "cls": cls,
        "met": method,
        "pos": str(pos),
        "name": method + (pos and " [%d]" % (pos + 1) or ""),
        "runner": workload["runner_type"],
        "config": json.dumps(workload_cfg, indent=2),
        "hooks": _process_hooks(workload["hooks"]),
        "description": workload.get("description", ""),
        "iterations": {
            "iter": main_area.render(),
            "pie": [("success", (workload["total_iteration_count"]
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
        "has_output": any(additive_output) or any(complete_output),
        "output_errors": output_errors,
        "errors": errors,
        "load_duration": workload["load_duration"],
        "full_duration": workload["full_duration"],
        "created_at": workload["created_at"],
        "sla": workload["sla_results"].get("sla"),
        "sla_success": workload["pass_sla"],
        "iterations_count": workload["total_iteration_count"],
    }


def _process_workloads(workloads):
    p_workloads = []
    position = collections.defaultdict(lambda: -1)

    for workload in workloads:
        name = workload["name"]
        position[name] += 1
        workload_cfg = objects.Workload.to_task(workload)
        p_workloads.append(_process_workload(workload, workload_cfg,
                                             position[name]))

    return sorted(p_workloads,
                  key=lambda r: (r["cls"], r["met"], int(r["pos"])))


def _make_source(tasks):
    # TODO(andreykurilin): include tags someday
    source = collections.OrderedDict([("version", 2)])
    single_task = (len(tasks) == 1)
    if not single_task:
        source["title"] = "A combined task."
        source["description"] = ("The task contains subtasks from a multiple "
                                 "number of tasks.")
    else:
        source["title"] = tasks[0]["title"]
        source["description"] = tasks[0]["description"]
    source["subtasks"] = []
    for task in tasks:
        for subtask in task["subtasks"]:
            subtask_cfg = collections.OrderedDict()
            subtask_cfg["title"] = subtask["title"]
            subtask_cfg["description"] = subtask["description"]
            if not single_task:
                # save original identifiers.
                if subtask_cfg["description"]:
                    subtask_cfg["description"] += "\n"
                subtask_cfg["description"] += (
                    "[Task UUID: %s]" % task["uuid"])
            # subtask_cfg["tags"] = subtask["tags"]
            subtask_cfg["workloads"] = []
            for workload in subtask["workloads"]:
                workload_cfg = collections.OrderedDict()
                workload_cfg["scenario"] = {workload["name"]: workload["args"]}
                workload_cfg["description"] = workload["description"]
                workload_cfg["contexts"] = workload["contexts"]
                workload_cfg["runner"] = {
                    workload["runner_type"]: workload["runner"]}
                workload_cfg["hooks"] = [h["config"]
                                         for h in workload["hooks"]]
                workload_cfg["sla"] = workload["sla"]
                subtask_cfg["workloads"].append(workload_cfg)
            source["subtasks"].append(subtask_cfg)
    return json.dumps(source, indent=2)


def plot(tasks_results, include_libs=False):
    source = _make_source(tasks_results)
    tasks = []
    subtasks = []
    workloads = []
    for task in tasks_results:
        tasks.append(task)
        for subtask in tasks[-1]["subtasks"]:
            workloads.extend(subtask.pop("workloads"))
        subtasks.extend(tasks[-1].pop("subtasks"))

    template = ui_utils.get_template("task/report.html")
    data = _process_workloads(workloads)
    return template.render(version=version.version_string(),
                           source=json.dumps(source),
                           data=json.dumps(data),
                           include_libs=include_libs)


def trends(tasks):
    trends = Trends()
    for task in tasks:
        for workload in itertools.chain(
                *[s["workloads"] for s in task["subtasks"]]):
            trends.add_result(task["uuid"], workload)
    template = ui_utils.get_template("task/trends.html")
    return template.render(version=version.version_string(),
                           data=json.dumps(trends.get_data()))


class Trends(object):
    """Process workloads results and make trends data.

    Group workloads results by their input configuration,
    calculate statistics for these groups and prepare it
    for displaying in trends HTML report.
    """

    def __init__(self):
        self._data = {}

    def _to_str(self, obj):
        """Convert object into string."""
        if obj is None:
            return "None"
        elif isinstance(obj, six.string_types + (int, float)):
            return str(obj).strip()
        elif isinstance(obj, (list, tuple)):
            return ",".join(sorted([self._to_str(v) for v in obj]))
        elif isinstance(obj, dict):
            return "|".join(sorted([":".join([self._to_str(k),
                                              self._to_str(v)])
                                    for k, v in obj.items()]))
        raise TypeError("Unexpected type %(type)r of object %(obj)r"
                        % {"obj": obj, "type": type(obj)})

    def _make_hash(self, obj):
        return hashlib.md5(self._to_str(obj).encode("utf8")).hexdigest()

    def add_result(self, task_uuid, workload):
        workload_cfg = objects.Workload.to_task(workload)
        # NOTE(andreykurilin): workload_cfg is a complite task with one only
        #   one workload. Task format v2 includes such fields like task
        #   description (it contains UUID of an original task), workload
        #   description. These fields do not affect the workload itself, but
        #   makes workload_cfg too unique. We need to crop these fields to find
        #   workloads with equal configs.
        del workload_cfg["description"]
        w_description = workload_cfg["subtasks"][0].pop("description")
        key = self._make_hash(workload_cfg)
        if key not in self._data:
            self._data[key] = {
                "actions": {},
                "sla_failures": 0,
                "name": workload["name"],
                "tasks": [],
                "description": w_description,
                "config": workload_cfg}

        self._data[key]["tasks"].append(task_uuid)
        if (self._data[key]["description"] and
                self._data[key]["description"] != w_description):
            self._data[key]["description"] = None

        self._data[key]["sla_failures"] += not workload["pass_sla"]

        duration_stats = workload["statistics"]["durations"]
        if not workload["start_time"]:
            # NOTE(andreykurilin): The workload didn't start. Probably,
            #   one of contexts failed.
            ts = None
        else:
            ts = int(workload["start_time"] * 1000)

        for action in itertools.chain(duration_stats["atomics"],
                                      [duration_stats["total"]]):
            action_name = action["display_name"]
            # NOTE(amaretskiy): some atomic actions can be missed due to
            #   failures. We can ignore that because we use NVD3 lineChart()
            #   for displaying trends, which is safe for missed points
            if action_name not in self._data[key]["actions"]:
                self._data[key]["actions"][action_name] = {
                    "durations": {"min": [], "median": [], "90%ile": [],
                                  "95%ile": [], "max": [], "avg": []},
                    "success": []}
            try:
                success = float(action["data"]["success"].rstrip("%"))
            except ValueError:
                # Got "n/a" for some reason
                success = 0

            self._data[key]["actions"][action_name]["success"].append(
                (ts, success))

            for tgt in ("min", "median", "90%ile", "95%ile", "max", "avg"):
                d = self._data[key]["actions"][action_name]["durations"]
                d[tgt].append((ts, action["data"][tgt]))

    def get_data(self):
        trends = []

        for wload in self._data.values():
            workload_cfg = wload["config"]
            # TODO(andreykurilin): The description can be too long and
            #   unfriendly while displaying. Move displaying tasks UUIDs
            #   under html report control.
            workload_cfg["description"] = ("Task(s) with the workload: %s" %
                                           ", ".join(wload["tasks"]))
            if not wload["description"]:
                try:
                    wload["description"] = scenario.Scenario.get(
                        wload["name"]).get_info()["title"]
                except (exceptions.PluginNotFound,
                        exceptions.MultiplePluginsFound):
                    wload["description"] = ""
            workload_cfg["subtasks"][0]["description"] = wload["description"]
            trend = {"stat": {},
                     "name": wload["name"],
                     "cls": wload["name"].split(".")[0],
                     "met": wload["name"].split(".")[1],
                     "sla_failures": wload["sla_failures"],
                     "config": json.dumps(workload_cfg, indent=2),
                     "actions": []}

            for action, data in wload["actions"].items():
                action_durs = [(k, sorted(v))
                               for k, v in data["durations"].items()]
                if action == "total":
                    trend.update(
                        {"length": len(data["success"]),
                         "durations": action_durs,
                         "success": [("success", sorted(data["success"]))]})
                else:
                    trend["actions"].append(
                        {"name": action,
                         "durations": action_durs,
                         "success": [("success", sorted(data["success"]))]})

            for stat, comp in (("min", charts.streaming.MinComputation()),
                               ("max", charts.streaming.MaxComputation()),
                               ("avg", charts.streaming.MeanComputation())):
                for k, v in trend["durations"]:
                    for i in v:
                        if isinstance(i[1], (float,) + six.integer_types):
                            comp.add(i[1])
                trend["stat"][stat] = comp.result()

            trends.append(trend)

        return sorted(trends, key=lambda i: i["name"])
