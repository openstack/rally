# Copyright 2014: Mirantis Inc.
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

import math

from rally.common import costilius
from rally.common.i18n import _
from rally import exceptions


def mean(values):
    """Find the simple mean of a list of values.

    :parameter values: non-empty list of numbers

    :returns: float value
    """
    if not values:
        raise exceptions.InvalidArgumentsException(
            "the list should be non-empty")
    return math.fsum(values) / len(values)


def median(values):
    """Find the simple median of a list of values.

    :parameter values: non-empty list of numbers

    :returns: float value
     """
    if not values:
        raise ValueError(_("no median for empty data"))

    values = sorted(values)
    size = len(values)

    if size % 2 == 1:
        return values[size // 2]
    else:
        index = size // 2
        return (values[index - 1] + values[index]) / 2.0


def percentile(values, percent):
    """Find the percentile of a list of values.

    :parameter values: list of numbers
    :parameter percent: float value from 0.0 to 1.0

    :returns: the percentile of values
    """
    if not values:
        return None
    values.sort()
    k = (len(values) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[int(f)] * (c - k)
    d1 = values[int(c)] * (k - f)
    return (d0 + d1)


# TODO(amaretskiy): This function is deprecated and should be removed
#                   after it becomes not used by rally.cli.commands.task
def get_atomic_actions_data(raw_data):
    """Retrieve detailed (by atomic actions & total runtime) benchmark data.

    :parameter raw_data: list of raw records (scenario runner output)

    :returns: dictionary containing atomic action + total duration lists
              for all atomic action keys
    """
    atomic_actions = []
    for row in raw_data:
        # find first non-error result to get atomic actions names
        if not row["error"] and "atomic_actions" in row:
            atomic_actions = row["atomic_actions"].keys()
            break
    actions_data = costilius.OrderedDict()
    for atomic_action in atomic_actions:
        actions_data[atomic_action] = [
            r["atomic_actions"][atomic_action]
            for r in raw_data
            if r["atomic_actions"].get(atomic_action) is not None]
    actions_data["total"] = [r["duration"] for r in raw_data if not r["error"]]
    return actions_data


class GraphZipper(object):

    def __init__(self, base_size, zipped_size=1000):
        """Init graph zipper.

        :param base_size: Amount of points in raw graph
        :param zip_size: Amount of points that should be in zipped graph
        """
        self.base_size = base_size
        self.zipped_size = zipped_size
        if self.base_size >= self.zipped_size:
            self.compression_ratio = self.base_size / float(self.zipped_size)
        else:
            self.compression_ratio = 1

        self.point_order = 0

        self.cached_ratios_sum = 0
        self.ratio_value_points = []

        self.zipped_graph = []

    def _get_zipped_point(self):
        if self.point_order - self.compression_ratio <= 1:
            order = 1
        elif self.point_order == self.base_size:
            order = self.base_size
        else:
            order = self.point_order - int(self.compression_ratio / 2.0)

        value = (
            sum(p[0] * p[1] for p in self.ratio_value_points) /
            self.compression_ratio
        )

        return [order, value]

    def add_point(self, value):
        self.point_order += 1

        if self.point_order > self.base_size:
            raise RuntimeError("GraphZipper is already full. "
                               "You can't add more points.")

        if not isinstance(value, (int, float)):
            value = 0

        if self.compression_ratio <= 1:    # We don't need to compress
            self.zipped_graph.append([self.point_order, value])
        elif self.cached_ratios_sum + 1 < self.compression_ratio:
            self.cached_ratios_sum += 1
            self.ratio_value_points.append([1, value])
        else:
            rest = self.compression_ratio - self.cached_ratios_sum
            self.ratio_value_points.append([rest, value])
            self.zipped_graph.append(self._get_zipped_point())
            self.ratio_value_points = [[1 - rest, value]]
            self.cached_ratios_sum = self.ratio_value_points[0][0]

    def get_zipped_graph(self):
        return self.zipped_graph
