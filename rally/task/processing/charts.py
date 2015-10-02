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

import abc
import bisect
import copy
import math

import six

from rally.common import costilius
from rally.common import streaming_algorithms as streaming
from rally.task.processing import utils


@six.add_metaclass(abc.ABCMeta)
class Chart(object):
    """Base class for charts."""

    def __init__(self, benchmark_info, zipped_size=1000):
        """Setup initial values.

        :param benchmark_info: dict, generalized info about iterations.
                               The most important value is `iterations_count'
                               that should have int value of total data size
        :param zipped_size: int maximum number of points on scale
        """
        self._data = costilius.OrderedDict()  # Container for results
        self._benchmark_info = benchmark_info
        self.base_size = benchmark_info.get("iterations_count", 0)
        self.zipped_size = zipped_size

    def add_iteration(self, iteration):
        """Add iteration data.

        This method must be called for each iteration.
        If overriden, this method must use streaming data processing,
        so chart instance could process unlimited number of iterations,
        with low memory usage.
        """
        for name, value in self._map_iteration_values(iteration):
            if name not in self._data:
                self._data[name] = utils.GraphZipper(self.base_size,
                                                     self.zipped_size)
            self._data[name].add_point(value)

    def render(self):
        """Generate chart data ready for drawing."""
        return [(name, points.get_zipped_graph())
                for name, points in self._data.items()]

    def _fix_atomic_actions(self, iteration):
        """Set `0' for missed atomic actions.

        Since some atomic actions can absent in some iterations
        due to failures, this method must be used in all cases
        related to atomic actions processing.
        """
        for name in self._benchmark_info["atomic"]:
            iteration["atomic_actions"].setdefault(name, 0)
        return iteration

    @abc.abstractmethod
    def _map_iteration_values(self, iteration):
        """Get values for processing, from given iteration."""


class MainStackedAreaChart(Chart):

    def _map_iteration_values(self, iteration):
        if iteration["error"]:
            result = [("duration", 0), ("idle_duration", 0)]
            if self._benchmark_info["iterations_failed"]:
                result.append(
                    ("failed_duration",
                     iteration["duration"] + iteration["idle_duration"]))
        else:
            result = [("duration", iteration["duration"]),
                      ("idle_duration", iteration["idle_duration"])]
            if self._benchmark_info["iterations_failed"]:
                result.append(("failed_duration", 0))
        return result


class AtomicStackedAreaChart(Chart):

    def _map_iteration_values(self, iteration):
        iteration = self._fix_atomic_actions(iteration)
        atomics = list(iteration["atomic_actions"].items())
        if self._benchmark_info["iterations_failed"]:
            if iteration["error"]:
                failed_duration = (
                    iteration["duration"] + iteration["idle_duration"]
                    - sum([(a[1] or 0) for a in atomics]))
            else:
                failed_duration = 0
            atomics.append(("failed_duration", failed_duration))
        return atomics


class OutputStackedAreaChart(Chart):

    def _map_iteration_values(self, iteration):
        return [(name, iteration["scenario_output"]["data"].get(name, 0))
                for name in self._benchmark_info["output_names"]]


class AvgChart(Chart):
    """Base class for charts with average results."""

    def add_iteration(self, iteration):
        for name, value in self._map_iteration_values(iteration):
            if name not in self._data:
                self._data[name] = streaming.MeanComputation()
            self._data[name].add(value or 0)

    def render(self):
        return [(k, v.result()) for k, v in self._data.items()]


class AtomicAvgChart(AvgChart):

    def _map_iteration_values(self, iteration):
        iteration = self._fix_atomic_actions(iteration)
        return list(iteration["atomic_actions"].items())


class LoadProfileChart(Chart):
    """Chart for parallel durations."""

    def __init__(self, benchmark_info, name="parallel iterations",
                 scale=200):
        """Setup chart with graph name and scale.

        :benchmark_info:  dict, generalized info about iterations
        :param name: str name for X axis
        :param scale: int number of X points
        """
        super(LoadProfileChart, self).__init__(benchmark_info)
        self._name = name
        self._duration = benchmark_info["load_duration"]
        self._tstamp_start = benchmark_info["tstamp_start"]

        # NOTE(amaretskiy): Determine a chart `step' - duration between
        #   two X points, rounded with minimal accuracy (digits after point)
        #   to improve JavaScript drawing performance.
        # Examples:
        #   scale  duration       step (initial)    accuracy  step
        #   200    30.8043010235  0.154021505117    1         0.2
        #   200    1.25884699821  0.00629423499107  3         0.006
        step = self._duration / float(scale)
        if step == 0:
            accuracy = 0
        else:
            accuracy = max(-int(math.floor(math.log10(step))), 0)
        step = round(step, accuracy)
        self._time_axis = [step * x
                           for x in six.moves.range(1, int(scale))
                           if (step * x) < self._duration]
        self._time_axis.append(self._duration)
        self._started = [0] * len(self._time_axis)
        self._stopped = [0] * len(self._time_axis)

    def _map_iteration_values(self, iteration):
        return (iteration["timestamp"],
                0 if iteration["error"] else iteration["duration"])

    def add_iteration(self, iteration):
        timestamp, duration = self._map_iteration_values(iteration)
        ts_start = timestamp - self._tstamp_start
        ts_stop = ts_start + duration
        self._started[bisect.bisect(self._time_axis, ts_start)] += 1
        self._stopped[bisect.bisect(self._time_axis, ts_stop)] += 1

    def render(self):
        data = []
        running = 0
        for ts, started, ended in zip(self._time_axis,
                                      self._started, self._stopped):
            running += started
            data.append([ts, running])
            running -= ended
        return [(self._name, data)]


