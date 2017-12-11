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
import collections
import math
import six

from rally.common.plugin import plugin
from rally.common import streaming_algorithms as streaming
from rally.task import atomic
from rally.task.processing import utils


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Chart(plugin.Plugin):
    """Base class for charts.

    This is a base for all plugins that prepare data for specific charts
    in HTML report. Each chart must at least declare chart widget and
    prepare data that is suitable for rendering by JavaScript.
    """

    @abc.abstractproperty
    def widget(self):
        """Widget name to display this chart by JavaScript."""

    def __init__(self, workload, zipped_size=1000):
        """Setup initial values.

        :param workload: dict, detailed info about the Workload
        :param zipped_size: int maximum number of points on scale
        """
        self._data = collections.OrderedDict()  # Container for results
        self._workload = workload
        self.base_size = self._workload["total_iteration_count"]
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

    @classmethod
    def render_complete_data(cls, data):
        """render processed complete data for drawing."""
        return data

    def _fix_atomic_actions(self, atomic_actions):
        """Set `0' for missed atomic actions.

        Since some atomic actions can absent in some iterations
        due to failures, this method must be used in all cases
        related to atomic actions processing.
        """
        return list(
            (name, atomic_actions.get(name, {}).get("duration", 0))
            for name in self._get_atomic_names()
        )

    def _get_atomic_names(self):
        duration_stats = self._workload["statistics"]["durations"]
        return [a["display_name"] for a in duration_stats["atomics"]]

    def _map_iteration_values(self, iteration):
        """Get values for processing, from given iteration."""
        return iteration


class MainStackedAreaChart(Chart):

    widget = "StackedArea"

    def _map_iteration_values(self, iteration):
        if iteration["error"]:
            result = [("duration", 0), ("idle_duration", 0)]
            if self._workload["failed_iteration_count"]:
                result.append(
                    ("failed_duration",
                     iteration["duration"] + iteration["idle_duration"]))
        else:
            result = [("duration", iteration["duration"]),
                      ("idle_duration", iteration["idle_duration"])]
            if self._workload["failed_iteration_count"]:
                result.append(("failed_duration", 0))
        return result


class AtomicStackedAreaChart(Chart):

    widget = "StackedArea"

    def _map_iteration_values(self, iteration):
        atomic_actions = atomic.merge_atomic_actions(
            iteration["atomic_actions"])
        atomics = self._fix_atomic_actions(atomic_actions)
        if self._workload["failed_iteration_count"]:
            if iteration["error"]:
                failed_duration = (
                    iteration["duration"] + iteration["idle_duration"]
                    - sum([(a[1] or 0) for a in atomics]))
            else:
                failed_duration = 0
            atomics.append(("failed_duration", failed_duration))
        return atomics


class AvgChart(Chart):
    """Base class for charts with average results."""

    widget = "Pie"

    def add_iteration(self, iteration):
        for name, value in self._map_iteration_values(iteration):
            if name not in self._data:
                self._data[name] = streaming.MeanComputation()
            self._data[name].add(value or 0)

    def render(self):
        return [(k, v.result()) for k, v in self._data.items()]


class AtomicAvgChart(AvgChart):

    def _map_iteration_values(self, iteration):
        atomic_actions = atomic.merge_atomic_actions(
            iteration["atomic_actions"])
        return self._fix_atomic_actions(atomic_actions)


class LoadProfileChart(Chart):
    """Chart for parallel durations."""

    widget = "StackedArea"

    def __init__(self, workload, name="parallel iterations",
                 scale=100):
        """Setup chart with graph name and scale.

        :param workload:  dict, detailed information about Workload
        :param name: str name for X axis
        :param scale: int number of X points
        """
        super(LoadProfileChart, self).__init__(workload)
        self._name = name
        # NOTE(boris-42): Add 2 points at the end of graph so at the end of
        #                 graph there will be point with 0 running iterations.
        self._duration = self._workload["load_duration"] * (1 + 2.0 / scale)

        self.step = self._duration / float(scale)
        self._time_axis = [self.step * x
                           for x in six.moves.range(int(scale))
                           if (self.step * x) < self._duration]
        self._time_axis.append(self._duration)
        self._running = [0] * len(self._time_axis)
        # NOTE(andreykurilin): There is a "start_time" field in workload
        #   object, but due to transformations in database layer, the
        #   microseconds can be not accurate enough.
        if self._workload["data"]:
            self._tstamp_start = self._workload["data"][0]["timestamp"]
        else:
            self._tstamp_start = self._workload["start_time"]

    def _map_iteration_values(self, iteration):
        return iteration["timestamp"], iteration["duration"]

    def add_iteration(self, iteration):
        timestamp, duration = self._map_iteration_values(iteration)
        ts_start = timestamp - self._tstamp_start
        started_idx = bisect.bisect(self._time_axis, ts_start)
        ended_idx = bisect.bisect(self._time_axis, ts_start + duration)
        if self._time_axis[ended_idx - 1] == ts_start + duration:
            ended_idx -= 1
        for idx in range(started_idx + 1, ended_idx):
            self._running[idx] += 1
        if started_idx == ended_idx:
            self._running[ended_idx] += duration / self.step
        else:
            self._running[started_idx] += (
                self._time_axis[started_idx] - ts_start) / self.step
            self._running[ended_idx] += (
                ts_start + duration
                - self._time_axis[ended_idx - 1]) / self.step

    def render(self):
        return [(self._name, list(zip(self._time_axis, self._running)))]


