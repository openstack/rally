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


"""
SLA (Service-level agreement) is set of details for determining compliance
with contracted values such as maximum error rate or minimum response time.
"""

import abc

import jsonschema
import six

from rally.benchmark.processing import utils as putils
from rally.common.i18n import _
from rally.common import utils
from rally import exceptions


class SLAResult(object):

    def __init__(self, success=True, msg=None):
        self.success = success
        self.msg = msg


@six.add_metaclass(abc.ABCMeta)
class SLA(object):
    """Factory for criteria classes."""

    @staticmethod
    def validate(config):
        properties = dict([(c.OPTION_NAME, c.CONFIG_SCHEMA)
                           for c in utils.itersubclasses(SLA)])
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        jsonschema.validate(config, schema)

    @staticmethod
    @abc.abstractmethod
    def check(criterion_value, result):
        """Check if task succeeded according to criterion.

        :param criterion_value: Criterion value specified in configuration
        :param result: result object
        :returns: True if success
        """

    @staticmethod
    def check_all(config, result):
        """Check all SLA criteria.

        :param config: sla related config for a task
        :param result: Result of a task
        :returns: A list of sla results
        """

        results = []
        opt_name_map = dict([(c.OPTION_NAME, c)
                             for c in utils.itersubclasses(SLA)])

        for name, criterion in six.iteritems(config.get("sla", {})):
            check_result = opt_name_map[name].check(criterion, result)
            results.append({'criterion': name,
                            'success': check_result.success,
                            'detail': check_result.msg})
        return results

    @staticmethod
    def get_by_name(name):
        """Returns SLA by name or config option name."""
        for sla in utils.itersubclasses(SLA):
            if name == sla.__name__ or name == sla.OPTION_NAME:
                return sla
        raise exceptions.NoSuchSLA(name=name)


class FailureRateDeprecated(SLA):
    """[Deprecated] Failure rate in percents."""
    OPTION_NAME = "max_failure_percent"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0, "maximum": 100.0}

    @staticmethod
    def check(criterion_value, result):
        errors = len(filter(lambda x: x['error'], result))
        error_rate = errors * 100.0 / len(result) if len(result) > 0 else 100.0
        if criterion_value < error_rate:
            success = False
        else:
            success = True
        msg = (_("Maximum failure percent %s%% failures, actually %s%%") %
                (criterion_value * 100.0, error_rate))
        return SLAResult(success, msg)


class FailureRate(SLA):
    """Failure rate minimum and maximum in percents."""
    OPTION_NAME = "failure_rate"
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": utils.JSON_SCHEMA,
        "properties": {
            "min": {"type": "number", "minimum": 0.0, "maximum": 100.0},
            "max": {"type": "number", "minimum": 0.0, "maximum": 100.0}
        }
    }

    @staticmethod
    def check(criterion_value, result):
        min_percent = criterion_value.get("min", 0)
        max_percent = criterion_value.get("max", 100)
        errors = len(filter(lambda x: x['error'], result))
        error_rate = errors * 100.0 / len(result) if len(result) > 0 else 100.0

        success = min_percent <= error_rate <= max_percent

        msg = (_("Maximum failure rate percent %s%% failures, minimum failure "
               "rate percent %s%% failures, actually %s%%") %
               (max_percent, min_percent, error_rate))

        return SLAResult(success, msg)


class IterationTime(SLA):
    """Maximum time for one iteration in seconds."""
    OPTION_NAME = "max_seconds_per_iteration"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0,
                     "exclusiveMinimum": True}

    @staticmethod
    def check(criterion_value, result):
        duration = 0
        success = True
        for i in result:
            if i['duration'] >= duration:
                duration = i['duration']
            if i['duration'] > criterion_value:
                success = False
        msg = (_("Maximum seconds per iteration %ss, found with %ss") %
                (criterion_value, duration))
        return SLAResult(success, msg)


class MaxAverageDuration(SLA):
    """Maximum average duration for one iteration in seconds."""
    OPTION_NAME = "max_avg_duration"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0,
                     "exclusiveMinimum": True}

    @staticmethod
    def check(criterion_value, result):
        durations = [r["duration"] for r in result if not r.get("error")]
        avg = putils.mean(durations)
        success = avg < criterion_value
        msg = (_("Maximum average duration per iteration %ss, found with %ss")
               % (criterion_value, avg))
        return SLAResult(success, msg)
