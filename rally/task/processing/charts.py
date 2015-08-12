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


class StackedAreaChart(Chart):
    """Abstract class for generic stacked area."""

    def render(self):
        return [{"key": k, "values": v}
                for k, v in super(StackedAreaChart, self).render()]


class MainStackedAreaChart(StackedAreaChart):

    def _map_iteration_values(self, iteration):
        if iteration["error"]:
            return [("duration", 0), ("idle_duration", 0),
                    ("failed_duration",
                     iteration["duration"] + iteration["idle_duration"])]
        return [("duration", iteration["duration"]),
                ("idle_duration", iteration["idle_duration"]),
                ("failed_duration", 0)]


class AtomicStackedAreaChart(StackedAreaChart):

    def _map_iteration_values(self, iteration):
        iteration = self._fix_atomic_actions(iteration)
        atomics = list(iteration["atomic_actions"].items())
        if iteration["error"]:
            failed_duration = (
                iteration["duration"] + iteration["idle_duration"]
                - sum([(a[1] or 0) for a in atomics]))
        else:
            failed_duration = 0
        atomics.append(("failed_duration", failed_duration))
        return atomics


class OutputStackedAreaChart(StackedAreaChart):

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
        return [{"key": k, "values": v.result()}
                for k, v in self._data.items()]


class AtomicAvgChart(AvgChart):

    def _map_iteration_values(self, iteration):
        iteration = self._fix_atomic_actions(iteration)
        return list(iteration["atomic_actions"].items())


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


@six.add_metaclass(abc.ABCMeta)
class Table(Chart):
    """Base class for table with processed data."""

    @abc.abstractmethod
    def _init_columns(self):
        """Initialize columns processing.

        :returns: OrderedDict(
            (("str column name", <StreamingAlgorithm instance>),
             ...))
        """

    def add_iteration(self, iteration):
        for name, value in self._map_iteration_values(iteration):
            if name not in self._data:
                self._data[name] = self._init_columns()
            for column in self._data[name]:
                self._data[name][column].add(value or 0)

    @abc.abstractmethod
    def render(self):
        """Generate table data ready for displaying.

        :returns: {"cols": [str, ...], "rows": [[numeric, ...], ...]}
        """


class MainStatsTable(Table):

    columns = ["Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
               "95%ile (sec)", "Max (sec)", "Avg (sec)", "Success", "Count"]
    float_columns = ["Min (sec)", "Median (sec)", "90%ile (sec)",
                     "95%ile (sec)", "Max (sec)", "Avg (sec)"]

    def _init_columns(self):
        return costilius.OrderedDict(
            (("Min (sec)", streaming.MinComputation()),
             ("Median (sec)", streaming.PercentileComputation(50)),
             ("90%ile (sec)", streaming.PercentileComputation(90)),
             ("95%ile (sec)", streaming.PercentileComputation(95)),
             ("Max (sec)", streaming.MaxComputation()),
             ("Avg (sec)", streaming.MeanComputation()),
             ("Success", streaming.ProgressComputation(self.base_size)),
             ("Count", streaming.IncrementComputation())))

    def _map_iteration_values(self, iteration):
        iteration = self._fix_atomic_actions(iteration)
        values = list(iteration["atomic_actions"].items())
        values.append(("total",
                       0 if iteration["error"] else iteration["duration"]))
        return values

    def render(self):
        rows = []
        total = None

        for name, values in self._data.items():
            row = [name]
            for column_name, column in self._data[name].items():
                if column_name == "Success":
                    row.append("%.1f%%" % column.result())
                else:
                    row.append(round(column.result(), 3))

            # Save `total' - it must be appended last
            if name.lower() == "total":
                total = row
                continue
            rows.append(row)

        if total:
            rows.append(total)

        return {"cols": self.columns, "rows": rows}
