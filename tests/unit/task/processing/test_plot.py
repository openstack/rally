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

import json

import mock

from rally.task.processing import plot
from tests.unit import test

PLOT = "rally.task.processing.plot."


class PlotTestCase(test.TestCase):

    @mock.patch(PLOT + "charts")
    def test__process_scenario(self, mock_charts):
        for mock_ins, ret in [
                (mock_charts.MainStatsTable, "main_stats"),
                (mock_charts.MainStackedAreaChart, "main_stacked"),
                (mock_charts.AtomicStackedAreaChart, "atomic_stacked"),
                (mock_charts.OutputStackedAreaChart, "output_stacked"),
                (mock_charts.LoadProfileChart, "load_profile"),
                (mock_charts.MainHistogramChart, ["main_histogram"]),
                (mock_charts.AtomicHistogramChart, ["atomic_histogram"]),
                (mock_charts.AtomicAvgChart, "atomic_avg")]:
            setattr(mock_ins.return_value.render, "return_value", ret)
        iterations = [
            {"timestamp": i + 2, "error": [],
             "duration": i + 5, "idle_duration": i,
             "scenario_output": {"errors": "", "data": {}},
             "atomic_actions": {"foo_action": i + 10}} for i in range(10)]
        data = {"iterations": iterations, "sla": [],
                "key": {"kw": {"runner": {"type": "constant"}},
                        "name": "Foo.bar", "pos": 0},
                "info": {"atomic": {"foo_action": {"max_duration": 19,
                                                   "min_duration": 10}},
                         "full_duration": 40, "load_duration": 32,
                         "iterations_count": 10, "iterations_passed": 10,
                         "max_duration": 14, "min_duration": 5,
                         "output_names": [],
                         "tstamp_end": 25, "tstamp_start": 2}}

        task_data = plot._process_scenario(data, 1)
        self.assertEqual(
            task_data, {
                "cls": "Foo", "met": "bar", "name": "bar [2]", "pos": "1",
                "runner": "constant", "config": json.dumps(
                    {"Foo.bar": [{"runner": {"type": "constant"}}]},
                    indent=2),
                "full_duration": 40, "load_duration": 32,
                "atomic": {"histogram": ["atomic_histogram"],
                           "iter": "atomic_stacked", "pie": "atomic_avg"},
                "iterations": {"histogram": "main_histogram",
                               "iter": "main_stacked",
                               "pie": [("success", 10), ("errors", 0)]},
                "iterations_count": 10, "errors": [],
                "load_profile": "load_profile",
                "output": "output_stacked", "output_errors": [],
                "sla": [], "sla_success": True, "table": "main_stats"})

    @mock.patch(PLOT + "_process_scenario")
    @mock.patch(PLOT + "json.dumps", return_value="json_data")
    def test__process_tasks(self, mock_json_dumps, mock__process_scenario):
        tasks_results = [{"key": {"name": i, "kw": "kw_" + i}}
                         for i in ("a", "b", "c", "b")]
        mock__process_scenario.side_effect = lambda a, b: (
            {"cls": "%s_cls" % a["key"]["name"], "name": str(b)})
        source, tasks = plot._process_tasks(tasks_results)
        self.assertEqual(source, "json_data")
        mock_json_dumps.assert_called_once_with(
            {"a": ["kw_a"], "b": ["kw_b", "kw_b"], "c": ["kw_c"]},
            sort_keys=True, indent=2)
        self.assertEqual(
            sorted(tasks, key=lambda x: x["cls"] + x["name"]),
            [{"cls": "a_cls", "name": "0"}, {"cls": "b_cls", "name": "0"},
             {"cls": "b_cls", "name": "1"}, {"cls": "c_cls", "name": "0"}])

    @mock.patch(PLOT + "_process_tasks")
    @mock.patch(PLOT + "objects")
    @mock.patch(PLOT + "ui_utils.get_template")
    @mock.patch(PLOT + "json.dumps", side_effect=lambda s: "json_" + s)
    def test_plot(self, mock_dumps, mock_get_template, mock_objects,
                  mock__process_tasks):
        mock__process_tasks.return_value = "source", "scenarios"
        mock_get_template.return_value.render.return_value = "tasks_html"
        mock_objects.Task.extend_results.return_value = ["extended_result"]
        tasks_results = [
            {"key": "foo_key", "sla": "foo_sla", "result": "foo_result",
             "full_duration": "foo_full_duration",
             "load_duration": "foo_load_duration"}]
        html = plot.plot(tasks_results)
        self.assertEqual(html, "tasks_html")
        generic_results = [
            {"id": None, "created_at": None, "updated_at": None,
             "task_uuid": None, "key": "foo_key",
             "data": {"raw": "foo_result",
                      "full_duration": "foo_full_duration",
                      "sla": "foo_sla",
                      "load_duration": "foo_load_duration"}}]
        mock_objects.Task.extend_results.assert_called_once_with(
            generic_results)
        mock_get_template.assert_called_once_with("task/report.mako")
        mock__process_tasks.assert_called_once_with(["extended_result"])
        mock_get_template.return_value.render.assert_called_once_with(
            data="json_scenarios", source="json_source")