class HistogramChart(Chart):
    """Base class for chart with histograms.

    This chart is relatively complex, because actually it is a set
    of histograms, that usually can be switched by dropdown select.
    And each histogram has several data views.
    """

    def _init_views(self, min_value, max_value):
        """Generate initial data for each histogram view."""
        if not self.base_size:
            return []
        min_value, max_value = min_value or 0, max_value or 0
        views = []
        for view, bins in [
                ("Square Root Choice",
                 int(math.ceil(math.sqrt(self.base_size)))),
                ("Sturges Formula",
                 int(math.ceil(math.log(self.base_size, 2) + 1))),
                ("Rice Rule",
                 int(math.ceil(2 * self.base_size ** (1.0 / 3)))),
                ("One Half",
                 int(math.ceil(self.base_size / 2.0)))]:
            bin_width = float(max_value - min_value) / bins
            x_axis = [min_value + (bin_width * x) for x in range(1, bins + 1)]
            views.append({"view": view, "bins": bins,
                          "x": x_axis, "y": [0] * len(x_axis)})
        return views

    def add_iteration(self, iteration):
        for name, value in self._map_iteration_values(iteration):
            if name not in self._data:
                raise KeyError("Unexpected histogram name: %s" % name)
            for i, view in enumerate(self._data[name]["views"]):
                for bin_i, bin_v in enumerate(view["x"]):
                    if (value or 0) <= bin_v:
                        self._data[name]["views"][i]["y"][bin_i] += 1
                        break

    def render(self):
        data = []
        for name, hist in self._data.items():
            data.append(
                [{"key": name, "view": v["view"], "disabled": hist["disabled"],
                  "values": [{"x": x, "y": y} for x, y in zip(v["x"], v["y"])]}
                 for v in hist["views"]])
        return data


class MainHistogramChart(HistogramChart):

    def __init__(self, benchmark_info):
        super(MainHistogramChart, self).__init__(benchmark_info)
        views = self._init_views(self._benchmark_info["min_duration"],
                                 self._benchmark_info["max_duration"])
        self._data["task"] = {"views": views, "disabled": None}

    def _map_iteration_values(self, iteration):
        return [("task", 0 if iteration["error"] else iteration["duration"])]


class AtomicHistogramChart(HistogramChart):

    def __init__(self, benchmark_info):
        super(AtomicHistogramChart, self).__init__(benchmark_info)
        for i, atomic in enumerate(self._benchmark_info["atomic"].items()):
            name, value = atomic
            self._data[name] = {
                "views": self._init_views(value["min_duration"],
                                          value["max_duration"]),
                "disabled": i}

    def _map_iteration_values(self, iteration):
        iteration = self._fix_atomic_actions(iteration)
        return list(iteration["atomic_actions"].items())


class MainStatsTable(Chart):

    def _init_row(self, name, iterations_count):

        def round_3(stream, no_result):
            if no_result:
                return "n/a"
            return round(stream.result(), 3)

        return [
            ("Action", name),
            ("Min (sec)", streaming.MinComputation(), round_3),
            ("Median (sec)",
             streaming.PercentileComputation(0.5, iterations_count), round_3),
            ("90%ile (sec)",
             streaming.PercentileComputation(0.9, iterations_count), round_3),
            ("95%ile (sec)",
             streaming.PercentileComputation(0.95, iterations_count), round_3),
            ("Max (sec)", streaming.MaxComputation(), round_3),
            ("Avg (sec)", streaming.MeanComputation(), round_3),
            ("Success", streaming.MeanComputation(),
             lambda stream, no_result: "%.1f%%" % (stream.result() * 100)),
            ("Count", streaming.IncrementComputation(),
             lambda x, no_result: x.result())
        ]

    def __init__(self, benchmark_info, zipped_size=1000):
        self.rows = list(benchmark_info["atomic"].keys())
        self.rows.append("total")
        self.rows_index = dict((name, i) for i, name in enumerate(self.rows))
        self.table = [self._init_row(name, benchmark_info["iterations_count"])
                      for name in self.rows]

    def add_iteration(self, iteration):
        data = copy.copy(iteration["atomic_actions"])
        data["total"] = iteration["duration"]

        for name, value in data.items():
            index = self.rows_index[name]
            self.table[index][-1][1].add(None)
            if iteration["error"]:
                self.table[index][-2][1].add(0)
            else:
                self.table[index][-2][1].add(1)
                for elem in self.table[index][1:-2]:
                    elem[1].add(value)

    def render(self):
        rows = []

        for i in range(len(self.table)):
            row = [self.table[i][0][1]]
            # no results if all iterations failed
            no_result = self.table[i][-2][1].result() == 0.0
            row.extend(x[2](x[1], no_result) for x in self.table[i][1:])
            rows.append(row)

        return {"cols": list(map(lambda x: x[0], self.table[0])),
                "rows": rows}

    def _map_iteration_values(self, iteration):
        pass
