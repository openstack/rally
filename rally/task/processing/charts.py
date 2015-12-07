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
        If overridden, this method must use streaming data processing,
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
                 int(math.ceil(2 * self.base_size ** (1.0 / 3))))]:
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


@six.add_metaclass(abc.ABCMeta)
class Table(Chart):
    """Base class for tables.

    Each Table subclass represents HTML table which can be easily rendered in
    report. Subclasses are responsible for setting up both columns and rows:
    columns are set simply by COLUMNS property (list of str columns names)
    and rows must be initialized in _data property, with the following format:
        self._data = {name: [streaming_ins, postprocess_func or None], ...}
          where:
            name - str name of table row parameter
            streaming_ins - instance of streaming algorithm
            postprocess_func - optional function that processes final result,
                               None means usage of default self._round()
        This can be done in __init__() or even in add_iteration().
    """

    @abc.abstractproperty
    def COLUMNS(self):
        """List of columns names."""

    def _round(self, ins, has_result):
        """This is a default post-process function for table cell value.

        :param ins: streaming_algorithms.StreamingAlgorithm subclass instance
        :param has_result: bool, whether current row is effective
        :returns: rounded float
        :returns: str "n/a"
        """
        return round(ins.result(), 3) if has_result else "n/a"

    def _row_has_results(self, values):
        """Determine whether row can be assumed as having values.

        :param values: row values list
                       [(StreamingAlgorithm, function or None), ...]
        :returns: bool
        """
        for ins, fn in values:
            if isinstance(ins, streaming.MinComputation):
                return bool(ins.result())
        return True

    def get_rows(self):
        """Collect rows values finally, after all data is processed.

        :returns: [str_name, (float or str), (float or str), ...]
        """
        rows = []
        for name, values in self._data.items():
            row = [name]
            has_result = self._row_has_results(values)
            for ins, fn in values:
                fn = fn or self._round
                row.append(fn(ins, has_result))
            rows.append(row)
        return rows

    def render(self):
        return {"cols": self.COLUMNS, "rows": self.get_rows()}


class MainStatsTable(Table):

    COLUMNS = ["Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
               "95%ile (sec)", "Max (sec)", "Avg (sec)", "Success", "Count"]

    def __init__(self, *args, **kwargs):
        super(MainStatsTable, self).__init__(*args, **kwargs)
        iters_num = self._benchmark_info["iterations_count"]
        for name in (list(self._benchmark_info["atomic"].keys()) + ["total"]):
            self._data[name] = [
                [streaming.MinComputation(), None],
                [streaming.PercentileComputation(0.5, iters_num), None],
                [streaming.PercentileComputation(0.9, iters_num), None],
                [streaming.PercentileComputation(0.95, iters_num), None],
                [streaming.MaxComputation(), None],
                [streaming.MeanComputation(), None],
                [streaming.MeanComputation(),
                 lambda st, has_result: ("%.1f%%" % (st.result() * 100)
                                         if has_result else "n/a")],
                [streaming.IncrementComputation(),
                 lambda st, has_result: st.result()]]

    def _map_iteration_values(self, iteration):
        return dict(iteration["atomic_actions"], total=iteration["duration"])

    def add_iteration(self, iteration):
        for name, value in self._map_iteration_values(iteration).items():
            self._data[name][-1][0].add()
            if iteration["error"]:
                self._data[name][-2][0].add(0)
            else:
                self._data[name][-2][0].add(1)
                for idx, dummy in enumerate(self._data[name][:-2]):
                    self._data[name][idx][0].add(value)
