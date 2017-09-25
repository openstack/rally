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

import six

from rally.common.plugin import plugin
from rally.common import validation


configure = plugin.configure


def _format_result(criterion_name, success, detail):
    """Returns the SLA result dict corresponding to the current state."""
    return {"criterion": criterion_name,
            "success": success,
            "detail": detail}


class SLAChecker(object):
    """Base SLA checker class."""

    def __init__(self, config):
        self.config = config
        self.unexpected_failure = None
        self.aborted_on_sla = False
        self.aborted_manually = False
        self.sla_criteria = [SLA.get(name)(criterion_value)
                             for name, criterion_value
                             in config.get("sla", {}).items()]

    def add_iteration(self, iteration):
        """Process the result of a single iteration.

        The call to add_iteration() will return True if all the SLA checks
        passed, and False otherwise.

        :param iteration: iteration result object
        """
        return all([sla.add_iteration(iteration) for sla in self.sla_criteria])

    def merge(self, other):
        self._validate_config(other)
        self._validate_sla_types(other)

        return all([self_sla.merge(other_sla)
                    for self_sla, other_sla
                    in six.moves.zip(
                        self.sla_criteria, other.sla_criteria)])

    def _validate_sla_types(self, other):
        for self_sla, other_sla in six.moves.zip_longest(
                self.sla_criteria, other.sla_criteria):
            self_sla.validate_type(other_sla)

    def _validate_config(self, other):
        self_config = self.config.get("sla", {})
        other_config = other.config.get("sla", {})
        if self_config != other_config:
            raise TypeError(
                "Error merging SLACheckers with configs %s, %s. "
                "Only SLACheckers with the same config could be merged."
                % (self_config, other_config))

    def results(self):
        results = [sla.result() for sla in self.sla_criteria]
        if self.aborted_on_sla:
            results.append(_format_result(
                "aborted_on_sla", False,
                "Task was aborted due to SLA failure(s)."))

        if self.aborted_manually:
            results.append(_format_result(
                "aborted_manually", False,
                "Task was aborted due to abort signal."))

        if self.unexpected_failure:
            results.append(_format_result(
                "something_went_wrong", False,
                "Unexpected error: %s" % self.unexpected_failure))

        return results

    def set_aborted_on_sla(self):
        self.aborted_on_sla = True

    def set_aborted_manually(self):
        self.aborted_manually = True

    def set_unexpected_failure(self, exc):
        self.unexpected_failure = exc


@validation.add_default("jsonschema")
@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class SLA(plugin.Plugin, validation.ValidatablePluginMixin):
    """Factory for criteria classes."""

    CONFIG_SCHEMA = {"type": "null"}

    def __init__(self, criterion_value):
        self.criterion_value = criterion_value
        self.success = True

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
        return _format_result(self.get_name(), self.success, self.details())

    @abc.abstractmethod
    def details(self):
        """Returns the string describing the current results of the SLA."""

    def status(self):
        """Return "Passed" or "Failed" depending on the current SLA status."""
        return "Passed" if self.success else "Failed"

    @abc.abstractmethod
    def merge(self, other):
        """Merge aggregated data from another SLA instance into self.

        Process the results of several iterations aggregated in another
        instance of SLA together with ones stored in self so that the
        code

            sla1 = SLA()
            sla1.add_iteration(a)
            sla1.add_iteration(b)

            sla2 = SLA()
            sla2.add_iteration(c)
            sla2.add_iteration(d)

            sla1.merge(sla2)

        is equivalent to

            sla1 = SLA()
            sla1.add_iteration(a)
            sla1.add_iteration(b)
            sla1.add_iteration(c)
            sla1.add_iteration(d)

        The call to merge() will return True if the SLA check
        passed, and False otherwise.

        :param other: another SLA object
        :returns: True if the SLA check passed, False otherwise
        """

    def validate_type(self, other):
        if type(self) != type(other):
            raise TypeError(
                "Error merging SLAs of types %s, %s. Only SLAs of the same "
                "type could be merged." % (type(self), type(other)))