class HistogramChart(Chart):
    """Base class for chart with histograms.

    This chart is relatively complex, because actually it is a set
    of histograms, that usually can be switched by dropdown select.
    And each histogram has several data views.
    """

    widget = "Histogram"

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
            for idx, v in enumerate(hist["views"]):
                graph = {"key": name,
                         "view": v["view"],
                         "disabled": hist["disabled"],
                         "values": [{"x": x, "y": y}
                                    for x, y in zip(v["x"], v["y"])]}
                try:
                    data[idx].append(graph)
                except IndexError:
                    data.append([graph])
        return {"data": data, "views": [{"id": i, "name": d[0]["view"]}
                                        for i, d in enumerate(data)]}


class MainHistogramChart(HistogramChart):

    def __init__(self, workload_info):
        super(MainHistogramChart, self).__init__(workload_info)
        views = self._init_views(self._workload["min_duration"],
                                 self._workload["max_duration"])
        self._data["task"] = {"views": views, "disabled": None}

    def _map_iteration_values(self, iteration):
        return [("task", 0 if iteration["error"] else iteration["duration"])]


class AtomicHistogramChart(HistogramChart):

    def __init__(self, workload_info):
        super(AtomicHistogramChart, self).__init__(workload_info)
        for i, aa in enumerate(
                self._workload["statistics"]["durations"]["atomics"]):
            self._data[aa["display_name"]] = {
                "views": self._init_views(aa["data"]["min"],
                                          aa["data"]["max"]),
                "disabled": i}

    def _map_iteration_values(self, iteration):
        atomic_actions = atomic.merge_atomic_actions(
            iteration["atomic_actions"])
        return self._fix_atomic_actions(atomic_actions)


@six.add_metaclass(abc.ABCMeta)
class Table(Chart):
    """Base class for tables.

    Each Table subclass represents HTML table which can be easily rendered in
    report. Subclasses are responsible for setting up both columns and rows:
    columns are set simply by `columns' property (list of str columns names)
    and rows must be initialized in _data property, with the following format:
        self._data = {name: [streaming_ins, postprocess_func or None], ...}
          where:
            name - str name of table row parameter
            streaming_ins - instance of streaming algorithm
            postprocess_func - optional function that processes final result,
                               None means usage of default self._round()
        This can be done in __init__() or even in add_iteration().
    """

    widget = "Table"
    _styles = {}

    @abc.abstractproperty
    def columns(self):
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
            if isinstance(ins, (streaming.MinComputation,
                                streaming.MaxComputation,
                                streaming.MeanComputation)):
                # NOTE(amaretskiy): None means this computation
                #                   has never been called
                return ins.result() is not None
        return True

    def _process_row(self, name, values):
        row = [name]
        has_result = self._row_has_results(values)
        for ins, fn in values:
            fn = fn or self._round
            row.append(fn(ins, has_result))
        return row

    def get_rows(self):
        """Collect rows values finally, after all data is processed.

        :returns: [str_name, (float or str), (float or str), ...]
        """
        rows = []
        for name, values in self._data.items():
            rows.append(self._process_row(name, values))
        return rows

    def render(self):
        rows = self.get_rows()
        if self._styles is None:
            # do not apply anything
            styles = {}
        elif not self._styles and rows:
            # make the last elements bold
            styles = {len(rows) - 1: "rich"}
        else:
            styles = self._styles
        return {"cols": self.columns,
                "rows": rows,
                "styles": styles}


