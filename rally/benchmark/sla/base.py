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

from rally import utils


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
    def check_all(task):
        """Check all SLA criteria.

        :param task: Task object
        :returns: Generator
        """

        opt_name_map = dict([(c.OPTION_NAME, c)
                             for c in utils.itersubclasses(SLA)])

        for result in task.results:
            config = result['key']['kw'].get('sla', None)
            if config:
                for name, criterion in config.iteritems():
                    success = opt_name_map[name].check(criterion, result)
                    yield {'benchmark': result['key']['name'],
                           'pos': result['key']['pos'],
                           'criterion': name,
                           'success': success}


class FailureRate(SLA):
    """Failure rate in percents."""
    OPTION_NAME = "max_failure_percent"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0, "maximum": 100.0}

    @staticmethod
    def check(criterion_value, result):
        raw = result['data']['raw']
        errors = len(filter(lambda x: x['error'], raw))
        if criterion_value < errors * 100.0 / len(raw):
            return False
        return True


class IterationTime(SLA):
    """Maximum time for one iteration in seconds."""
    OPTION_NAME = "max_seconds_per_iteration"
    CONFIG_SCHEMA = {"type": "number", "minimum": 0.0,
                     "exclusuveMinimum": True}

    @staticmethod
    def check(criterion_value, result):
        for i in result['data']['raw']:
            if i['duration'] > criterion_value:
                return False
        return True
