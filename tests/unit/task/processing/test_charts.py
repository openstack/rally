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

    workload_info = {"iterations_count": 20,
                     "tstamp_start": 1459421691.607279,
                     "load_duration": 2.5298428535461426}
    iterations = [(1459421691.607279, 0.5002949237823486),
                  (1459421691.60854, 0.5005340576171875),
                  (1459421691.612978, 0.5005340576171875),
                  (1459421691.615876, 0.500960111618042),
                  (1459421692.110288, 0.5002930164337158),
                  (1459421692.111956, 0.5004231929779053),
                  (1459421692.118393, 0.5004739761352539),
                  (1459421692.125796, 0.5002138614654541),
                  (1459421692.612263, 0.5001211166381836),
                  (1459421692.614128, 0.5009160041809082),
                  (1459421692.620582, 0.5005178451538086),
                  (1459421692.629205, 0.5005218982696533),
                  (1459421693.113873, 0.5005190372467041),
                  (1459421693.117251, 0.5005340576171875),
                  (1459421693.122341, 0.5060141086578369),
                  (1459421693.131172, 0.5005171298980713),
                  (1459421693.616505, 0.5005180835723877),
                  (1459421693.624986, 0.500521183013916),
                  (1459421693.629693, 0.5004010200500488),
                  (1459421693.636602, 0.5005199909210205)]

    @ddt.data(
        {"info": workload_info,
         "iterations": iterations,
         "kwargs": {},
         "expected": [("parallel iterations",
                       [(0.0, 0), (0.025804397106170652, 2.0),
                        (0.051608794212341304, 4), (0.07741319131851196, 4),
                        (0.10321758842468261, 4), (0.12902198553085326, 4),
                        (0.15482638263702392, 4), (0.18063077974319455, 4),
                        (0.20643517684936522, 4), (0.23223957395553588, 4),
                        (0.2580439710617065, 4), (0.2838483681678772, 4),
                        (0.30965276527404784, 4), (0.3354571623802185, 4),
                        (0.3612615594863891, 4), (0.38706595659255977, 4),
                        (0.41287035369873043, 4), (0.4386747508049011, 4),
                        (0.46447914791107175, 4), (0.49028354501724236, 4),
                        (0.516087942123413, 3.5), (0.5418923392295837, 3.5),
                        (0.5676967363357543, 4), (0.593501133441925, 4),
                        (0.6193055305480957, 4), (0.6451099276542663, 4),
                        (0.670914324760437, 4), (0.6967187218666075, 4),
                        (0.7225231189727782, 4), (0.7483275160789489, 4),
                        (0.7741319131851195, 4), (0.7999363102912902, 4),
                        (0.8257407073974609, 4), (0.8515451045036315, 4),
                        (0.8773495016098022, 4), (0.9031538987159728, 4),
                        (0.9289582958221435, 4), (0.9547626929283142, 4),
                        (0.9805670900344847, 4), (1.0063714871406555, 3.5),
                        (1.032175884246826, 3.5), (1.0579802813529968, 4),
                        (1.0837846784591674, 4), (1.109589075565338, 4),
                        (1.1353934726715087, 4), (1.1611978697776792, 4),
                        (1.18700226688385, 4), (1.2128066639900206, 4),
                        (1.2386110610961913, 4), (1.264415458202362, 4),
                        (1.2902198553085327, 4), (1.3160242524147032, 4),
                        (1.341828649520874, 4), (1.3676330466270445, 4),
                        (1.393437443733215, 4), (1.4192418408393859, 4),
                        (1.4450462379455564, 4), (1.4708506350517272, 4),
                        (1.4966550321578977, 4), (1.5224594292640685, 3.5),
                        (1.548263826370239, 3.5), (1.5740682234764098, 4),
                        (1.5998726205825804, 4), (1.6256770176887512, 4),
                        (1.6514814147949217, 4), (1.6772858119010923, 4),
                        (1.703090209007263, 4), (1.7288946061134336, 4),
                        (1.7546990032196044, 4), (1.780503400325775, 4),
                        (1.8063077974319457, 4), (1.8321121945381162, 4),
                        (1.857916591644287, 4), (1.8837209887504576, 4),
                        (1.9095253858566283, 4), (1.935329782962799, 4),
                        (1.9611341800689694, 4), (1.9869385771751402, 4),
                        (2.012742974281311, 3.5), (2.0385473713874815, 3.5),
                        (2.064351768493652, 4), (2.0901561655998226, 4),
                        (2.1159605627059936, 4), (2.141764959812164, 4),
                        (2.1675693569183347, 4), (2.1933737540245053, 4),
                        (2.219178151130676, 4), (2.244982548236847, 4),
                        (2.2707869453430174, 4), (2.296591342449188, 4),
                        (2.3223957395553585, 4), (2.3482001366615295, 4),
                        (2.3740045337677, 4), (2.3998089308738706, 4),
                        (2.425613327980041, 4), (2.451417725086212, 4),
                        (2.4772221221923827, 4), (2.5030265192985532, 4),
                        (2.528830916404724, 2.5), (2.5546353135108943, 0.5),
                        (2.5804397106170653, 0)])]},
        {"info": workload_info,
         "iterations": iterations,
         "kwargs": {"name": "Custom name", "scale": 8},
         "expected": [("Custom name",
                       [(0.0, 0),
                        (0.3952879458665848, 2.0),
                        (0.7905758917331696, 4.0),
                        (1.1858638375997543, 4.0),
                        (1.5811517834663391, 4.0),
                        (1.976439729332924, 4),
                        (2.3717276751995087, 4.0),
                        (2.7670156210660934, 2.0),
                        (3.1623035669326782, 0)])]},
        {"info": {"iterations_count": 2,
                  "tstamp_start": 1459421691.607279,
                  "load_duration": 2.5298428535461426},
         "iterations": [],
         "kwargs": {"scale": 8},
         "expected": [("parallel iterations",
                       [(0.0, 0),
                        (0.3952879458665848, 0),
                        (0.7905758917331696, 0),
                        (1.1858638375997543, 0),
                        (1.5811517834663391, 0),
                        (1.976439729332924, 0),
                        (2.3717276751995087, 0),
                        (2.7670156210660934, 0),
                        (3.1623035669326782, 0)])]})
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
