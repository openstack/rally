# Copyright 2015: Mirantis Inc.
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
from unittest import mock

import ddt

from rally.common.plugin import plugin
from rally.task.processing import charts
from tests.unit import test

CHARTS = "rally.task.processing.charts."


class ChartTestCase(test.TestCase):

    class Chart(charts.Chart):

        widget = "FooWidget"

        def _map_iteration_values(self, iteration):
            return [("foo_" + k, iteration[k]) for k in ["a", "b"]]

    @property
    def wload_info(self):
        return {
            "total_iteration_count": 42,
            "statistics": {
                "durations": {
                    "total": {"name": "total",
                              "duration": 6,
                              "display_name": "total",
                              "children": [],
                              "count": 1},
                    "atomics": [
                        {"name": "a", "duration": 1, "display_name": "a",
                         "children": [], "count": 1},
                        {"name": "b", "duration": 2, "display_name": "b",
                         "children": [], "count": 1},
                        {"name": "c", "duration": 3, "display_name": "c",
                         "children": [], "count": 1}
                    ]
                }
            }
        }

    def test___init__(self):
        self.assertRaises(TypeError, charts.Chart, self.wload_info)
        chart = self.Chart(self.wload_info)
        self.assertIsInstance(chart, plugin.Plugin)
        self.assertEqual({}, chart._data)
        self.assertEqual(42, chart.base_size)
        self.assertEqual(1000, chart.zipped_size)
        chart = self.Chart(self.wload_info, zipped_size=24)
        self.assertEqual({}, chart._data)
        self.assertEqual(42, chart.base_size)
        self.assertEqual(24, chart.zipped_size)

    @mock.patch(CHARTS + "utils.GraphZipper")
    def test_add_iteration_and_render(self, mock_graph_zipper):
        gzipper_a = mock.Mock(get_zipped_graph=lambda: "a_points")
        gzipper_b = mock.Mock(get_zipped_graph=lambda: "b_points")
        mock_graph_zipper.side_effect = [gzipper_a, gzipper_b]
        chart = self.Chart(self.wload_info, 24)
        self.assertEqual([], chart.render())
        [chart.add_iteration(itr) for itr in [{"a": 1, "b": 2},
                                              {"a": 3, "b": 4}]]
        self.assertEqual([mock.call(42, 24), mock.call(42, 24)],
                         mock_graph_zipper.mock_calls)
        self.assertEqual(2, len(chart._data))
        self.assertEqual([mock.call(1), mock.call(3)],
                         chart._data["foo_a"].add_point.mock_calls)
        self.assertEqual([mock.call(2), mock.call(4)],
                         chart._data["foo_b"].add_point.mock_calls)
        self.assertEqual([("foo_a", "a_points"), ("foo_b", "b_points")],
                         chart.render())

    def test_render_complete_data(self):
        return_val = self.Chart.render_complete_data("aa")
        self.assertEqual("aa", return_val)

    def test__fix_atomic_actions(self):
        chart = self.Chart(self.wload_info)
        self.assertEqual(
            [("a", 5), ("b", 6), ("c", 0)],
            chart._fix_atomic_actions({"a": {"duration": 5},
                                       "b": {"duration": 6}}))

    def test__get_atomic_names(self):
        chart = self.Chart(self.wload_info)
        self.assertEqual(["a", "b", "c"],
                         chart._get_atomic_names())


class MainStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.MainStackedAreaChart({"total_iteration_count": 3,
                                             "failed_iteration_count": 0}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(itr) for itr in (
            {"duration": 1.1, "idle_duration": 2.2, "error": []},
            {"error": [], "duration": 1.1, "idle_duration": 0.5},
            {"duration": 1.3, "idle_duration": 3.4, "error": []})]
        expected = [("duration", [[1, 1.1], [2, 1.1], [3, 1.3]]),
                    ("idle_duration", [[1, 2.2], [2, 0.5], [3, 3.4]])]
        self.assertEqual(expected, chart.render())

    def test_add_iteration_and_render_with_failed_iterations(self):
        chart = charts.MainStackedAreaChart({"total_iteration_count": 3,
                                             "failed_iteration_count": 2}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(itr) for itr in (
            {"duration": 1.1, "idle_duration": 2.2, "error": []},
            {"error": ["foo_err"], "duration": 1.1, "idle_duration": 0.5},
            {"duration": 1.3, "idle_duration": 3.4, "error": ["foo_err"]})]
        expected = [("duration", [[1, 1.1], [2, 0], [3, 0]]),
                    ("idle_duration", [[1, 2.2], [2, 0], [3, 0]]),
                    ("failed_duration", [[1, 0], [2, 1.6], [3, 4.7]])]
        self.assertEqual(expected, chart.render())


class AtomicStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        iterations = (
            {"atomic_actions": [{"name": "foo",
                                 "children": [],
                                 "started_at": 0,
                                 "finished_at": 1.1}],
             "error": []},
            {"atomic_actions": [{"name": "foo",
                                 "children": [],
                                 "started_at": 0,
                                 "finished_at": 1.1},
                                {"name": "bar",
                                 "children": [],
                                 "started_at": 0,
                                 "finished_at": 1.2}
                                ],
             "error": [], "duration": 40, "idle_duration": 2},
            {"atomic_actions": [{"name": "bar",
                                 "children": [],
                                 "started_at": 0,
                                 "finished_at": 1.2}],
             "error": [], "duration": 5.5, "idle_duration": 2.5})
        expected = [("bar", [[1, 0], [2, 1.2], [3, 1.2]]),
                    ("foo", [[1, 1.1], [2, 1.1], [3, 0]])]
        chart = charts.AtomicStackedAreaChart(
            {"total_iteration_count": 3,
             "failed_iteration_count": 0,
             "statistics": {
                 "durations": {
                     "total": {"name": "total",
                               "duration": 3,
                               "display_name": "total",
                               "children": [],
                               "count": 1},
                     "atomics": [
                         {"name": "foo", "duration": 1, "display_name": "foo",
                          "children": [], "count": 1},
                         {"name": "bar", "duration": 2, "display_name": "bar",
                          "children": [], "count": 1}
                     ]
                 }
             }}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(iteration) for iteration in iterations]
        self.assertEqual(expected, sorted(chart.render()))

    def test_add_iteration_and_render_with_failed_iterations(self):
        iterations = (
            {
                "atomic_actions": [
                    {"name": "foo",
                     "started_at": 0,
                     "finished_at": 1.1,
                     "children": []}
                ],
                "error": []
            },
            {
                "atomic_actions": [
                    {"name": "foo",
                     "started_at": 0,
                     "finished_at": 1.1,
                     "children": []},
                    {"name": "bar",
                     "started_at": 0,
                     "finished_at": 1.2,
                     "children": []}
                ],
                "error": ["foo_err"], "duration": 40, "idle_duration": 2},
            {
                "atomic_actions": [
                    {"name": "bar",
                     "started_at": 0,
                     "finished_at": 1.2,
                     "children": []}
                ],
                "error": ["foo_err"], "duration": 5.5, "idle_duration": 2.5})
        expected = [("bar", [[1, 0], [2, 1.2], [3, 1.2]]),
                    ("failed_duration", [[1, 0], [2, 39.7], [3, 6.8]]),
                    ("foo", [[1, 1.1], [2, 1.1], [3, 0]])]
        chart = charts.AtomicStackedAreaChart(
            {"total_iteration_count": 3, "failed_iteration_count": 2,
             "statistics": {
                 "durations": {
                     "total": {"name": "total",
                               "display_name": "total",
                               "duration": 4,
                               "count": 1,
                               "children": []},
                     "atomics": [
                         {"name": "foo",
                          "display_name": "foo",
                          "duration": 2,
                          "count": 1,
                          "children": []},
                         {"name": "bar",
                          "display_name": "bar",
                          "duration": 2,
                          "count": 1,
                          "children": []}
                     ]}}}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(iteration) for iteration in iterations]
        self.assertEqual(expected, sorted(chart.render()))


class AvgChartTestCase(test.TestCase):

    class AvgChart(charts.AvgChart):
        def _map_iteration_values(self, iteration):
            return iteration["foo"].items()

    def test_add_iteration_and_render(self):
        chart = self.AvgChart({"total_iteration_count": 3})
        self.assertIsInstance(chart, charts.AvgChart)
        data = ({"a": 1.3, "b": 4.3},
                {"a": 2.4, "b": 5.4},
                {"a": 3.5, "b": 7.7})
        for x in data:
            chart.add_iteration({"foo": x})
        self.assertEqual([("a", 2.4), ("b", 5.8)], sorted(chart.render()))


class AtomicAvgChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.AtomicAvgChart(
            {"total_iteration_count": 3,
             "statistics": {
                 "durations": {
                     "total": {"name": "total",
                               "duration": 3,
                               "display_name": "total",
                               "children": [],
                               "count": 1},
                     "atomics": [
                         {"name": "foo", "duration": 1, "display_name": "foo",
                          "children": [], "count": 1},
                         {"name": "bar", "duration": 2, "display_name": "bar",
                          "children": [], "count": 1}
                     ]
                 }
             }})
        self.assertIsInstance(chart, charts.AvgChart)
        for a in ([{"name": "foo", "started_at": 0, "finished_at": 2,
                    "children": []},
                   {"name": "bar", "started_at": 0, "finished_at": 5,
                    "children": []}],
                  [{"name": "foo", "started_at": 0, "finished_at": 4,
                    "children": []}],
                  [{"name": "bar", "started_at": 0, "finished_at": 7,
                    "children": []}]):
            chart.add_iteration({"atomic_actions": a})
        self.assertEqual([("bar", 4.0), ("foo", 2.0)], sorted(chart.render()))


