# Copyright 2014: The Rally team
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


class Histogram:
    """Represents a Histogram chart."""

    def __init__(self, data, number_of_bins, method=None, key=None):
        """Initialize a Histogram object

        :param data: a list of numbers
        :param number_of_bins: an integer
        :param description: a string
        :param key: a string
        """
        self.data = data
        self.number_of_bins = number_of_bins
        self.method = method
        self.key = key

        self.size = len(data)
        self.min_data = min(data)
        self.max_data = max(data)
        self.bin_width = self._calculate_bin_width()

        self.x_axis = self._calculate_x_axis()
        self.y_axis = self._calculate_y_axis()

    def _calculate_bin_width(self):
        """Calculate the bin width using a given number of bins."""
        return (self.max_data - self.min_data) / self.number_of_bins

    def _calculate_x_axis(self):
        """Return a list with the values of the x axis."""
        return [self.min_data + (self.bin_width * i)
                for i in range(1, self.number_of_bins + 1)]

    def _calculate_y_axis(self):
        """Return a list with the values of the y axis."""
        y_axis = [0] * len(self.x_axis)
        for data_point in self.data:
            for i, bin in enumerate(self.x_axis):
                if data_point <= bin:
                    y_axis[i] += 1
                    break
        return y_axis


def calculate_number_of_bins_sqrt(data):
    """Calculate the number of bins using the square root formula."""
    return int(math.ceil(math.sqrt(len(data))))


def calculate_number_of_bins_sturges(data):
    """Calculate the number of bins using Sturges formula."""
    return int(math.ceil(math.log(len(data), 2) + 1))


def calculate_number_of_bins_rice(data):
    """Calculate the number of bins using the Rice rule."""
    return int(math.ceil(2 * len(data) ** (1.0 / 3.0)))


def calculate_number_of_bins_half(data):
    """The number of bins will be the half of the data size."""
    return int(math.ceil(len(data) / 2.0))


def hvariety(data):
    """Describe methods of calculating the number of bins.

    :returns: List of dictionaries, where every dictionary
              describes a method of calculating the number of bins.
    """
    if len(data) == 0:
        raise ValueError("Cannot calculate number of histrogram bins "
                         "for zero length array of data")
    return [
            {
                "method": "Square Root Choice",
                "number_of_bins": calculate_number_of_bins_sqrt(data),
            },
            {
                "method": "Sturges Formula",
                "number_of_bins": calculate_number_of_bins_sturges(data),
            },
            {
                "method": "Rice Rule",
                "number_of_bins": calculate_number_of_bins_rice(data),
            },
            {
                "method": "One Half",
                "number_of_bins": calculate_number_of_bins_half(data),
            }
    ]
