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