@ddt.ddt
class LoadProfileChartTestCase(test.TestCase):

    @ddt.data(
        {"info": {"total_iteration_count": 9,
                  "data": [{"timestamp": 0.0}],
                  "load_duration": 8.0},
         "iterations": [(0.0, 0.5), (0.5, 0.5), (2.0, 4.0), (2.0, 2.0),
                        (4.0, 2.0), (6.0, 0.5), (6.5, 0.5), (7.5, 0.5),
                        (7.5, 1.5)],
         "kwargs": {"scale": 8},
         "expected": [("parallel iterations",
                       [(0.0, 0), (1.25, 0.8), (2.5, 0.8), (3.75, 2),
                        (5.0, 2.0), (6.25, 1.8), (7.5, 0.6000000000000001),
                        (8.75, 1.4), (10.0, 0.2)])]},
        {"info": {"total_iteration_count": 6,
                  "data": [{"timestamp": 0.0}],
                  "load_duration": 12.0},
         "iterations": [(0.0, 0.75), (0.75, 0.75), (1.5, 0.375), (3.0, 5.0),
                        (3.75, 4.25), (10.0, 1.0)],
         "kwargs": {"name": "Custom name", "scale": 8},
         "expected": [("Custom name",
                       [(0.0, 0), (1.875, 1.0), (3.75, 0.4),
                        (5.625, 2.0), (7.5, 2), (9.375, 0.5333333333333333),
                        (11.25, 0.5333333333333333), (13.125, 0),
                        (15.0, 0)])]},
        {"info": {"total_iteration_count": 2,
                  "data": [{"timestamp": 0.0}],
                  "load_duration": 1.0},
         "iterations": [(0.0, 0.5), (0.5, 0.5)],
         "kwargs": {"scale": 4},
         "expected": [("parallel iterations",
                       [(0.0, 0), (0.375, 1.0), (0.75, 1.0),
                        (1.125, 0.6666666666666666), (1.5, 0)])]},
        {"info": {"total_iteration_count": 2,
                  "data": [],
                  "load_duration": 1.0,
                  "start_time": 0.0},
         "iterations": [(0.0, 0.5), (0.5, 0.5)],
         "kwargs": {"scale": 4},
         "expected": [("parallel iterations",
                       [(0.0, 0), (0.375, 1.0), (0.75, 1.0),
                        (1.125, 0.6666666666666666), (1.5, 0)])]})
    @ddt.unpack
    def test_add_iteration_and_render(self, info, iterations, kwargs,
                                      expected):
        chart = charts.LoadProfileChart(info, **kwargs)
        self.assertIsInstance(chart, charts.Chart)
        for iteration in iterations:
            ts, duration = iteration
            chart.add_iteration({"timestamp": ts, "duration": duration})
        self.assertEqual(expected, chart.render())


@ddt.ddt
class HistogramChartTestCase(test.TestCase):

    class HistogramChart(charts.HistogramChart):

        def __init__(self, workload_info):
            super(HistogramChartTestCase.HistogramChart,
                  self).__init__(workload_info)
            self._data["bar"] = {"views": self._init_views(1.2, 4.2),
                                 "disabled": None}

        def _map_iteration_values(self, iteration):
            return iteration["foo"].items()

    def test_add_iteration_and_render(self):
        chart = self.HistogramChart({"total_iteration_count": 3})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration({"foo": x}) for x in ({"bar": 1.2},
                                                   {"bar": 2.4},
                                                   {"bar": 4.2})]
        expected = {
            "data": [
                [{"disabled": None, "key": "bar", "view": "Square Root Choice",
                  "values": [{"x": 2.7, "y": 2}, {"x": 4.2, "y": 1}]}],
                [{"disabled": None, "key": "bar", "view": "Sturges Formula",
                  "values": [{"x": 2.2, "y": 1}, {"x": 3.2, "y": 1},
                             {"x": 4.2, "y": 1}]}],
                [{"disabled": None, "key": "bar", "view": "Rice Rule",
                  "values": [{"x": 2.2, "y": 1}, {"x": 3.2, "y": 1},
                             {"x": 4.2, "y": 1}]}]],
            "views": [{"id": 0, "name": "Square Root Choice"},
                      {"id": 1, "name": "Sturges Formula"},
                      {"id": 2, "name": "Rice Rule"}]}
        self.assertEqual(expected, chart.render())

    @ddt.data(
        {"base_size": 2, "min_value": 1, "max_value": 4,
         "expected": [{"bins": 2, "view": "Square Root Choice",
                       "x": [2.5, 4.0], "y": [0, 0]},
                      {"bins": 2, "view": "Sturges Formula",
                       "x": [2.5, 4.0], "y": [0, 0]},
                      {"bins": 3, "view": "Rice Rule",
                       "x": [2.0, 3.0, 4.0], "y": [0, 0, 0]}]},
        {"base_size": 100, "min_value": 27, "max_value": 42,
         "expected": [
             {"bins": 10, "view": "Square Root Choice",
              "x": [28.5, 30.0, 31.5, 33.0, 34.5, 36.0, 37.5, 39.0, 40.5,
                    42.0], "y": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
             {"bins": 8, "view": "Sturges Formula",
              "x": [28.875, 30.75, 32.625, 34.5, 36.375, 38.25, 40.125,
                    42.0], "y": [0, 0, 0, 0, 0, 0, 0, 0]},
             {"bins": 10, "view": "Rice Rule",
              "x": [28.5, 30.0, 31.5, 33.0, 34.5, 36.0, 37.5, 39.0, 40.5,
                    42.0], "y": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}]})
    @ddt.unpack
    def test_views(self, base_size=None, min_value=None, max_value=None,
                   expected=None):
        chart = self.HistogramChart({"total_iteration_count": base_size})
        self.assertEqual(expected, chart._init_views(min_value, max_value))


class MainHistogramChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.MainHistogramChart(
            {"total_iteration_count": 3, "min_duration": 2, "max_duration": 7})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration(itr) for itr in (
            {"duration": 1.1, "idle_duration": 2.2, "error": None},
            {"error": True},
            {"duration": 1.3, "idle_duration": 3.4, "error": None})]
        expected = {
            "data": [
                [{"disabled": None, "key": "task",
                  "values": [{"x": 4.5, "y": 3}, {"x": 7.0, "y": 0}],
                  "view": "Square Root Choice"}],
                [{"disabled": None, "key": "task", "view": "Sturges Formula",
                  "values": [{"x": 3.666666666666667, "y": 3},
                             {"x": 5.333333333333334, "y": 0},
                             {"x": 7.0, "y": 0}]}],
                [{"disabled": None, "key": "task", "view": "Rice Rule",
                  "values": [{"x": 3.666666666666667, "y": 3},
                             {"x": 5.333333333333334, "y": 0},
                             {"x": 7.0, "y": 0}]}]],
            "views": [{"id": 0, "name": "Square Root Choice"},
                      {"id": 1, "name": "Sturges Formula"},
                      {"id": 2, "name": "Rice Rule"}]}
        self.assertEqual(expected, chart.render())


class AtomicHistogramChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.AtomicHistogramChart(
            {"total_iteration_count": 3, "statistics": {
                "durations": {
                    "total": {"name": "total",
                              "duration": 6,
                              "display_name": "total",
                              "children": [],
                              "count": 1},
                    "atomics": [
                        {
                            "name": "foo",
                            "duration": 1,
                            "display_name": "foo",
                            "children": [],
                            "count": 1,
                            "data": {"min": 1.6,
                                     "max": 2.8}
                        },
                        {
                            "name": "bar",
                            "duration": 2,
                            "display_name": "bar",
                            "children": [],
                            "count": 1,
                            "data": {"min": 3.1,
                                     "max": 5.5}}
                    ]
                }
            }})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration({"atomic_actions": a})
         for a in ([{"name": "foo", "started_at": 0, "finished_at": 1.6,
                     "children": []},
                    {"name": "bar", "started_at": 0, "finished_at": 3.1,
                     "children": []}],
                   [{"name": "foo", "started_at": 0, "finished_at": 2.8,
                     "children": []}],
                   [{"name": "bar", "started_at": 0, "finished_at": 5.5,
                     "children": []}])]
        expected = {
            "data": [
                [{"disabled": 0, "key": "foo", "view": "Square Root Choice",
                  "values": [{"x": 2.2, "y": 2}, {"x": 2.8, "y": 1}]},
                 {"disabled": 1, "key": "bar", "view": "Square Root Choice",
                  "values": [{"x": 4.3, "y": 2}, {"x": 5.5, "y": 1}]}],
                [{"disabled": 0, "key": "foo", "view": "Sturges Formula",
                  "values": [{"x": 2.0, "y": 2}, {"x": 2.4, "y": 0},
                             {"x": 2.8, "y": 1}]},
                 {"disabled": 1, "key": "bar", "view": "Sturges Formula",
                  "values": [{"x": 3.9, "y": 2}, {"x": 4.7, "y": 0},
                             {"x": 5.5, "y": 1}]}],
                [{"disabled": 0, "key": "foo", "view": "Rice Rule",
                  "values": [{"x": 2.0, "y": 2}, {"x": 2.4, "y": 0},
                             {"x": 2.8, "y": 1}]},
                 {"disabled": 1, "key": "bar", "view": "Rice Rule",
                  "values": [{"x": 3.9, "y": 2}, {"x": 4.7, "y": 0},
                             {"x": 5.5, "y": 1}]}]],
            "views": [{"id": 0, "name": "Square Root Choice"},
                      {"id": 1, "name": "Sturges Formula"},
                      {"id": 2, "name": "Rice Rule"}]}
        self.assertEqual(expected, chart.render())


