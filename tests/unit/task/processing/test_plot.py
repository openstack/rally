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

import ddt
import mock

from rally.task.processing import plot
from tests.unit import test

PLOT = "rally.task.processing.plot."


@ddt.ddt
class PlotTestCase(test.TestCase):

    @mock.patch(PLOT + "charts")
    def test__process_scenario(self, mock_charts):
        for mock_ins, ret in [
                (mock_charts.MainStatsTable, "main_stats"),
                (mock_charts.MainStackedAreaChart, "main_stacked"),
                (mock_charts.AtomicStackedAreaChart, "atomic_stacked"),
                (mock_charts.OutputStackedAreaDeprecatedChart,
                 "output_stacked"),
                (mock_charts.LoadProfileChart, "load_profile"),
                (mock_charts.MainHistogramChart, "main_histogram"),
                (mock_charts.AtomicHistogramChart, "atomic_histogram"),
                (mock_charts.AtomicAvgChart, "atomic_avg")]:
            setattr(mock_ins.return_value.render, "return_value", ret)
        iterations = [
            {"timestamp": i + 2, "error": [],
             "duration": i + 5, "idle_duration": i,
             "output": {"additive": [], "complete": []},
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
                "atomic": {"histogram": "atomic_histogram",
                           "iter": "atomic_stacked", "pie": "atomic_avg"},
                "iterations": {"histogram": "main_histogram",
                               "iter": "main_stacked",
                               "pie": [("success", 10), ("errors", 0)]},
                "iterations_count": 10, "errors": [],
                "load_profile": "load_profile",
                "additive_output": [],
                "complete_output": [[], [], [], [], [], [], [], [], [], []],
                "output_errors": [],
                "sla": [], "sla_success": True, "table": "main_stats"})

    @mock.patch(PLOT + "_process_scenario")
    @mock.patch(PLOT + "json.dumps", return_value="json_data")
    def test__process_tasks(self, mock_json_dumps, mock__process_scenario):
        tasks_results = [{"key": {"name": i, "kw": "kw_" + i}}
                         for i in ("a", "b", "c", "b")]
        mock__process_scenario.side_effect = lambda a, b: (
            {"cls": "%s_cls" % a["key"]["name"],
             "name": str(b),
             "met": "dummy",
             "pos": str(b)})
        source, tasks = plot._process_tasks(tasks_results)
        self.assertEqual(source, "json_data")
        mock_json_dumps.assert_called_once_with(
            {"a": ["kw_a"], "b": ["kw_b", "kw_b"], "c": ["kw_c"]},
            sort_keys=True, indent=2)
        self.assertEqual(
            tasks,
            [{"cls": "a_cls", "met": "dummy", "name": "0", "pos": "0"},
             {"cls": "b_cls", "met": "dummy", "name": "0", "pos": "0"},
             {"cls": "b_cls", "met": "dummy", "name": "1", "pos": "1"},
             {"cls": "c_cls", "met": "dummy", "name": "0", "pos": "0"}])

    @ddt.data({},
              {"include_libs": True},
              {"include_libs": False})
    @ddt.unpack
    @mock.patch(PLOT + "_process_tasks")
    @mock.patch(PLOT + "_extend_results")
    @mock.patch(PLOT + "ui_utils.get_template")
    @mock.patch(PLOT + "json.dumps", side_effect=lambda s: "json_" + s)
    def test_plot(self, mock_dumps, mock_get_template, mock__extend_results,
                  mock__process_tasks, **ddt_kwargs):
        mock__process_tasks.return_value = "source", "scenarios"
        mock_get_template.return_value.render.return_value = "tasks_html"
        mock__extend_results.return_value = ["extended_result"]
        html = plot.plot("tasks_results", **ddt_kwargs)
        self.assertEqual(html, "tasks_html")
        mock__extend_results.assert_called_once_with("tasks_results")
        mock_get_template.assert_called_once_with("task/report.html")
        mock__process_tasks.assert_called_once_with(["extended_result"])
        if "include_libs" in ddt_kwargs:
            mock_get_template.return_value.render.assert_called_once_with(
                data="json_scenarios", source="json_source",
                include_libs=ddt_kwargs["include_libs"])
        else:
            mock_get_template.return_value.render.assert_called_once_with(
                data="json_scenarios", source="json_source",
                include_libs=False)

    @mock.patch(PLOT + "objects.Task.extend_results")
    def test__extend_results(self, mock_task_extend_results):
        mock_task_extend_results.side_effect = iter(
            [["extended_foo"], ["extended_bar"], ["extended_spam"]])
        tasks_results = [
            {"key": "%s_key" % k, "sla": "%s_sla" % k,
             "full_duration": "%s_full_duration" % k,
             "load_duration": "%s_load_duration" % k,
             "result": "%s_result" % k} for k in ("foo", "bar", "spam")]
        generic_results = [
            {"id": None, "created_at": None, "updated_at": None,
             "task_uuid": None, "key": "%s_key" % k,
             "data": {"raw": "%s_result" % k,
                      "full_duration": "%s_full_duration" % k,
                      "load_duration": "%s_load_duration" % k,
                      "sla": "%s_sla" % k}} for k in ("foo", "bar", "spam")]
        results = plot._extend_results(tasks_results)
        self.assertEqual([mock.call([r]) for r in generic_results],
                         mock_task_extend_results.mock_calls)
        self.assertEqual(["extended_foo", "extended_bar", "extended_spam"],
                         results)

    def test__extend_results_empty(self):
        self.assertEqual([], plot._extend_results([]))
