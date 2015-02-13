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

from rally.common.i18n import _
from rally.common import utils
from rally import consts
from rally import exceptions


class SLAChecker(object):
    """Base SLA checker class."""

    def __init__(self, config):
        self.config = config
        self.sla_criteria = [SLA.get_by_name(name)(criterion_value)
                             for name, criterion_value
                             in config.get("sla", {}).items()]

    def add_iteration(self, iteration):
        """Process the result of a single iteration.

        The call to add_iteration() will return True if all the SLA checks
        passed, and False otherwise.

        :param iteration: iteration result object
        """
        return all([sla.add_iteration(iteration) for sla in self.sla_criteria])

    def results(self):
        return [sla.result() for sla in self.sla_criteria]


@six.add_metaclass(abc.ABCMeta)
class SLA(object):
    """Factory for criteria classes."""

    def __init__(self, criterion_value):
        self.criterion_value = criterion_value
        self.success = True

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
    def get_by_name(name):
        """Returns SLA by name or config option name."""
        for sla in utils.itersubclasses(SLA):
            if name == sla.__name__ or name == sla.OPTION_NAME:
                return sla
        raise exceptions.NoSuchSLA(name=name)

    @abc.abstractmethod
    def add_iteration(self, iteration):
        """Process the result of a single iteration and perform a SLA check.

        The call to add_iteration() will return True if the SLA check passed,
        and False otherwise.

        :param iteration: iteration result object
        :returns: True if the SLA check passed, False otherwise
        """

    def result(self):
        """Returns the SLA result dict corresponding to the current state."""
        return {
            "criterion": self.OPTION_NAME,
            "success": self.success,
            "detail": self.details()
        }

    @abc.abstractmethod
    def details(self):
        """Returns the string describing the current results of the SLA."""

    def status(self):
        """Return "Passed" or "Failed" depending on the current SLA status."""
        return "Passed" if self.success else "Failed"


class FailureRateDeprecated(SLA):
    """[Deprecated] Failure rate in percents."""
    OPTION_NAME = "max_failure_percent"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0, "maximum": 100.0}

    def __init__(self, criterion_value):
        super(FailureRateDeprecated, self).__init__(criterion_value)
        self.errors = 0
        self.total = 0
        self.error_rate = 0.0

    def add_iteration(self, iteration):
        self.total += 1
        if iteration["error"]:
            self.errors += 1
        self.error_rate = self.errors * 100.0 / self.total
        self.success = self.error_rate <= self.criterion_value
        return self.success

    def details(self):
        return (_("Maximum failure rate %s%% <= %s%% - %s") %
                (self.criterion_value, self.error_rate, self.status()))


class FailureRate(SLA):
    """Failure rate minimum and maximum in percents."""
    OPTION_NAME = "failure_rate"
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "min": {"type": "number", "minimum": 0.0, "maximum": 100.0},
            "max": {"type": "number", "minimum": 0.0, "maximum": 100.0}
        }
    }

    def __init__(self, criterion_value):
        super(FailureRate, self).__init__(criterion_value)
        self.min_percent = self.criterion_value.get("min", 0)
        self.max_percent = self.criterion_value.get("max", 100)
        self.errors = 0
        self.total = 0
        self.error_rate = 0.0

    def add_iteration(self, iteration):
        self.total += 1
        if iteration["error"]:
            self.errors += 1
        self.error_rate = self.errors * 100.0 / self.total
        self.success = self.min_percent <= self.error_rate <= self.max_percent
        return self.success

    def details(self):
        return (_("Failure rate criteria %.2f%% <= %.2f%% <= %.2f%% - %s") %
                (self.min_percent, self.error_rate, self.max_percent,
                 self.status()))


class IterationTime(SLA):
    """Maximum time for one iteration in seconds."""
    OPTION_NAME = "max_seconds_per_iteration"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0,
                     "exclusiveMinimum": True}

    def __init__(self, criterion_value):
        super(IterationTime, self).__init__(criterion_value)
        self.max_iteration_time = 0.0

    def add_iteration(self, iteration):
        if iteration["duration"] > self.max_iteration_time:
            self.max_iteration_time = iteration["duration"]
        self.success = self.max_iteration_time <= self.criterion_value
        return self.success

    def details(self):
        return (_("Maximum seconds per iteration %.2fs<= %.2fs - %s") %
                (self.max_iteration_time, self.criterion_value, self.status()))


class MaxAverageDuration(SLA):
    """Maximum average duration of one iteration in seconds."""
    OPTION_NAME = "max_avg_duration"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0,
                     "exclusiveMinimum": True}

    def __init__(self, criterion_value):
        super(MaxAverageDuration, self).__init__(criterion_value)
        self.total_duration = 0.0
        self.iterations = 0
        self.avg = 0.0

    def add_iteration(self, iteration):
        if not iteration.get("error"):
            self.total_duration += iteration["duration"]
            self.iterations += 1
        self.avg = self.total_duration / self.iterations
        self.success = self.avg <= self.criterion_value
        return self.success

    def details(self):
        return (_("Maximum average duration of one iteration %.2fs <= %.2fs - "
                  "%s") % (self.avg, self.criterion_value, self.status()))