class TableTestCase(test.TestCase):

    class Table(charts.Table):
        columns = ["Name", "Min", "Max", "Max rounded by 2"]

        def __init__(self, *args, **kwargs):
            super(TableTestCase.Table, self).__init__(*args, **kwargs)
            for name in "foo", "bar":
                self._data[name] = [
                    [charts.streaming.MinComputation(), None],
                    [charts.streaming.MaxComputation(), None],
                    [charts.streaming.MaxComputation(),
                     lambda st, has_result: round(st.result(), 2)
                     if has_result else "n/a"]]

        def _map_iteration_values(self, iteration):
            return iteration

        def add_iteration(self, iteration):
            for name, value in self._map_iteration_values(iteration).items():
                for i, dummy in enumerate(self._data[name]):
                    self._data[name][i][0].add(value)

    def test___init__(self):
        self.assertRaises(TypeError, charts.Table,
                          {"total_iteration_count": 42})

    def test__round(self):
        table = self.Table({"total_iteration_count": 4})

        class FakeSA(charts.streaming.StreamingAlgorithm):
            def add(self, value):
                pass

            def merge(self, other):
                pass

            def result(self):
                return 42.424242

        self.assertRaises(TypeError, table._round, FakeSA())
        self.assertEqual("n/a", table._round(FakeSA(), False))
        self.assertEqual(round(42.424242, 3), table._round(FakeSA(), True))

    def test__row_has_results(self):
        table = self.Table({"total_iteration_count": 1})
        for st_cls in (charts.streaming.MinComputation,
                       charts.streaming.MaxComputation,
                       charts.streaming.MeanComputation):
            st = st_cls()
            self.assertFalse(table._row_has_results([(st, None)]))
            st.add(0)
            self.assertTrue(table._row_has_results([(st, None)]))

    def test__row_has_results_and_get_rows(self):
        table = self.Table({"total_iteration_count": 3})
        self.assertFalse(table._row_has_results(table._data["foo"]))
        self.assertFalse(table._row_has_results(table._data["bar"]))
        self.assertEqual(
            [["foo", "n/a", "n/a", "n/a"], ["bar", "n/a", "n/a", "n/a"]],
            table.get_rows())
        for i in range(3):
            table.add_iteration({"foo": i + 1.2, "bar": i + 3.456})
        self.assertTrue(table._row_has_results(table._data["foo"]))
        self.assertTrue(table._row_has_results(table._data["bar"]))
        self.assertEqual(
            [["foo", 1.2, 3.2, 3.2], ["bar", 3.456, 5.456, 5.46]],
            table.get_rows())

    def test_render(self):
        table = self.Table({"total_iteration_count": 42})
        table.get_rows = lambda: ["rows data"]
        self.assertEqual({"cols": ["Name", "Min", "Max", "Max rounded by 2"],
                          "rows": ["rows data"],
                          "styles": {0: "rich"}},
                         table.render())


def generate_iteration(duration, error, *actions):
    atomic_actions = [{"name": name,
                       "started_at": 0,
                       "finished_at": finished_at,
                       "children": []}
                      for name, finished_at in actions]
    if error:
        atomic_actions[-1]["failed"] = True
    return {
        "atomic_actions": atomic_actions,
        "duration": duration,
        "idle_duration": 0,
        "error": error
    }


