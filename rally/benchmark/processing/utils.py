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
                                        "the list should be non-empty")
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
    actions_data = {}
    for atomic_action in atomic_actions:
        actions_data[atomic_action] = [
            r["atomic_actions"][atomic_action]
            for r in raw_data
            if r["atomic_actions"].get(atomic_action) is not None]
    actions_data["total"] = [r["duration"] for r in raw_data if not r["error"]]
    return actions_data


def compress(data, limit=1000, merge=None, normalize=None):
    """Enumerate and reduce list of values.

    :param data: data list
    :param limit: int, max length of result list
    :param merge: function that merges two values
    :param normalize: function that guarantees sanity of value
    :returns: items list [(idx1, value1), (idx2, value2) ...]
    """

    if not normalize:
        normalize = lambda i: i and round(float(i), 2) or 0.0

    if not merge:
        merge = lambda a, b: normalize((a + normalize(b)) / 2)

    if len(data) <= limit:
        return [(idx, normalize(v)) for idx, v in enumerate(data, start=1)]

    # For determining which rows should be merged we are using `factor'
    # e.g. if we have 100 rows and should reduce it to 75 then we have
    # factor of 0.25 and delete (merge with previous) each 4th row.
    factor = float(limit) / len(data)
    store = 0.0

    result = []
    first = True

    for idx, value in enumerate(data, start=1):
        store += factor

        if first:
            cur_value = normalize(value)
            first = False
        else:
            cur_value = merge(cur_value, value)

        if store > 1:
            store -= 1
            first = True
            result.append((idx, cur_value))

    if not first:
        result.append((len(data), cur_value))

    return result
