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
from rally import exceptions


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
        self.aborted = False
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
        results = [sla.result() for sla in self.sla_criteria]
        if self.aborted:
            results.append(_format_result(
                "aborted_on_sla", False,
                _("Task was aborted due to SLA failure(s).")))
        if self.unexpected_failure:
            results.append(_format_result(
                "something_went_wrong", False,
                _("Unexpected error: %s") % self.unexpected_failure))
        return results

    def set_aborted(self):
        self.aborted = True

    def set_unexpected_failure(self, exc):
        self.unexpected_failure = exc


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
        return _format_result(self.OPTION_NAME, self.success, self.details())

    @abc.abstractmethod
    def details(self):
        """Returns the string describing the current results of the SLA."""

    def status(self):
        """Return "Passed" or "Failed" depending on the current SLA status."""
        return "Passed" if self.success else "Failed"
