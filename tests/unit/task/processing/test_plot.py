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
    def test__process_workload(self, mock_charts):
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
        workload = {
            "iterations": iterations, "sla": {}, "pass_sla": True,
            "position": 0,
            "name": "Foo.bar", "description": "Description!!",
            "runner": {"type": "constant"},
            "info": {"atomic": {"foo_action": {"max_duration": 19,
                                               "min_duration": 10}},
                     "full_duration": 40, "load_duration": 32,
                     "iterations_count": 10, "iterations_passed": 10,
                     "max_duration": 14, "min_duration": 5,
                     "output_names": [],
                     "tstamp_end": 25, "tstamp_start": 2},
            "created_at": "xxx_time",
            "hooks": []}

        result = plot._process_workload(
            workload, {"runner": {"type": "constant"}}, 1)
        self.assertEqual(
            {"cls": "Foo", "met": "bar", "pos": "1",
             "name": "bar [2]", "description": "Description!!",
             "runner": "constant", "config": json.dumps(
                 {"Foo.bar": [{"runner": {"type": "constant"}}]},
                 indent=2),
             "created_at": "xxx_time",
             "full_duration": 40, "load_duration": 32, "hooks": [],
             "atomic": {"histogram": "atomic_histogram",
                        "iter": "atomic_stacked", "pie": "atomic_avg"},
             "iterations": {"histogram": "main_histogram",
                            "iter": "main_stacked",
                            "pie": [("success", 10), ("errors", 0)]},
             "iterations_count": 10, "errors": [],
             "load_profile": "load_profile",
             "additive_output": [],
             "complete_output": [[], [], [], [], [], [], [], [], [], []],
             "has_output": False,
             "output_errors": [],
             "sla": {}, "sla_success": True, "table": "main_stats"},
            result)

    @ddt.data(
        {"hooks": [], "expected": []},
        {"hooks": [
            {"config": {
                "trigger": {"args": {"at": [2, 5], "unit": "iteration"},
                            "name": "event"},
                "args": "foo cmd", "description": "Foo", "name": "sys_call"},
             "results": [
                 {"status": "success", "finished_at": 1475589987.525735,
                  "triggered_by": {"event_type": "iteration", "value": 2},
                  "started_at": 1475589987.433399,
                  "output": {
                      "additive": [
                          {"chart_plugin": "StatsTable", "title": "Foo table",
                           "data": [["A", 158], ["B", 177]]}],
                      "complete": []}},
                 {"status": "success", "finished_at": 1475589993.457818,
                  "triggered_by": {"event_type": "iteration", "value": 5},
                  "started_at": 1475589993.432734,
                  "output": {
                      "additive": [
                          {"chart_plugin": "StatsTable", "title": "Foo table",
                           "data": [["A", 243], ["B", 179]]}],
                      "complete": []}}],
             "summary": {"success": 2}},
            {"config": {"trigger": {"args": {"at": [1, 2, 4], "unit": "time"},
                                    "name": "event"},
                        "args": "bar cmd", "name": "sys_call"},
             "results": [
                 {"status": "success", "finished_at": 1475589988.437791,
                  "triggered_by": {"event_type": "time", "value": 1},
                  "started_at": 1475589988.434244,
                  "output": {"additive": [],
                             "complete": [
                                 {"chart_plugin": "Pie", "title": "Bar Pie",
                                  "data": [["F", 4], ["G", 2]]}]}},
                 {"status": "success",
                  "finished_at": 1475589989.437589,
                  "triggered_by": {"event_type": "time", "value": 2},
                  "started_at": 1475589989.433964,
                  "output": {"additive": [],
                             "complete": [
                                 {"chart_plugin": "Pie", "title": "Bar Pie",
                                  "data": [["F", 42], ["G", 24]]}]}}],
             "summary": {"success": 2}}],
         "expected": [
             {"additive": [
                 {"data": {"cols": ["Action", "Min (sec)", "Median (sec)",
                                    "90%ile (sec)", "95%ile (sec)",
                                    "Max (sec)", "Avg (sec)", "Count"],
                           "rows": [["A", 158.0, 200.5, 234.5, 238.75, 243.0,
                                     100.75, 2],
                                    ["B", 177.0, 178.0, 178.8, 178.9, 179.0,
                                     89.5, 2]]},
                  "axis_label": "", "description": "", "label": "",
                  "title": "Foo table", "widget": "Table"}],
              "complete": [], "desc": "Foo", "name": "sys_call"},
             {"additive": [],
              "complete": [
                  {"charts": [{"data": [["F", 4], ["G", 2]],
                               "title": "Bar Pie", "widget": "Pie"}],
                   "finished_at": "2016-10-04 14:06:28",
                   "started_at": "2016-10-04 14:06:28",
                   "status": "success",
                   "triggered_by": "time: 1"},
                  {"charts": [{"data": [["F", 42], ["G", 24]],
                               "title": "Bar Pie", "widget": "Pie"}],
                   "finished_at": "2016-10-04 14:06:29",
                   "started_at": "2016-10-04 14:06:29",
                   "status": "success",
                   "triggered_by": "time: 2"}],
              "desc": "",
              "name": "sys_call"}]})
    @ddt.unpack
    def test__process_hooks(self, hooks, expected):
        self.assertEqual(expected, plot._process_hooks(hooks))

    @mock.patch(PLOT + "_process_workload")
    @mock.patch(PLOT + "json.dumps", return_value="json_data")
    def test__process_workloads(self, mock_json_dumps, mock__process_workload):
        workloads = [{"id": i, "uuid": "uuid-%s" % i, "task_uuid": "task-uuid",
                      "subtask_uuid": "subtask-uuid",
                      "name": "Foo.bar_%s" % i,
                      "description": "Make something useful (or not).",
                      "position": i,
                      "runner": {"type": "constant", "times": 3},
                      "context": {"users": {}},
                      "sla": {"failure_rate": {"max": 0}},
                      "args": {"key1": "value1"},
                      "hooks": [{"config": {"hook1": "xxx"}}],
                      "sla_results": {"sla": []},
                      "start_time": "2997.23.12",
                      "load_duration": 42,
                      "full_duration": 37,
                      "min_duration": 1, "max_duration": 2,
                      "total_iteration_count": 7, "failed_iteration_count": 2,
                      "pass_sla": True} for i in (1, 2, 3, 1)]
        mock__process_workload.side_effect = lambda a, b, c: (
            {"cls": "%s_cls" % a["name"],
             "name": str(c),
             "met": "dummy",
             "pos": str(c)})
        source, p_workloads = plot._process_workloads(workloads)
        self.assertEqual(source, "json_data")
        mock_json_dumps.assert_called_once_with(
            {"Foo.bar_1": [{"runner": {"type": "constant", "times": 3},
                            "hooks": [{"hook1": "xxx"}],
                            "args": {"key1": "value1"},
                            "sla": {"failure_rate": {"max": 0}},
                            "context": {"users": {}}},
                           {"runner": {"type": "constant", "times": 3},
                            "hooks": [{"hook1": "xxx"}],
                            "args": {"key1": "value1"},
                            "sla": {"failure_rate": {"max": 0}},
                            "context": {"users": {}}}],
             "Foo.bar_3": [
                {"runner": {"type": "constant", "times": 3},
                 "hooks": [{"hook1": "xxx"}], "args": {"key1": "value1"},
                 "sla": {"failure_rate": {"max": 0}},
                 "context": {"users": {}}}],
             "Foo.bar_2": [
                {"runner": {"type": "constant", "times": 3},
                 "hooks": [{"hook1": "xxx"}], "args": {"key1": "value1"},
                 "sla": {"failure_rate": {"max": 0}},
                 "context": {"users": {}}}]},
            sort_keys=True, indent=2)
        self.assertEqual([
            {"cls": "Foo.bar_1_cls", "met": "dummy", "name": "0", "pos": "0"},
            {"cls": "Foo.bar_1_cls", "met": "dummy", "name": "1", "pos": "1"},
            {"cls": "Foo.bar_2_cls", "met": "dummy", "name": "0", "pos": "0"},
            {"cls": "Foo.bar_3_cls", "met": "dummy", "name": "0", "pos": "0"}],
            p_workloads)

    @ddt.data({},
              {"include_libs": True},
              {"include_libs": False})
    @ddt.unpack
    @mock.patch(PLOT + "objects.Task")
    @mock.patch(PLOT + "_process_workloads")
    @mock.patch(PLOT + "ui_utils.get_template")
    @mock.patch("rally.common.version.version_string", return_value="42.0")
    def test_plot(self, mock_version_string, mock_get_template,
                  mock__process_workloads, mock_task, **ddt_kwargs):
        task_dict = {"subtasks": [{"workloads": ["foo", "bar"]}]}
        task = mock_task.return_value
        task.extend_results.return_value.to_dict.return_value = task_dict
        mock__process_workloads.return_value = "source", "scenarios"
        mock_get_template.return_value.render.return_value = "tasks_html"

        html = plot.plot(["tasks_results"], **ddt_kwargs)

        self.assertEqual(html, "tasks_html")
        mock_get_template.assert_called_once_with("task/report.html")
        mock__process_workloads.assert_called_once_with(["foo", "bar"])
        if "include_libs" in ddt_kwargs:
            mock_get_template.return_value.render.assert_called_once_with(
                version="42.0", data="\"scenarios\"",
                source="\"source\"",
                include_libs=ddt_kwargs["include_libs"])
        else:
            mock_get_template.return_value.render.assert_called_once_with(
                version="42.0", data="\"scenarios\"",
                source="\"source\"", include_libs=False)

    @mock.patch(PLOT + "objects.Workload.format_workload_config")
    @mock.patch(PLOT + "objects.Task")
    @mock.patch(PLOT + "Trends")
    @mock.patch(PLOT + "ui_utils.get_template")
    @mock.patch("rally.common.version.version_string", return_value="42.0")
    def test_trends(self, mock_version_string, mock_get_template, mock_trends,
                    mock_task, mock_format_workload_config):
        task_dict = {"subtasks": [{"workloads": ["foo", "bar"]}]}
        task = mock_task.return_value
        task.extend_results.return_value.to_dict.return_value = task_dict

        trends = mock.Mock()
        trends.get_data.return_value = ["foo", "bar"]
        mock_trends.return_value = trends
        template = mock.Mock()
        template.render.return_value = "trends html"
        mock_get_template.return_value = template

        result = plot.trends(["tasks_results"])

        self.assertEqual("trends html", result)
        self.assertEqual(
            [mock.call("foo", mock_format_workload_config.return_value),
             mock.call("bar", mock_format_workload_config.return_value)],
            trends.add_result.mock_calls)
        mock_get_template.assert_called_once_with("task/trends.html")
        template.render.assert_called_once_with(version="42.0",
                                                data="[\"foo\", \"bar\"]")