@ddt.ddt
class MainStatsTableTestCase(test.TestCase):

    @ddt.data(
        {
            "info": {"total_iteration_count": 1},
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0), ("bar", 2.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, "100.0%", 1],
                ["bar", 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, "100.0%", 1],
                ["total", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "100.0%", 1],
                [" -> duration",
                 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "100.0%", 1],
                [" -> idle_duration",
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "100.0%", 1]],
            "expected_styles": {2: "rich", 3: "oblique", 4: "oblique"}
        },
        {
            "info": {"total_iteration_count": 2},
            "data": [
                generate_iteration(10.0, True, ("foo", 1.0)),
                generate_iteration(10.0, True, ("foo", 2.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 1.5, 1.9, 1.95, 2.0, 1.5, "0.0%", 2],
                ["total", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "0.0%", 2],
                [" -> duration",
                 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "0.0%", 2],
                [" -> idle_duration",
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "0.0%", 2]],
            "expected_styles": {1: "rich", 2: "oblique", 3: "oblique"}
        },
        {
            "info": {"total_iteration_count": 2},
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0)),
                generate_iteration(20.0, True, ("foo", 2.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 1.5, 1.9, 1.95, 2.0, 1.5, "50.0%", 2],
                ["total", 10.0, 15.0, 19.0, 19.5, 20.0, 15.0, "50.0%", 2],
                [" -> duration",
                 10.0, 15.0, 19.0, 19.5, 20.0, 15.0, "50.0%", 2],
                [" -> idle_duration",
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "50.0%", 2]],
            "expected_styles": {1: "rich", 2: "oblique", 3: "oblique"}
        },
        {
            "info": {"total_iteration_count": 4},
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0), ("bar", 4.0)),
                generate_iteration(20.0, False, ("foo", 2.0), ("bar", 4.0)),
                generate_iteration(30.0, False, ("foo", 3.0), ("bar", 4.0)),
                generate_iteration(40.0, True, ("foo", 4.0), ("bar", 4.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 2.5, 3.7, 3.85, 4.0, 2.5, "100.0%", 4],
                ["bar", 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, "75.0%", 4],
                ["total", 10.0, 25.0, 37.0, 38.5, 40.0, 25.0, "75.0%", 4],
                [" -> duration",
                 10.0, 25.0, 37.0, 38.5, 40.0, 25.0, "75.0%", 4],
                [" -> idle_duration",
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "75.0%", 4]],
            "expected_styles": {2: "rich", 3: "oblique", 4: "oblique"}
        },
        {
            "info": {"total_iteration_count": 0},
            "data": [],
            "expected_rows": [
                ["total", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 0]],
            "expected_styles": {0: "rich"}
        },
        {
            "info": {"total_iteration_count": 4},
            "data": [
                generate_iteration(1.6, True, ("foo", 1.2)),
                generate_iteration(5.2, False, ("foo", 1.2)),
                generate_iteration(5.0, True, ("bar", 4.8)),
                generate_iteration(12.3, False, ("foo", 4.2), ("bar", 5.6))
            ],
            "expected_rows": [
                ["foo", 1.2, 1.2, 3.6, 3.9, 4.2, 2.2, "66.7%", 3],
                ["bar", 4.8, 5.2, 5.52, 5.56, 5.6, 5.2, "50.0%", 2],
                ["total", 1.6, 5.1, 10.17, 11.235, 12.3, 6.025, "50.0%", 4],
                [" -> duration",
                 1.6, 5.1, 10.17, 11.235, 12.3, 6.025, "50.0%", 4],
                [" -> idle_duration",
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "50.0%", 4]],
            "expected_styles": {2: "rich", 3: "oblique", 4: "oblique"}
        },
        {
            "info": {"total_iteration_count": 4},
            "data": [
                {
                    "atomic_actions": [
                        {"name": "foo",
                         "started_at": 0,
                         "finished_at": 3.3,
                         "children": [
                             {"name": "bar",
                              "started_at": 0,
                              "finished_at": 1.3,
                              "children": []},
                             {"name": "bar",
                              "started_at": 0,
                              "finished_at": 3.3,
                              "children": []}]}
                    ],
                    "duration": 3.3,
                    "idle_duration": 17,
                    "error": False},
                {
                    "atomic_actions": [
                        {"name": "foo",
                         "started_at": 0,
                         "finished_at": 7.3,
                         "failed": True,
                         "children": [
                             {"name": "bar",
                              "started_at": 0,
                              "finished_at": 2.3,
                              "children": []},
                             {"name": "bar",
                              "failed": True,
                              "started_at": 0,
                              "finished_at": 7.3,
                              "children": []}]}
                    ],
                    "duration": 7.3,
                    "idle_duration": 20,
                    "error": True}
            ],
            "expected_rows": [
                ["foo", 3.3, 5.3, 6.9, 7.1, 7.3, 5.3, "50.0%", 2],
                [" -> bar (x2)", 4.6, 7.1, 9.1, 9.35, 9.6, 7.1, "50.0%", 2],
                ["total", 20.3, 23.8, 26.6, 26.95, 27.3, 23.8, "50.0%", 2],
                [" -> duration", 3.3, 5.3, 6.9, 7.1, 7.3, 5.3, "50.0%", 2],
                [" -> idle_duration",
                 17.0, 18.5, 19.7, 19.85, 20.0, 18.5, "50.0%", 2]],
            "expected_styles": {1: "oblique", 2: "rich",
                                3: "oblique", 4: "oblique"}
        },
        {
            "info": {"total_iteration_count": 1},
            "data": [
                {
                    "atomic_actions": [
                        {"name": "foo",
                         "started_at": 0,
                         "finished_at": 7.3,
                         "children": []}
                    ],
                    "duration": 7.3,
                    "idle_duration": 20,
                    "error": True}
            ],
            "expected_rows": [
                ["foo", 7.3, 7.3, 7.3, 7.3, 7.3, 7.3, "100.0%", 1],
                ["<no-name-action>", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "0.0%", 1],
                ["total", 27.3, 27.3, 27.3, 27.3, 27.3, 27.3, "0.0%", 1],
                [" -> duration", 7.3, 7.3, 7.3, 7.3, 7.3, 7.3, "0.0%", 1],
                [" -> idle_duration", 20.0, 20.0, 20.0, 20.0, 20.0, 20.0,
                 "0.0%", 1]],
            "expected_styles": {2: "rich", 3: "oblique", 4: "oblique"}
        }
    )
    @ddt.unpack
    def test_add_iteration_and_render(self, info, data, expected_rows,
                                      expected_styles):

        table = charts.MainStatsTable(info)
        for el in data:
            table.add_iteration(el)
        expected = {"cols": ["Action", "Min (sec)", "Median (sec)",
                             "90%ile (sec)", "95%ile (sec)", "Max (sec)",
                             "Avg (sec)", "Success", "Count"],
                    "rows": expected_rows,
                    "styles": expected_styles}
        self.assertEqual(expected, table.render())

    def test_to_dict(self):
        table = charts.MainStatsTable({"total_iteration_count": 4})
        data = [generate_iteration(1.6, True, ("foo", 1.2)),
                generate_iteration(5.2, False, ("foo", 1.2)),
                generate_iteration(5.0, True, ("bar", 4.8)),
                generate_iteration(12.3, False, ("foo", 4.2), ("bar", 5.6))]
        for el in data:
            table.add_iteration(el)

        self.assertEqual({
            "atomics": [{"children": [],
                         "data": {"90%ile": 3.6,
                                  "95%ile": 3.9,
                                  "avg": 2.2,
                                  "iteration_count": 3,
                                  "max": 4.2,
                                  "median": 1.2,
                                  "min": 1.2,
                                  "success": "66.7%"},
                         "display_name": "foo",
                         "count_per_iteration": 1,
                         "name": "foo"},
                        {"children": [],
                         "data": {"90%ile": 5.52,
                                  "95%ile": 5.56,
                                  "avg": 5.2,
                                  "iteration_count": 2,
                                  "max": 5.6,
                                  "median": 5.2,
                                  "min": 4.8,
                                  "success": "50.0%"},
                         "display_name": "bar",
                         "count_per_iteration": 1,
                         "name": "bar"}],
            "total": {"data": {"90%ile": 10.17,
                               "95%ile": 11.235,
                               "avg": 6.025,
                               "iteration_count": 4,
                               "max": 12.3,
                               "median": 5.1,
                               "min": 1.6,
                               "success": "50.0%"},
                      "display_name": "total",
                      "count_per_iteration": 1,
                      "name": "total",
                      "children": [
                          {"children": [],
                           "count_per_iteration": 1,
                           "data": {"90%ile": 10.17,
                                    "95%ile": 11.235,
                                    "avg": 6.025,
                                    "iteration_count": 4,
                                    "max": 12.3,
                                    "median": 5.1,
                                    "min": 1.6,
                                    "success": "50.0%"},
                           "display_name": "duration",
                           "name": "duration"},
                          {"children": [],
                           "count_per_iteration": 1,
                           "data": {"90%ile": 0.0,
                                    "95%ile": 0.0,
                                    "avg": 0.0,
                                    "iteration_count": 4,
                                    "max": 0.0,
                                    "median": 0.0,
                                    "min": 0.0,
                                    "success": "50.0%"},
                           "display_name": "idle_duration",
                           "name": "idle_duration"}]
                      }
        }, table.to_dict())