class MainStatsTable(Table):

    columns = ["Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
               "95%ile (sec)", "Max (sec)", "Avg (sec)", "Success", "Count"]

    _DEPTH_OF_PROCESSING = 2

    def __init__(self, *args, **kwargs):
        super(MainStatsTable, self).__init__(*args, **kwargs)
        self.iters_num = self._workload["total_iteration_count"]

    def _initialize_atomic(self, name, root, real_name=None, count=1):
        real_name = real_name or name
        root[name] = {
            # streaming algorithms
            "sa": [
                [streaming.MinComputation(), None],
                [streaming.PercentileComputation(0.5, self.iters_num), None],
                [streaming.PercentileComputation(0.9, self.iters_num), None],
                [streaming.PercentileComputation(0.95, self.iters_num), None],
                [streaming.MaxComputation(), None],
                [streaming.MeanComputation(), None],
                [streaming.MeanComputation(),
                 lambda st, has_result: ("%.1f%%" % (st.result() * 100)
                                         if has_result else "n/a")],
                [streaming.IncrementComputation(),
                 lambda st, has_result: st.result()]],
            "children": collections.OrderedDict(),
            "real_name": real_name,
            "count_per_iteration": count
        }

    def _add_data(self, raw_data, root=None):
        """Add iteration data."""
        p_data = self._data if root is None else root
        for name, data in raw_data.items():
            original_name = name
            if data["count"] > 1:
                name += (" (x%s)" % data["count"])
            if name not in p_data:
                self._initialize_atomic(name,
                                        root=p_data,
                                        real_name=original_name,
                                        count=data["count"])

            stats = p_data[name]["sa"]
            # count
            stats[-1][0].add()
            # success
            stats[-2][0].add(0 if data.get("failed", False) else 1)
            for idx in range(6):
                stats[idx][0].add(data["duration"])

            if data["children"]:
                self._add_data(data["children"], root=p_data[name]["children"])

    def add_iteration(self, iteration):
        """Add data of a single iteration."""
        data = atomic.merge_atomic_actions(iteration["atomic_actions"])
        # NOTE(andreykurilin): the easiest way to identify the last
        #   atomic is to find the last added key to the OrderedDict. The
        #   most perfect way is to use reversed, since class OrderedDict
        #   uses a doubly linked list for the dictionary items and
        #   implements __reversed__(), what is why such implementation
        #   gives you O(1) access to the desired element.
        if data:
            the_last = data[next(reversed(data))]
            if iteration["error"] and not the_last.get("failed", False):
                # un-wrapped action failed
                data["<no-name-action>"] = {"duration": 0, "count": 1,
                                            "failed": True, "children": {}}
        total_duration = iteration["duration"] + iteration["idle_duration"]
        data["total"] = {"duration": total_duration,
                         "count": 1,
                         "failed": bool(iteration["error"]),
                         "children": collections.OrderedDict(
                             [("duration", {
                                 "duration": iteration["duration"],
                                 "count": 1,
                                 "failed": bool(iteration["error"]),
                                 "children": []}),
                              ("idle_duration", {
                                  "duration": iteration["idle_duration"],
                                  "count": 1,
                                  "failed": bool(iteration["error"]),
                                  "children": []})
                              ])}

        self._add_data(data)

    def _process_result(self, name, values, depth=0):
        row = self._process_row(name, values["sa"])
        children = []

        for c_name, c_values in values["children"].items():
            children.append(self._process_result(c_name, c_values))
        return {"data": {"iteration_count": row[8],
                         "min": row[1],
                         "median": row[2],
                         "90%ile": row[3],
                         "95%ile": row[4],
                         "max": row[5],
                         "avg": row[6],
                         "success": row[7]},
                "count_per_iteration": values["count_per_iteration"],
                "name": values["real_name"],
                "display_name": name,
                "children": children}

    def _get_results(self):
        if self._data:
            # NOTE(andreykurilin): In case when the specific atomic action was
            #   not executed in the first iteration, it will be added to
            #   self._data after the "total" raw. It is a wrong order, so
            #   let's ensure that the "total" is always at the end
            self._data["total"] = self._data.pop("total")
        else:
            # NOTE(andreykurilin): The workload doesn't have any iteration, so
            #   the method `add_iteration` had not been called and 'total' item
            #   had not be initialized. Let's do it here, since 'total' item
            #   should always present in the rows.
            self._initialize_atomic("total", root=self._data)

        results = []
        for name, values in self._data.items():
            results.append(self._process_result(name, values))
        return results

    def get_rows(self):
        rows = []

        def _process_elem(elem, depth=0):
            name = elem["display_name"]
            if depth > 0:
                name = (" %s> %s" % ("-" * depth, name))
            rows.append([name,
                         elem["data"]["min"],
                         elem["data"]["median"],
                         elem["data"]["90%ile"],
                         elem["data"]["95%ile"],
                         elem["data"]["max"],
                         elem["data"]["avg"],
                         elem["data"]["success"],
                         elem["data"]["iteration_count"]])
            for child in elem["children"]:
                _process_elem(child, depth=(depth + 1))

        for elem in self._get_results():
            _process_elem(elem)

        return rows

    def to_dict(self):
        res = self._get_results()
        return {"total": res[-1], "atomics": res[:-1]}

    def render(self):
        rendered_data = super(MainStatsTable, self).render()
        rows_len = len(rendered_data["rows"])
        if rows_len > 1:
            styles = {rows_len - 3: "rich",
                      rows_len - 2: "oblique",
                      rows_len - 1: "oblique"}
            for i, row in enumerate(rendered_data["rows"]):
                if i == rows_len - 3:
                    break
                if row[0].startswith(" -"):
                    styles[i] = "oblique"
            rendered_data["styles"] = styles
        return rendered_data


