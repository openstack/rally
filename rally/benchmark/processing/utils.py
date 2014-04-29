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

from rally import exceptions


def mean(values):
    """Find the simple average of a list of values.

    :parameter values: non-empty list of numbers

    :returns: float value
    """
    if not values:
        raise exceptions.InvalidArgumentsException(
                                        message="the list should be non-empty")
    return math.fsum(values) / len(values)


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


def get_durations(raw_data, get_duration, is_successful):
    """Retrieve the benchmark duration data from a list of records.

    :parameter raw_data: list of records
    :parameter get_duration: function that retrieves the duration data from
                             a given record
    :parameter is_successful: function that returns True if the record contains
                              a successful benchmark result, False otherwise

    :returns: list of float values corresponding to benchmark durations
    """
    data = [get_duration(run) for run in raw_data if is_successful(run)]
    return data