class OutputChartTestCase(test.TestCase):

    class OutputChart(charts.OutputChart):
        widget = "FooWidget"

    def test___init__(self):
        self.assertRaises(TypeError,
                          charts.OutputChart, {"total_iteration_count": 42})

        chart = self.OutputChart({"total_iteration_count": 42})
        self.assertIsInstance(chart, charts.Chart)

    def test__map_iteration_values(self):
        chart = self.OutputChart({"total_iteration_count": 42})
        self.assertEqual("foo data", chart._map_iteration_values("foo data"))

    def test_render(self):
        chart = self.OutputChart({"total_iteration_count": 42})
        self.assertEqual(
            {"widget": "FooWidget", "data": [],
             "title": "", "description": "", "label": "", "axis_label": ""},
            chart.render())

        chart = self.OutputChart({"total_iteration_count": 42},
                                 title="foo title", description="Test!",
                                 label="Foo label", axis_label="Axis label")
        self.assertEqual(
            {"widget": "FooWidget", "data": [], "label": "Foo label",
             "axis_label": "Axis label", "title": "foo title",
             "description": "Test!"},
            chart.render())


class OutputStackedAreaChartTestCase(test.TestCase):

    def test___init__(self):
        self.assertEqual("StackedArea", charts.OutputStackedAreaChart.widget)

        chart = charts.OutputStackedAreaChart({"total_iteration_count": 42})
        self.assertIsInstance(chart, charts.OutputChart)

    def test_render(self):
        # Explicit label
        chart = charts.OutputStackedAreaChart(
            {"total_iteration_count": 2}, label="Label",
            axis_label="Axis label")
        chart.add_iteration((("foo", 10), ("bar", 20)))
        # One iteration is transformed to Table
        self.assertEqual({"axis_label": "Axis label",
                          "data": {"cols": ["Name", "Label"],
                                   "rows": [["foo", 10], ["bar", 20]]},
                          "description": "", "label": "Label",
                          "title": "", "widget": "Table"},
                         chart.render())
        chart.add_iteration((("foo", 11), ("bar", 21)))
        # StackedArea for more iterations
        self.assertEqual({"axis_label": "Axis label",
                          "data": [("foo", [[1, 10], [2, 11]]),
                                   ("bar", [[1, 20], [2, 21]])],
                          "description": "", "label": "Label",
                          "title": "", "widget": "StackedArea"},
                         chart.render())

        # No label
        chart = charts.OutputStackedAreaChart({"total_iteration_count": 1})
        chart.add_iteration((("foo", 10), ("bar", 20)))
        self.assertEqual({"axis_label": "",
                          "data": {"cols": ["Name", "Value"],
                                   "rows": [["foo", 10], ["bar", 20]]},
                          "description": "", "label": "", "title": "",
                          "widget": "Table"}, chart.render())


class OutputAvgChartTestCase(test.TestCase):

    def test___init__(self):
        self.assertEqual("Pie", charts.OutputAvgChart.widget)

        chart = charts.OutputAvgChart({"total_iteration_count": 42})
        self.assertIsInstance(chart, charts.OutputChart)
        self.assertIsInstance(chart, charts.AvgChart)


class OutputTableTestCase(test.TestCase):

    class OutputTable(charts.OutputTable):

        columns = []

        def add_iteration(self, iteration):
            pass

    def test___init__(self):
        self.assertEqual("Table", charts.OutputTable.widget)
        self.assertRaises(TypeError,
                          charts.OutputTable, {"total_iteration_count": 42})
        self.OutputTable({"total_iteration_count": 42})


