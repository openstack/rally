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

import ddt
import mock

from rally.common import costilius
from rally.task.processing import charts
from tests.unit import test

CHARTS = "rally.task.processing.charts."


class ChartTestCase(test.TestCase):

    class Chart(charts.Chart):
        def _map_iteration_values(self, iteration):
            return [("foo_" + k, iteration[k]) for k in ["a", "b"]]

    @property
    def bench_info(self):
        return {"iterations_count": 42, "atomic": {"a": {}, "b": {}, "c": {}}}

    def test___init__(self):
        self.assertRaises(TypeError, charts.Chart, self.bench_info)
        chart = self.Chart(self.bench_info)
        self.assertEqual({}, chart._data)
        self.assertEqual(42, chart.base_size)
        self.assertEqual(1000, chart.zipped_size)
        chart = self.Chart(self.bench_info, zipped_size=24)
        self.assertEqual({}, chart._data)
        self.assertEqual(42, chart.base_size)
        self.assertEqual(24, chart.zipped_size)

    @mock.patch(CHARTS + "utils.GraphZipper")
    def test_add_iteration_and_render(self, mock_graph_zipper):
        gzipper_a = mock.Mock(get_zipped_graph=lambda: "a_points")
        gzipper_b = mock.Mock(get_zipped_graph=lambda: "b_points")
        mock_graph_zipper.side_effect = [gzipper_a, gzipper_b]
        chart = self.Chart(self.bench_info, 24)
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

    def test__fix_atomic_actions(self):
        chart = self.Chart(self.bench_info)
        self.assertEqual(
            {"atomic_actions": {"a": 5, "b": 6, "c": 0}},
            chart._fix_atomic_actions({"atomic_actions": {"a": 5, "b": 6}}))


class MainStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.MainStackedAreaChart({"iterations_count": 3,
                                             "iterations_failed": 0}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(itr) for itr in (
            {"duration": 1.1, "idle_duration": 2.2, "error": []},
            {"error": [], "duration": 1.1, "idle_duration": 0.5},
            {"duration": 1.3, "idle_duration": 3.4, "error": []})]
        expected = [("duration", [[1, 1.1], [2, 1.1], [3, 1.3]]),
                    ("idle_duration", [[1, 2.2], [2, 0.5], [3, 3.4]])]
        self.assertEqual(expected, chart.render())

    def test_add_iteration_and_render_with_failed_iterations(self):
        chart = charts.MainStackedAreaChart({"iterations_count": 3,
                                             "iterations_failed": 2}, 10)
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
            {"atomic_actions": {"foo": 1.1}, "error": []},
            {"atomic_actions": {"foo": 1.1, "bar": 1.2},
             "error": [], "duration": 40, "idle_duration": 2},
            {"atomic_actions": {"bar": 1.2},
             "error": [], "duration": 5.5, "idle_duration": 2.5})
        expected = [("bar", [[1, 0], [2, 1.2], [3, 1.2]]),
                    ("foo", [[1, 1.1], [2, 1.1], [3, 0]])]
        chart = charts.AtomicStackedAreaChart(
            {"iterations_count": 3, "iterations_failed": 0,
             "atomic": {"foo": {}, "bar": {}}}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(iteration) for iteration in iterations]
        self.assertEqual(expected, sorted(chart.render()))

    def test_add_iteration_and_render_with_failed_iterations(self):
        iterations = (
            {"atomic_actions": {"foo": 1.1}, "error": []},
            {"atomic_actions": {"foo": 1.1, "bar": 1.2},
             "error": ["foo_err"], "duration": 40, "idle_duration": 2},
            {"atomic_actions": {"bar": 1.2},
             "error": ["foo_err"], "duration": 5.5, "idle_duration": 2.5})
        expected = [("bar", [[1, 0], [2, 1.2], [3, 1.2]]),
                    ("failed_duration", [[1, 0], [2, 39.7], [3, 6.8]]),
                    ("foo", [[1, 1.1], [2, 1.1], [3, 0]])]
        chart = charts.AtomicStackedAreaChart(
            {"iterations_count": 3, "iterations_failed": 2,
             "atomic": {"foo": {}, "bar": {}}}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration(iteration) for iteration in iterations]
        self.assertEqual(expected, sorted(chart.render()))


class OutputStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.OutputStackedAreaChart(
            {"iterations_count": 3, "output_names": ["foo", "bar"]}, 10)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration({"scenario_output": {"data": x}})
         for x in ({"foo": 1.1, "bar": 1.2}, {"foo": 1.3}, {"bar": 1.4})]
        expected = [("bar", [[1, 1.2], [2, 0], [3, 1.4]]),
                    ("foo", [[1, 1.1], [2, 1.3], [3, 0]])]
        self.assertEqual(expected, sorted(chart.render()))


class AvgChartTestCase(test.TestCase):

    class AvgChart(charts.AvgChart):
        def _map_iteration_values(self, iteration):
            return iteration["foo"].items()

    def test_add_iteration_and_render(self):
        self.assertRaises(TypeError, charts.AvgChart, {"iterations_count": 3})
        chart = self.AvgChart({"iterations_count": 3})
        self.assertIsInstance(chart, charts.AvgChart)
        [chart.add_iteration({"foo": x}) for x in ({"a": 1.3, "b": 4.3},
                                                   {"a": 2.4, "b": 5.4},
                                                   {"a": 3.5, "b": 7.7})]
        self.assertEqual([("a", 2.4), ("b", 5.8)], sorted(chart.render()))


class AtomicAvgChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.AtomicAvgChart({"iterations_count": 3,
                                       "atomic": {"foo": {}, "bar": {}}})
        self.assertIsInstance(chart, charts.AvgChart)
        [chart.add_iteration({"atomic_actions": costilius.OrderedDict(a)})
         for a in ([("foo", 2), ("bar", 5)], [("foo", 4)], [("bar", 7)])]
        self.assertEqual([("bar", 4.0), ("foo", 2.0)], sorted(chart.render()))


@ddt.ddt
class LoadProfileChartTestCase(test.TestCase):

    @ddt.data({"count": 5, "load_duration": 63, "tstamp_start": 12345,
               "kwargs": {"scale": 10}, "data": [
                   (12345, 4.2, False), (12347, 42, False), (12349, 10, True),
                   (12351, 5.5, False), (12353, 0.42, False)],
               "expected": [("parallel iterations", [
                   [6.0, 3], [12.0, 3], [18.0, 1], [24.0, 1], [30.0, 1],
                   [36.0, 1], [42.0, 1], [48.0, 1], [54.0, 0], [63, 0]])]},
              {"count": 5, "load_duration": 63, "tstamp_start": 12345,
               "kwargs": {"scale": 8, "name": "Custom text"}, "data": [
                   (12345, 4.2, False), (12347, 42, False), (12349, 10, True),
                   (12351, 5.5, False), (12353, 0.42, False)],
               "expected": [("Custom text", [
                   [8.0, 4], [16.0, 3], [24.0, 1], [32.0, 1], [40.0, 1],
                   [48.0, 1], [56.0, 0], [63, 0]])]},
              {"count": 0, "load_duration": 0, "tstamp_start": 12345,
               "kwargs": {"scale": 8}, "data": [],
               "expected": [("parallel iterations", [[0, 0]])]})
    @ddt.unpack
    def test_add_iteration_and_render(self, count, load_duration,
                                      tstamp_start, kwargs, data, expected):
        chart = charts.LoadProfileChart(
            {"iterations_count": count,
             "load_duration": load_duration, "tstamp_start": tstamp_start},
            **kwargs)
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration({"timestamp": t, "duration": d, "error": e})
         for t, d, e in data]
        self.assertEqual(expected, chart.render())