class OutputChart(Chart):
    """Base class for charts related to scenario output."""

    def __init__(self, workload_info, zipped_size=1000,
                 title="", description="", label="", axis_label=""):
        super(OutputChart, self).__init__(workload_info, zipped_size)
        self.title = title
        self.description = description
        self.label = label
        self.axis_label = axis_label

    def render(self):
        return {"title": self.title,
                "description": self.description,
                "widget": self.widget,
                "data": super(OutputChart, self).render(),
                "label": self.label,
                "axis_label": self.axis_label}


@plugin.configure(name="StackedArea")
class OutputStackedAreaChart(OutputChart):
    """Display results as stacked area.

    This plugin processes additive data and displays it in HTML report
    as stacked area with X axis bound to iteration number.
    Complete output data is displayed as stacked area as well, without
    any processing.

    Keys "description", "label" and "axis_label" are optional.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            additive={"title": "Additive data as stacked area",
                      "description": "Iterations trend for foo and bar",
                      "chart_plugin": "StackedArea",
                      "data": [["foo", 12], ["bar", 34]]},
            complete={"title": "Complete data as stacked area",
                      "description": "Data is shown as stacked area, as-is",
                      "chart_plugin": "StackedArea",
                      "data": [["foo", [[0, 5], [1, 42], [2, 15], [3, 7]]],
                               ["bar", [[0, 2], [1, 1.3], [2, 5], [3, 9]]]],
                      "label": "Y-axis label text",
                      "axis_label": "X-axis label text"})
    """

    widget = "StackedArea"

    def render(self):
        result = super(OutputStackedAreaChart, self).render()

        # NOTE(amaretskiy): transform to Table if there is a single iteration
        if result["data"] and len(result["data"][0][1]) == 1:
            rows = [[v[0], v[1][0][1]] for v in result["data"]]
            result.update({"widget": "Table",
                           "data": {"cols": ["Name", self.label or "Value"],
                                    "rows": rows}})
        return result


@plugin.configure(name="Lines")
class OutputLinesChart(OutputStackedAreaChart):
    """Display results as generic chart with lines.

    This plugin processes additive data and displays it in HTML report
    as linear chart with X axis bound to iteration number.
    Complete output data is displayed as linear chart as well, without
    any processing.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            additive={"title": "Additive data as stacked area",
                      "description": "Iterations trend for foo and bar",
                      "chart_plugin": "Lines",
                      "data": [["foo", 12], ["bar", 34]]},
            complete={"title": "Complete data as stacked area",
                      "description": "Data is shown as stacked area, as-is",
                      "chart_plugin": "Lines",
                      "data": [["foo", [[0, 5], [1, 42], [2, 15], [3, 7]]],
                               ["bar", [[0, 2], [1, 1.3], [2, 5], [3, 9]]]],
                      "label": "Y-axis label text",
                      "axis_label": "X-axis label text"})
    """

    widget = "Lines"


@plugin.configure(name="Pie")
class OutputAvgChart(OutputChart, AvgChart):
    """Display results as pie, calculate average values for additive data.

    This plugin processes additive data and calculate average values.
    Both additive and complete data are displayed in HTML report as pie chart.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            additive={"title": "Additive output",
                      "description": ("Pie with average data "
                                      "from all iterations values"),
                      "chart_plugin": "Pie",
                      "data": [["foo", 12], ["bar", 34], ["spam", 56]]},
            complete={"title": "Complete output",
                      "description": "Displayed as a pie, as-is",
                      "chart_plugin": "Pie",
                      "data": [["foo", 12], ["bar", 34], ["spam", 56]]})
    """

    widget = "Pie"


