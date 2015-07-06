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


class StackedAreaChartTestCase(test.TestCase):

    class StackedAreaChart(charts.StackedAreaChart):
        def _map_iteration_values(self, iteration):
            return iteration["foo"].items()

    def test_add_iteration_and_render(self):
        self.assertRaises(TypeError, charts.StackedAreaChart,
                          {"iterations_count": 42})
        chart = self.StackedAreaChart({"iterations_count": 42})
        self.assertIsInstance(chart, charts.Chart)
        [chart.add_iteration({"foo": x}) for x in ({"a": 1.3, "b": 4.3},
                                                   {"a": 2.4, "b": 5.4},
                                                   {"a": 3.5, "b": 7.7})]
        self.assertEqual([{"key": "a",
                           "values": [[1, 1.3], [2, 2.4], [3, 3.5]]},
                          {"key": "b",
                           "values": [[1, 4.3], [2, 5.4], [3, 7.7]]}],
                         sorted(chart.render(), key=lambda x: x["key"]))


class MainStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.MainStackedAreaChart({"iterations_count": 3}, 10)
        self.assertIsInstance(chart, charts.StackedAreaChart)
        [chart.add_iteration(itr) for itr in (
            {"duration": 1.1, "idle_duration": 2.2, "error": None},
            {"error": True, "duration": 1.1, "idle_duration": 0.5},
            {"duration": 1.3, "idle_duration": 3.4, "error": None})]
        expected = [
            {"key": "duration", "values": [[1, 1.1], [2, 0], [3, 1.3]]},
            {"key": "idle_duration", "values": [[1, 2.2], [2, 0], [3, 3.4]]},
            {"key": "failed_duration", "values": [[1, 0], [2, 1.6], [3, 0]]}]
        self.assertEqual(expected, chart.render())


class AtomicStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        iterations = (
            {"atomic_actions": {"foo": 1.1}, "error": False},
            {"atomic_actions": {"foo": 1.1, "bar": 1.2},
             "error": True, "duration": 40, "idle_duration": 2},
            {"atomic_actions": {"bar": 1.2},
             "error": True, "duration": 5.5, "idle_duration": 2.5})
        expected = [
            {"key": "bar", "values": [[1, 0], [2, 1.2], [3, 1.2]]},
            {"key": "failed_duration", "values": [[1, 0], [2, 39.7],
                                                  [3, 6.8]]},
            {"key": "foo", "values": [[1, 1.1], [2, 1.1], [3, 0]]}]
        chart = charts.AtomicStackedAreaChart(
            {"iterations_count": 3, "atomic": {"foo": {}, "bar": {}}}, 10)
        self.assertIsInstance(chart, charts.StackedAreaChart)
        [chart.add_iteration(iteration) for iteration in iterations]
        self.assertEqual(expected,
                         sorted(chart.render(), key=lambda x: x["key"]))


class OutputStackedAreaChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.OutputStackedAreaChart(
            {"iterations_count": 3, "output_names": ["foo", "bar"]}, 10)
        self.assertIsInstance(chart, charts.StackedAreaChart)
        [chart.add_iteration({"scenario_output": {"data": x}})
         for x in ({"foo": 1.1, "bar": 1.2}, {"foo": 1.3}, {"bar": 1.4})]
        expected = [{"key": "bar", "values": [[1, 1.2], [2, 0], [3, 1.4]]},
                    {"key": "foo", "values": [[1, 1.1], [2, 1.3], [3, 0]]}]
        self.assertEqual(expected,
                         sorted(chart.render(), key=lambda x: x["key"]))


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
        self.assertEqual([{"key": "a", "values": 2.4},
                          {"key": "b", "values": 5.8}],
                         sorted(chart.render(), key=lambda x: x["key"]))


class AtomicAvgChartTestCase(test.TestCase):

    def test_add_iteration_and_render(self):
        chart = charts.AtomicAvgChart({"iterations_count": 3,
                                       "atomic": {"foo": {}, "bar": {}}})
        self.assertIsInstance(chart, charts.AvgChart)
        [chart.add_iteration({"atomic_actions": costilius.OrderedDict(a)})
         for a in ([("foo", 2), ("bar", 5)], [("foo", 4)], [("bar", 7)])]
        self.assertEqual([{"key": "bar", "values": 4.0},
                          {"key": "foo", "values": 2.0}],
                         sorted(chart.render(), key=lambda x: x["key"]))


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


class TableTestCase(test.TestCase):

    class Table(charts.Table):
        columns = ["name", "foo", "bar"]
        foo = mock.Mock()
        bar = mock.Mock()

        def _init_columns(self):
            return costilius.OrderedDict(
                [("foo", self.foo), ("bar", self.bar)])

        def _map_iteration_values(self, iteration):
            return [("value_" + k, iteration[k]) for k in ["a", "b"]]

        def render(self):
            return self._data

    def setUp(self, *args, **kwargs):
        super(TableTestCase, self).setUp(*args, **kwargs)
        self.bench_info = {"iterations_count": 42,
                           "atomic": {"a": {}, "b": {}, "c": {}}}

    def test_add_iteration_and_render(self):
        self.assertRaises(TypeError, charts.Table, self.bench_info)
        table = self.Table(self.bench_info)
        self.assertEqual(costilius.OrderedDict(), table.render())
        [table.add_iteration({"a": i, "b": 43 - i}) for i in range(1, 43)]
        self.assertEqual(
            costilius.OrderedDict(
                [("value_a", costilius.OrderedDict([("foo", table.foo),
                                                    ("bar", table.bar)])),
                 ("value_b", costilius.OrderedDict([("foo", table.foo),
                                                    ("bar", table.bar)]))]),
            table.render())


class MainStatsTableTestCase(test.TestCase):

    def setUp(self, *args, **kwargs):
        super(MainStatsTableTestCase, self).setUp(*args, **kwargs)
        self.bench_info = {"iterations_count": 42,
                           "atomic": {"a": {}, "b": {}, "c": {}}}
        self.columns = [
            "Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
            "95%ile (sec)", "Max (sec)", "Avg (sec)", "Success", "Count"]

    def test_add_iteration_and_render(self):
        table = charts.MainStatsTable({"iterations_count": 42,
                                       "atomic": {"foo": {}, "bar": {}}})
        [table.add_iteration(
            {"atomic_actions": costilius.OrderedDict([("foo", i),
                                                      ("bar", 43 - 1)]),
             "duration": i, "error": i % 40}) for i in range(1, 43)]
        expected_rows = [
            ["foo", 1.0, 21.5, 38.5, 40.5, 42.0, 21.5, "100.0%", 42.0],
            ["bar", 42.0, 42.0, 42.0, 42.0, 42.0, 42.0, "100.0%", 42.0],
            ["total", 0.0, 0.0, 0.0, 0.0, 40.0, 0.952, "100.0%", 42.0]]
        self.assertEqual({"cols": self.columns, "rows": expected_rows},
                         table.render())
