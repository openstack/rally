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

import ddt
import mock

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
        return {"iterations_count": 42, "atomic": {"a": {}, "b": {}, "c": {}}}

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

    def test__fix_atomic_actions(self):
        chart = self.Chart(self.wload_info)
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
        [chart.add_iteration({"atomic_actions": collections.OrderedDict(a)})
         for a in ([("foo", 2), ("bar", 5)], [("foo", 4)], [("bar", 7)])]
        self.assertEqual([("bar", 4.0), ("foo", 2.0)], sorted(chart.render()))


@ddt.ddt
class LoadProfileChartTestCase(test.TestCase):

    @ddt.data(
        {"info": {"iterations_count": 9,
                  "tstamp_start": 0.0,
                  "load_duration": 8.0},
         "iterations": [(0.0, 0.5), (0.5, 0.5), (2.0, 4.0), (2.0, 2.0),
                        (4.0, 2.0), (6.0, 0.5), (6.5, 0.5), (7.5, 0.5),
                        (7.5, 1.5)],
         "kwargs": {"scale": 8},
         "expected": [("parallel iterations",
                       [(0.0, 0), (1.25, 0.8), (2.5, 0.8), (3.75, 2),
                        (5.0, 2.0), (6.25, 1.8), (7.5, 0.6000000000000001),
                        (8.75, 1.4), (10.0, 0.2)])]},
        {"info": {"iterations_count": 6,
                  "tstamp_start": 0.0,
                  "load_duration": 12.0},
         "iterations": [(0.0, 0.75), (0.75, 0.75), (1.5, 0.375), (3.0, 5.0),
                        (3.75, 4.25), (10.0, 1.0)],
         "kwargs": {"name": "Custom name", "scale": 8},
         "expected": [("Custom name",
                       [(0.0, 0), (1.875, 1.0), (3.75, 0.4),
                        (5.625, 2.0), (7.5, 2), (9.375, 0.5333333333333333),
                        (11.25, 0.5333333333333333), (13.125, 0),
                        (15.0, 0)])]},
        {"info": {"iterations_count": 2,
                  "tstamp_start": 0.0,
                  "load_duration": 1.0},
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
        self.assertRaises(TypeError, charts.HistogramChart,
                          {"iterations_count": 3})
        chart = self.HistogramChart({"iterations_count": 3})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration({"foo": x}) for x in ({"bar": 1.2}, {"bar": 2.4},
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
            {"iterations_count": 3,
             "atomic": collections.OrderedDict(
                 [("foo", {"min_duration": 1.6, "max_duration": 2.8}),
                  ("bar", {"min_duration": 3.1, "max_duration": 5.5})])})
        self.assertIsInstance(chart, charts.HistogramChart)
        [chart.add_iteration({"atomic_actions": a})
         for a in ({"foo": 1.6, "bar": 3.1}, {"foo": 2.8}, {"bar": 5.5})]
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
        self.assertRaises(TypeError, charts.Table, {"iterations_count": 42})

    def test__round(self):
        table = self.Table({"iterations_count": 4})
        streaming_ins = mock.Mock()
        streaming_ins.result.return_value = 42.424242
        self.assertRaises(TypeError, table._round, streaming_ins)
        self.assertEqual("n/a", table._round(streaming_ins, False))
        self.assertEqual(round(42.424242, 3),
                         table._round(streaming_ins, True))

    def test__row_has_results(self):
        table = self.Table({"iterations_count": 1})
        for st_cls in (charts.streaming.MinComputation,
                       charts.streaming.MaxComputation,
                       charts.streaming.MeanComputation):
            st = st_cls()
            self.assertFalse(table._row_has_results([(st, None)]))
            st.add(0)
            self.assertTrue(table._row_has_results([(st, None)]))

    def test__row_has_results_and_get_rows(self):
        table = self.Table({"iterations_count": 3})
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
        table = self.Table({"iterations_count": 42})
        table.get_rows = lambda: "rows data"
        self.assertEqual({"cols": ["Name", "Min", "Max", "Max rounded by 2"],
                          "rows": "rows data"},
                         table.render())


def generate_iteration(duration, error, *actions):
    return {
        "atomic_actions": collections.OrderedDict(actions),
        "duration": duration,
        "error": error
    }


@ddt.ddt
class MainStatsTableTestCase(test.TestCase):

    @ddt.data(
        {
            "info": {
                "iterations_count": 1,
                "atomic": collections.OrderedDict([("foo", {}), ("bar", {})])
            },
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0), ("bar", 2.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, "100.0%", 1],
                ["bar", 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, "100.0%", 1],
                ["total", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "100.0%", 1]]
        },
        {
            "info": {"iterations_count": 2, "atomic": {"foo": {}}},
            "data": [
                generate_iteration(10.0, True, ("foo", 1.0)),
                generate_iteration(10.0, True, ("foo", 2.0))
            ],
            "expected_rows": [
                ["foo", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 2],
                ["total", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 2]]
        },
        {
            "info": {"iterations_count": 2, "atomic": {"foo": {}}},
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0)),
                generate_iteration(20.0, True, ("foo", 2.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, "50.0%", 2],
                ["total", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, "50.0%", 2]]
        },
        {
            "info": {
                "iterations_count": 4,
                "atomic": collections.OrderedDict([("foo", {}), ("bar", {})])
            },
            "data": [
                generate_iteration(10.0, False, ("foo", 1.0), ("bar", 4.0)),
                generate_iteration(20.0, False, ("foo", 2.0), ("bar", 4.0)),
                generate_iteration(30.0, False, ("foo", 3.0), ("bar", 4.0)),
                generate_iteration(40.0, True, ("foo", 4.0), ("bar", 4.0))
            ],
            "expected_rows": [
                ["foo", 1.0, 2.0, 2.8, 2.9, 3.0, 2.0, "75.0%", 4],
                ["bar", 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, "75.0%", 4],
                ["total", 10.0, 20.0, 28.0, 29.0, 30.0, 20.0, "75.0%", 4]]
        },
        {
            "info": {
                "iterations_count": 0,
                "atomic": collections.OrderedDict()
            },
            "data": [],
            "expected_rows": [
                ["total", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", 0]]
        },
        {
            "info": {"iterations_count": 4,
                     "atomic": collections.OrderedDict([("foo", {}),
                                                        ("bar", {})])},
            "data": [
                generate_iteration(1.6, True, ("foo", 1.2)),
                generate_iteration(5.2, False, ("foo", 1.2)),
                generate_iteration(5.0, True, ("bar", 4.8)),
                generate_iteration(12.3, False, ("foo", 4.2), ("bar", 5.6))
            ],
            "expected_rows": [
                ["foo", 1.2, 2.7, 3.9, 4.05, 4.2, 2.7, "66.7%", 3],
                ["bar", 5.6, 5.6, 5.6, 5.6, 5.6, 5.6, "50.0%", 2],
                ["total", 5.2, 8.75, 11.59, 11.945, 12.3, 8.75, "50.0%", 4]]
        }
    )
    @ddt.unpack
    def test_add_iteration_and_render(self, info, data, expected_rows):

        table = charts.MainStatsTable(info)
        for el in data:
            table.add_iteration(el)
        expected = {"cols": ["Action", "Min (sec)", "Median (sec)",
                             "90%ile (sec)", "95%ile (sec)", "Max (sec)",
                             "Avg (sec)", "Success", "Count"],
                    "rows": expected_rows}
        self.assertEqual(expected, table.render())


class OutputChartTestCase(test.TestCase):

    class OutputChart(charts.OutputChart):
        widget = "FooWidget"

    def test___init__(self):
        self.assertRaises(TypeError,
                          charts.OutputChart, {"iterations_count": 42})

        chart = self.OutputChart({"iterations_count": 42})
        self.assertIsInstance(chart, charts.Chart)

    def test__map_iteration_values(self):
        chart = self.OutputChart({"iterations_count": 42})
        self.assertEqual("foo data", chart._map_iteration_values("foo data"))

    def test_render(self):
        chart = self.OutputChart({"iterations_count": 42})
        self.assertEqual(
            {"widget": "FooWidget", "data": [],
             "title": "", "description": "", "label": "", "axis_label": ""},
            chart.render())

        chart = self.OutputChart({"iterations_count": 42},
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

        chart = charts.OutputStackedAreaChart({"iterations_count": 42})
        self.assertIsInstance(chart, charts.OutputChart)

    def test_render(self):
        # Explicit label
        chart = charts.OutputStackedAreaChart(
            {"iterations_count": 2}, label="Label", axis_label="Axis label")
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
        chart = charts.OutputStackedAreaChart({"iterations_count": 1})
        chart.add_iteration((("foo", 10), ("bar", 20)))
        self.assertEqual({"axis_label": "",
                          "data": {"cols": ["Name", "Value"],
                                   "rows": [["foo", 10], ["bar", 20]]},
                          "description": "", "label": "", "title": "",
                          "widget": "Table"}, chart.render())


class OutputAvgChartTestCase(test.TestCase):

    def test___init__(self):
        self.assertEqual("Pie", charts.OutputAvgChart.widget)

        chart = charts.OutputAvgChart({"iterations_count": 42})
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
                          charts.OutputTable, {"iterations_count": 42})
        self.OutputTable({"iterations_count": 42})


@ddt.ddt
class OutputStatsTableTestCase(test.TestCase):

    def test___init__(self):
        self.assertEqual("Table", charts.OutputStatsTable.widget)
        self.assertEqual(
            ["Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
             "95%ile (sec)", "Max (sec)", "Avg (sec)", "Count"],
            charts.OutputStatsTable.columns)

        table = charts.OutputStatsTable({"iterations_count": 42})
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
         "expected": [["a", 5.6, 11.0, 35.8, 38.9, 42.0, 10.267, 3],
                      ["b", 7.8, 22.0, 23.6, 23.8, 24.0, 9.467, 3]]})
    @ddt.unpack
    def test_add_iteration_and_render(self, title, description, iterations,
                                      expected):
        table = charts.OutputStatsTable({"iterations_count": len(iterations)},
                                        title=title, description=description)
        for iteration in iterations:
            table.add_iteration(iteration)
        self.assertEqual({"title": title,
                          "description": description,
                          "widget": "Table",
                          "data": {"cols": charts.OutputStatsTable.columns,
                                   "rows": expected},
                          "label": "",
                          "axis_label": ""},
                         table.render())


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
              {"args": ["additive", {"title": "foo"}],
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
