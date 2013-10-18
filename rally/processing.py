# Copyright 2013: Mirantis Inc.
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

import itertools

from rally import db
from rally import exceptions
from rally.openstack.common import importutils

plt = importutils.try_import("matplotlib.pyplot")
ticker = importutils.try_import("matplotlib.ticker")


def aggregated_plot(task_id, aggregated_field):
    """Draws an aggregated figure of benchmark runtimes in a separate window.

    The resulting figure has the aggregated field values on the X axis and
    the benchmark runtimes (in seconds) on the Y axis. For each benchmark run,
    minimum, maximum and average runtime values will be drawn, thus resulting
    in three plots on the figure.

    :param task_id: ID of the task to draw the plot for
    :param aggregated_field: Field from the test config to aggregate the data
                             on. This can be e.g. "active_users", "times" etc.
    """

    task = db.task_get_detailed(task_id)

    task["results"].sort(key=lambda res: res["key"]["name"])
    results_by_benchmark = itertools.groupby(task["results"],
                                             lambda res: res["key"]["name"])
    for benchmark_name, data in results_by_benchmark:
        data_dict = {}
        for result in data:

            if aggregated_field not in result["key"]["kw"]["config"]:
                raise exceptions.NoSuchConfigField(name=aggregated_field)

            raw = result["data"]["raw"]
            times = map(lambda x: x["time"],
                        filter(lambda r: not r["error"], raw))

            aggr_field_val = result["key"]["kw"]["config"][aggregated_field]

            data_dict[aggr_field_val] = {"min": min(times),
                                         "avg": sum(times) / len(times),
                                         "max": max(times)}

        aggr_field_vals = sorted(data_dict.keys())
        mins = [data_dict[x]["min"] for x in aggr_field_vals]
        avgs = [data_dict[x]["avg"] for x in aggr_field_vals]
        maxes = [data_dict[x]["max"] for x in aggr_field_vals]

        axes = plt.subplot(111)

        plt.plot(aggr_field_vals, maxes, "r-", label="max", linewidth=2)
        plt.plot(aggr_field_vals, avgs, "b-", label="avg", linewidth=2)
        plt.plot(aggr_field_vals, mins, "g-", label="min", linewidth=2)

        title = "Benchmark results: %s" % benchmark_name
        plt.title(title)
        fig = plt.gcf()
        fig.canvas.set_window_title(title)

        plt.xlabel(aggregated_field)
        axes.set_xlim(0, max(aggr_field_vals) + 1)
        x_axis = axes.get_xaxis()
        x_axis.set_major_locator(ticker.MaxNLocator(integer=True))

        plt.ylabel("Time (sec)")
        axes.set_ylim(min(mins) - 2, max(maxes) + 2)

        plt.legend(loc="upper right")

        plt.show()


# NOTE(msdubov): A mapping from plot names to plotting functions is used in CLI
PLOTS = {
    "aggregated": aggregated_plot
}