@ddt.ddt
class HistogramChartTestCase(test.TestCase):

    class HistogramChart(charts.HistogramChart):

        def __init__(self, benchmark_info):
            super(HistogramChartTestCase.HistogramChart,
                  self).__init__(benchmark_info)
            self._data["bar"] = {"views": self._init_views(1.2, 4.2),
                                 "disabled": None}

        def _map_iteration_values(self, iteration):
            return iteration["foo"].items()

    def test_add_iteration_and_render(self):
        self.assertRaises(TypeError, charts.HistogramChart,
                          {"iterations_count": 3})
        chart = self.HistogramChart({"iterations_count": 3})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration({"foo": x}) for x in ({"bar": 1.2}, {"bar": 2.4},
                                                   {"bar": 4.2})]
        expected = [[{"disabled": None, "key": "bar",
                      "values": [{"x": 2.7, "y": 2}, {"x": 4.2, "y": 1}],
                      "view": "Square Root Choice"},
                     {"disabled": None, "key": "bar",
                      "values": [{"x": 2.2, "y": 1}, {"x": 3.2, "y": 1},
                                 {"x": 4.2, "y": 1}],
                      "view": "Sturges Formula"},
                     {"disabled": None,
                      "key": "bar",
                      "values": [{"x": 2.2, "y": 1}, {"x": 3.2, "y": 1},
                                 {"x": 4.2, "y": 1}],
                      "view": "Rice Rule"},
                     {"disabled": None, "key": "bar",
                      "values": [{"x": 2.7, "y": 2}, {"x": 4.2, "y": 1}],
                      "view": "One Half"}]]
        self.assertEqual(expected, chart.render())

    @ddt.data(
        {"base_size": 2, "min_value": 1, "max_value": 4,
         "expected": [{"bins": 2, "view": "Square Root Choice",
                       "x": [2.5, 4.0], "y": [0, 0]},
                      {"bins": 2, "view": "Sturges Formula",
                       "x": [2.5, 4.0], "y": [0, 0]},
                      {"bins": 3, "view": "Rice Rule",
                       "x": [2.0, 3.0, 4.0], "y": [0, 0, 0]},
                      {"bins": 1, "view": "One Half", "x": [4.0], "y": [0]}]},
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
                    42.0], "y": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
             {"bins": 50, "view": "One Half",
              "x": [27.3, 27.6, 27.9, 28.2, 28.5, 28.8, 29.1, 29.4, 29.7,
                    30.0, 30.3, 30.6, 30.9, 31.2, 31.5, 31.8, 32.1, 32.4,
                    32.7, 33.0, 33.3, 33.6, 33.9, 34.2, 34.5, 34.8, 35.1,
                    35.4, 35.7, 36.0, 36.3, 36.6, 36.9, 37.2, 37.5, 37.8,
                    38.1, 38.4, 38.7, 39.0, 39.3, 39.6, 39.9, 40.2, 40.5,
                    40.8, 41.1, 41.4, 41.7, 42.0], "y": [0] * 50}]})
    @ddt.unpack
    def test_views(self, base_size=None, min_value=None, max_value=None,
                   expected=None):
        chart = self.HistogramChart({"iterations_count": base_size})
        self.assertEqual(expected, chart._init_views(min_value, max_value))


class MainHistogramChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.MainHistogramChart(
            {"iterations_count": 3, "min_duration": 2, "max_duration": 7})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration(itr) for itr in (
            {"duration": 1.1, "idle_duration": 2.2, "error": None},
            {"error": True},
            {"duration": 1.3, "idle_duration": 3.4, "error": None})]
        expected = [
            {"disabled": None, "key": "task", "view": "Square Root Choice",
             "values": [{"x": 4.5, "y": 3}, {"x": 7.0, "y": 0}]},
            {"disabled": None, "key": "task", "view": "Sturges Formula",
             "values": [{"x": 3.666666666666667, "y": 3},
                        {"x": 5.333333333333334, "y": 0},
                        {"x": 7.0, "y": 0}]},
            {"disabled": None, "key": "task", "view": "Rice Rule",
             "values": [{"x": 3.666666666666667, "y": 3},
                        {"x": 5.333333333333334, "y": 0},
                        {"x": 7.0, "y": 0}]},
            {"disabled": None, "key": "task", "view": "One Half",
             "values": [{"x": 4.5, "y": 3}, {"x": 7.0, "y": 0}]}]
        self.assertEqual([expected], chart.render())


class AtomicHistogramChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.AtomicHistogramChart(
            {"iterations_count": 3,
             "atomic": costilius.OrderedDict(
                 [("foo", {"min_duration": 1.6, "max_duration": 2.8}),
                  ("bar", {"min_duration": 3.1, "max_duration": 5.5})])})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration({"atomic_actions": a})
         for a in ({"foo": 1.6, "bar": 3.1}, {"foo": 2.8}, {"bar": 5.5})]
        expected = [
            [{"disabled": 0, "key": "foo", "view": "Square Root Choice",
              "values": [{"x": 2.2, "y": 2}, {"x": 2.8, "y": 1}]},
             {"disabled": 0, "key": "foo", "view": "Sturges Formula",
              "values": [{"x": 2.0, "y": 2}, {"x": 2.4, "y": 0},
                         {"x": 2.8, "y": 1}]},
             {"disabled": 0, "key": "foo", "view": "Rice Rule",
              "values": [{"x": 2.0, "y": 2}, {"x": 2.4, "y": 0},
                         {"x": 2.8, "y": 1}]},
             {"disabled": 0, "key": "foo", "view": "One Half",
              "values": [{"x": 2.2, "y": 2}, {"x": 2.8, "y": 1}]}],
            [{"disabled": 1, "key": "bar", "view": "Square Root Choice",
              "values": [{"x": 4.3, "y": 2}, {"x": 5.5, "y": 1}]},
             {"disabled": 1, "key": "bar", "view": "Sturges Formula",
              "values": [{"x": 3.9, "y": 2}, {"x": 4.7, "y": 0},
                         {"x": 5.5, "y": 1}]},
             {"disabled": 1, "key": "bar", "view": "Rice Rule",
              "values": [{"x": 3.9, "y": 2}, {"x": 4.7, "y": 0},
                         {"x": 5.5, "y": 1}]},
             {"disabled": 1, "key": "bar", "view": "One Half",
              "values": [{"x": 4.3, "y": 2}, {"x": 5.5, "y": 1}]}]]
        self.assertEqual(expected, chart.render())


MAIN_STATS_TABLE_COLUMNS = ["Action", "Min (sec)", "Median (sec)",
                            "90%ile (sec)", "95%ile (sec)", "Max (sec)",
                            "Avg (sec)", "Success", "Count"]


def generate_iteration(duration, error, *args):
    return {
        "atomic_actions": costilius.OrderedDict(args),
        "duration": duration,
        "error": error
    }


@ddt.ddt
class MainStatsTableTestCase(test.TestCase):

    @ddt.data(
        {
            "info": {
                "iterations_count": 1,
                "atomic": costilius.OrderedDict([("foo", {}), ("bar", {})])
            },
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0), ("bar", 2.0))
            ],
            "expected": {
                "cols": MAIN_STATS_TABLE_COLUMNS,
                "rows": [
                    ["foo", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, "100.0%", 1],
                    ["bar", 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, "100.0%", 1],
                    ["total", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "100.0%", 1],
                ]
            }
        },
        {
            "info": {"iterations_count": 2, "atomic": {"foo": {}}},
            "data": [
                generate_iteration(10.0, True, ("foo", 1.0)),
                generate_iteration(10.0, True, ("foo", 2.0))
            ],
            "expected": {
                "cols": MAIN_STATS_TABLE_COLUMNS,
                "rows": [
                    ["foo", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "0.0%",
                     2],
                    ["total", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "0.0%",
                     2],
                ]
            }
        },
        {
            "info": {"iterations_count": 2, "atomic": {"foo": {}}},
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0)),
                generate_iteration(20.0, True, ("foo", 2.0))
            ],
            "expected": {
                "cols": MAIN_STATS_TABLE_COLUMNS,
                "rows": [
                    ["foo", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, "50.0%", 2],
                    ["total", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "50.0%", 2]
                ]
            }
        },
        {
            "info": {
                "iterations_count": 4,
                "atomic": costilius.OrderedDict([("foo", {}), ("bar", {})])
            },
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0), ("bar", 4.0)),
                generate_iteration(20.0, False, ("foo", 2.0), ("bar", 4.0)),
                generate_iteration(30.0, False, ("foo", 3.0), ("bar", 4.0)),
                generate_iteration(40.0, True, ("foo", 4.0), ("bar", 4.0))
            ],
            "expected": {
                "cols": MAIN_STATS_TABLE_COLUMNS,
                "rows": [
                    ["foo", 1.0, 2.0, 2.8, 2.9, 3.0, 2.0, "75.0%", 4],
                    ["bar", 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, "75.0%", 4],
                    ["total", 10.0, 20.0, 28.0, 29.0, 30.0, 20.0, "75.0%", 4]
                ]
            }
        }
    )
    @ddt.unpack
    def test_add_iteration_and_render(self, info, data, expected):

        table = charts.MainStatsTable(info)
        for el in data:
            table.add_iteration(el)

        self.assertEqual(expected, table.render())