@ddt.ddt
class OutputStatsTableTestCase(test.TestCase):

    def test___init__(self):
        self.assertEqual("Table", charts.OutputStatsTable.widget)
        self.assertEqual(
            ["Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
             "95%ile (sec)", "Max (sec)", "Avg (sec)", "Count"],
            charts.OutputStatsTable.columns)

        table = charts.OutputStatsTable({"total_iteration_count": 42})
        self.assertIsInstance(table, charts.Table)

    @ddt.data(
        {"title": "Foo title",
         "description": "",
         "iterations": [],
         "expected": []},
        {"title": "Foo title",
         "description": "Test description!",
         "iterations": [[("a", 11), ("b", 22)], [("a", 5.6), ("b", 7.8)],
                        [("a", 42), ("b", 24)]],
         "expected": [["a", 5.6, 11.0, 35.8, 38.9, 42.0, 19.533, 3],
                      ["b", 7.8, 22.0, 23.6, 23.8, 24.0, 17.933, 3]]})
    @ddt.unpack
    def test_add_iteration_and_render(self, title, description, iterations,
                                      expected):
        table = charts.OutputStatsTable(
            {"total_iteration_count": len(iterations)},
            title=title, description=description)
        for iteration in iterations:
            table.add_iteration(iteration)
        styles = {1: "rich"} if iterations else {}
        self.assertEqual({"title": title,
                          "description": description,
                          "widget": "Table",
                          "data": {"cols": charts.OutputStatsTable.columns,
                                   "rows": expected,
                                   "styles": styles},
                          "label": "",
                          "axis_label": ""},
                         table.render())


class OutputTextAreaTestCase(test.TestCase):

    def test_class(self):
        self.assertTrue(issubclass(charts.OutputTextArea, charts.OutputChart))
        self.assertEqual("TextArea", charts.OutputTextArea.widget)


class OutputEmbeddedChartTestCase(test.TestCase):

    def test_render_complete_data(self):
        title = "title"
        custom_page = (
            "<html>"
            "<head><script>Something</script></head>"
            "<body>Hello world!</body>"
            "</html>"
        )

        pdata = {"data": custom_page, "title": title}

        chart_data = charts.OutputEmbeddedChart.render_complete_data(pdata)
        self.assertEqual(
            {
                "title": title,
                "widget": "EmbedChart",
                "data": {
                    "source": None,
                    "embedded": custom_page.replace("/script>", "\\/script>")
                }
            },
            chart_data)


class OutputEmbeddedExternalChartTestCase(test.TestCase):

    def test_render_complete_data(self):
        title = "title"
        custom_page = "https://example.com"

        pdata = {"data": custom_page, "title": title}

        cdata = charts.OutputEmbeddedExternalChart.render_complete_data(pdata)
        self.assertEqual(
            {
                "title": title,
                "widget": "EmbedChart",
                "data": {"source": custom_page, "embedded": None}
            },
            cdata)


@ddt.ddt
class ModuleTestCase(test.TestCase):

    @ddt.data({"args": ["unexpected_foo", {}],
               "expected": ("unexpected output type: 'unexpected_foo', "
                            "should be in ('additive', 'complete')")},
              {"args": ["additive", 42],
               "expected": ("additive output item has wrong type 'int', "
                            "must be 'dict'")},
              {"args": ["additive", {}],
               "expected": "additive output missing key 'title'"},
              {"args": ["additive", collections.OrderedDict(
                  [("title", "foo")])],
               "expected": "additive output missing key 'chart_plugin'"},
              {"args": ["additive", {"title": "a", "chart_plugin": "b"}],
               "expected": "additive output missing key 'data'"},
              {"args": ["additive", {"title": "a", "chart_plugin": "b",
                                     "data": "c"}],
               "expected": ("Value of additive output data has wrong type "
                            "'str', should be in ('list', 'dict')")},
              {"args": ["additive", {"title": "a", "chart_plugin": "b",
                                     "data": []}]},
              {"args": ["additive", {"title": "a", "chart_plugin": "b",
                                     "data": [], "unexpected_foo": 42}],
               "expected": ("additive output has unexpected key "
                            "'unexpected_foo'")},
              {"args": ["complete", {}],
               "expected": "complete output missing key 'title'"},
              {"args": ["complete", {"title": "foo"}],
               "expected": "complete output missing key 'chart_plugin'"},
              {"args": ["complete", {"title": "a", "chart_plugin": "b"}],
               "expected": "complete output missing key 'data'"},
              {"args": ["complete", {"title": "a", "chart_plugin": "b",
                                     "data": "c"}],
               "expected": ("Value of complete output data has wrong type "
                            "'str', should be in ('list', 'dict')")},
              {"args": ["complete", {"title": "a", "chart_plugin": "b",
                                     "data": {"foo": "bar"}}]},
              {"args": ["complete", {"title": "a", "chart_plugin": "b",
                                     "data": [], "unexpected": "bar"}],
               "expected": ("complete output has unexpected key "
                            "'unexpected'")})
    @ddt.unpack
    def test_validate_output(self, args, expected=None):
        self.assertEqual(expected, charts.validate_output(*args))