@ddt.ddt
class TrendsTestCase(test.TestCase):

    def test___init__(self):
        trends = plot.Trends()
        self.assertEqual({}, trends._data)
        self.assertRaises(TypeError, plot.Trends, 42)

    @ddt.data({"args": [None], "result": "None"},
              {"args": [""], "result": ""},
              {"args": [" str value "], "result": "str value"},
              {"args": [" 42 "], "result": "42"},
              {"args": ["42"], "result": "42"},
              {"args": [42], "result": "42"},
              {"args": [42.00], "result": "42.0"},
              {"args": [[3.2, 1, " foo ", None]], "result": "1,3.2,None,foo"},
              {"args": [(" def", "abc", [22, 33])], "result": "22,33,abc,def"},
              {"args": [{}], "result": ""},
              {"args": [{1: 2, "a": " b c "}], "result": "1:2|a:b c"},
              {"args": [{"foo": "bar", (1, 2): [5, 4, 3]}],
               "result": "1,2:3,4,5|foo:bar"},
              {"args": [1, 2], "raises": TypeError},
              {"args": [set()], "raises": TypeError})
    @ddt.unpack
    def test__to_str(self, args, result=None, raises=None):
        trends = plot.Trends()
        if raises:
            self.assertRaises(raises, trends._to_str, *args)
        else:
            self.assertEqual(result, trends._to_str(*args))

    @mock.patch(PLOT + "hashlib")
    def test__make_hash(self, mock_hashlib):
        mock_hashlib.md5.return_value.hexdigest.return_value = "md5_digest"
        trends = plot.Trends()
        trends._to_str = mock.Mock()
        trends._to_str.return_value.encode.return_value = "foo_str"

        self.assertEqual("md5_digest", trends._make_hash("foo_obj"))
        trends._to_str.assert_called_once_with("foo_obj")
        trends._to_str.return_value.encode.assert_called_once_with("utf8")
        mock_hashlib.md5.assert_called_once_with("foo_str")

    def _make_result(self, salt, sla_success=True, with_na=False):
        if with_na:
            atomic = {"a": "n/a", "b": "n/a"}
            stat_rows = [
                ["a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 4],
                ["b", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 4],
                ["total", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 4]]
        else:
            atomic = {"a": 123, "b": 456}
            stat_rows = [["a", 0.7, 0.85, 0.9, 0.87, 1.25, 0.67, "100.0%", 4],
                         ["b", 0.5, 0.75, 0.85, 0.9, 1.1, 0.58, "100.0%", 4],
                         ["total", 1.2, 1.55, 1.7, 1.8, 1.5, 0.8, "100.0%", 4]]
        return {
            "name": "Scenario.name_%d" % salt,
            "pass_sla": sla_success,
            "sla": [{"success": sla_success}],
            "info": {"iterations_count": 4, "atomic": atomic,
                     "tstamp_start": 123456.789 + salt,
                     "stat": {"rows": stat_rows,
                              "cols": ["Action", "Min (sec)", "Median (sec)",
                                       "90%ile (sec)", "95%ile (sec)",
                                       "Max (sec)", "Avg (sec)", "Success",
                                       "Count"]}},
            "iterations": ["<iter-0>", "<iter-1>", "<iter-2>", "<iter-3>"]}

    def _sort_trends(self, trends_result):
        for idx in range(len(trends_result)):
            trends_result[idx]["durations"].sort()
            for a_idx in range(len(trends_result[idx]["actions"])):
                trends_result[idx]["actions"][a_idx]["durations"].sort()
        return trends_result

    def test_add_result_and_get_data(self):
        trends = plot.Trends()
        for i in 0, 1:
            trends.add_result(self._make_result(i), "kw_%s" % i)
        expected = [
            {"actions": [{"durations": [("90%ile", [(123456789, 0.9)]),
                                        ("95%ile", [(123456789, 0.87)]),
                                        ("avg", [(123456789, 0.67)]),
                                        ("max", [(123456789, 1.25)]),
                                        ("median", [(123456789, 0.85)]),
                                        ("min", [(123456789, 0.7)])],
                          "name": "a",
                          "success": [("success", [(123456789, 100.0)])]},
                         {"durations": [("90%ile", [(123456789, 0.85)]),
                                        ("95%ile", [(123456789, 0.9)]),
                                        ("avg", [(123456789, 0.58)]),
                                        ("max", [(123456789, 1.1)]),
                                        ("median", [(123456789, 0.75)]),
                                        ("min", [(123456789, 0.5)])],
                          "name": "b",
                          "success": [("success", [(123456789, 100.0)])]}],
             "cls": "Scenario",
             "config": "\"kw_0\"",
             "durations": [("90%ile", [(123456789, 1.7)]),
                           ("95%ile", [(123456789, 1.8)]),
                           ("avg", [(123456789, 0.8)]),
                           ("max", [(123456789, 1.5)]),
                           ("median", [(123456789, 1.55)]),
                           ("min", [(123456789, 1.2)])],
             "length": 1,
             "met": "name_0",
             "name": "Scenario.name_0",
             "sla_failures": 0,
             "stat": {"avg": 1.425, "max": 1.8, "min": 0.8},
             "success": [("success", [(123456789, 100.0)])]},
            {"actions": [{"durations": [("90%ile", [(123457789, 0.9)]),
                                        ("95%ile", [(123457789, 0.87)]),
                                        ("avg", [(123457789, 0.67)]),
                                        ("max", [(123457789, 1.25)]),
                                        ("median", [(123457789, 0.85)]),
                                        ("min", [(123457789, 0.7)])],
                          "name": "a",
                          "success": [("success", [(123457789, 100.0)])]},
                         {"durations": [("90%ile", [(123457789, 0.85)]),
                                        ("95%ile", [(123457789, 0.9)]),
                                        ("avg", [(123457789, 0.58)]),
                                        ("max", [(123457789, 1.1)]),
                                        ("median", [(123457789, 0.75)]),
                                        ("min", [(123457789, 0.5)])],
                          "name": "b",
                          "success": [("success", [(123457789, 100.0)])]}],
             "cls": "Scenario",
             "config": "\"kw_1\"",
             "durations": [("90%ile", [(123457789, 1.7)]),
                           ("95%ile", [(123457789, 1.8)]),
                           ("avg", [(123457789, 0.8)]),
                           ("max", [(123457789, 1.5)]),
                           ("median", [(123457789, 1.55)]),
                           ("min", [(123457789, 1.2)])],
             "length": 1,
             "met": "name_1",
             "name": "Scenario.name_1",
             "sla_failures": 0,
             "stat": {"avg": 1.425, "max": 1.8, "min": 0.8},
             "success": [("success", [(123457789, 100.0)])]}]
        self.assertEqual(expected, self._sort_trends(trends.get_data()))

    def test_add_result_once_and_get_data(self):
        trends = plot.Trends()
        trends.add_result(self._make_result(42, sla_success=False), "kw_42")
        expected = [
            {"actions": [{"durations": [("90%ile", [(123498789, 0.9)]),
                                        ("95%ile", [(123498789, 0.87)]),
                                        ("avg", [(123498789, 0.67)]),
                                        ("max", [(123498789, 1.25)]),
                                        ("median", [(123498789, 0.85)]),
                                        ("min", [(123498789, 0.7)])],
                          "name": "a",
                          "success": [("success", [(123498789, 100.0)])]},
                         {"durations": [("90%ile", [(123498789, 0.85)]),
                                        ("95%ile", [(123498789, 0.9)]),
                                        ("avg", [(123498789, 0.58)]),
                                        ("max", [(123498789, 1.1)]),
                                        ("median", [(123498789, 0.75)]),
                                        ("min", [(123498789, 0.5)])],
                          "name": "b",
                          "success": [("success", [(123498789, 100.0)])]}],
             "cls": "Scenario",
             "config": "\"kw_42\"",
             "durations": [("90%ile", [(123498789, 1.7)]),
                           ("95%ile", [(123498789, 1.8)]),
                           ("avg", [(123498789, 0.8)]),
                           ("max", [(123498789, 1.5)]),
                           ("median", [(123498789, 1.55)]),
                           ("min", [(123498789, 1.2)])],
             "length": 1,
             "met": "name_42",
             "name": "Scenario.name_42",
             "sla_failures": 1,
             "stat": {"avg": 1.425, "max": 1.8, "min": 0.8},
             "success": [("success", [(123498789, 100.0)])]}]
        self.assertEqual(expected, self._sort_trends(trends.get_data()))

    def test_add_result_with_na_and_get_data(self):
        trends = plot.Trends()
        trends.add_result(
            self._make_result(42, sla_success=False, with_na=True), "kw_42")
        expected = [
            {"actions": [{"durations": [("90%ile", [(123498789, "n/a")]),
                                        ("95%ile", [(123498789, "n/a")]),
                                        ("avg", [(123498789, "n/a")]),
                                        ("max", [(123498789, "n/a")]),
                                        ("median", [(123498789, "n/a")]),
                                        ("min", [(123498789, "n/a")])],
                          "name": "a",
                          "success": [("success", [(123498789, 0)])]},
                         {"durations": [("90%ile", [(123498789, "n/a")]),
                                        ("95%ile", [(123498789, "n/a")]),
                                        ("avg", [(123498789, "n/a")]),
                                        ("max", [(123498789, "n/a")]),
                                        ("median", [(123498789, "n/a")]),
                                        ("min", [(123498789, "n/a")])],
                          "name": "b",
                          "success": [("success", [(123498789, 0)])]}],
             "cls": "Scenario",
             "config": "\"kw_42\"",
             "durations": [("90%ile", [(123498789, "n/a")]),
                           ("95%ile", [(123498789, "n/a")]),
                           ("avg", [(123498789, "n/a")]),
                           ("max", [(123498789, "n/a")]),
                           ("median", [(123498789, "n/a")]),
                           ("min", [(123498789, "n/a")])],
             "length": 1,
             "met": "name_42",
             "name": "Scenario.name_42",
             "sla_failures": 1,
             "stat": {"avg": None, "max": None, "min": None},
             "success": [("success", [(123498789, 0)])]}]

        self.assertEqual(expected, self._sort_trends(trends.get_data()))

    def test_get_data_no_results_added(self):
        trends = plot.Trends()
        self.assertEqual([], trends.get_data())