@plugin.configure(name="Table")
class OutputTable(OutputChart, Table):
    """Display complete output as table, can not be used for additive data.

    Use this plugin for complete output data to display it in HTML report
    as table. This plugin can not be used for additive data because it
    does not contain any processing logic.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            complete={"title": "Arbitrary Table",
                      "description": "Just show columns and rows as-is",
                      "chart_plugin": "Table",
                      "data": {"cols": ["foo", "bar", "spam"],
                               "rows": [["a row", 1, 2], ["b row", 3, 4],
                                        ["c row", 5, 6]]}})
    """

    widget = "Table"


@plugin.configure(name="StatsTable")
class OutputStatsTable(OutputTable):
    """Calculate statistics for additive data and display it as table.

    This plugin processes additive data and compose statistics that is
    displayed as table in HTML report.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            additive={"title": "Statistics",
                      "description": ("Table with statistics generated "
                                      "from all iterations values"),
                      "chart_plugin": "StatsTable",
                      "data": [["foo stat", 12], ["bar", 34], ["spam", 56]]})
    """

    columns = ["Action", "Min (sec)", "Median (sec)", "90%ile (sec)",
               "95%ile (sec)", "Max (sec)", "Avg (sec)", "Count"]

    def add_iteration(self, iteration):
        for name, value in self._map_iteration_values(iteration):
            if name not in self._data:
                iters_num = self._workload["total_iteration_count"]
                self._data[name] = [
                    [streaming.MinComputation(), None],
                    [streaming.PercentileComputation(0.5, iters_num), None],
                    [streaming.PercentileComputation(0.9, iters_num), None],
                    [streaming.PercentileComputation(0.95, iters_num), None],
                    [streaming.MaxComputation(), None],
                    [streaming.MeanComputation(), None],
                    [streaming.IncrementComputation(),
                     lambda v, na: v.result()]]

            self._data[name][-1][0].add(None)
            self._data[name][-2][0].add(1)
            for idx, dummy in enumerate(self._data[name][:-1]):
                self._data[name][idx][0].add(value)


@plugin.configure(name="TextArea")
class OutputTextArea(OutputChart):
    """Arbitrary text

    This plugin processes complete data and displays of output in HTML report.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            complete={"title": "Script Inline",
                      "chart_plugin": "TextArea",
                      "data": ["first output", "second output",
                               "third output"]]})
    """

    widget = "TextArea"


_OUTPUT_SCHEMA = {
    "key_types": {
        "title": six.string_types,
        "description": six.string_types,
        "chart_plugin": six.string_types,
        "data": (list, dict),
        "label": six.string_types,
        "axis_label": six.string_types},
    "required": ["title", "chart_plugin", "data"]}


def validate_output(output_type, output):
    # TODO(amaretskiy): this validation is simple and must be improved.
    #   Maybe it is worth to add classmethod OutputChart.validate(), so
    #   we could have flexible validation for custom chart plugins
    if output_type not in ("additive", "complete"):
        return ("unexpected output type: '%s', "
                "should be in ('additive', 'complete')" % output_type)

    if not isinstance(output, dict):
        return ("%(name)s output item has wrong type '%(type)s', "
                "must be 'dict'" % {"name": output_type,
                                    "type": type(output).__name__})

    for key in _OUTPUT_SCHEMA["required"]:
        if key not in output:
            return ("%(name)s output missing key '%(key)s'"
                    % {"name": output_type, "key": key})

    for key in output:
        if key not in _OUTPUT_SCHEMA["key_types"]:
            return ("%(name)s output has unexpected key '%(key)s'"
                    % {"name": output_type, "key": key})

        proper_type = _OUTPUT_SCHEMA["key_types"][key]
        if not isinstance(output[key], proper_type):
            if type(proper_type) == tuple:
                return ("Value of %(name)s output %(key)s has wrong type "
                        "'%(actual_type)s', should be in %(types)r"
                        % {"name": output_type,
                           "key": key,
                           "actual_type": type(output[key]).__name__,
                           "types": tuple(t.__name__
                                          for t in proper_type)})
            return ("Value of %(name)s output %(key)s has wrong type "
                    "'%(actual_type)s', should be %(proper_type)s"
                    % {"name": output_type,
                       "key": key,
                       "actual_type": type(output[key]).__name__,
                       "proper_type": proper_type.__name__})
