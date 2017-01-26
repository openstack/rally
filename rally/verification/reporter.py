# Copyright 2016: Mirantis Inc.
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
Reporter - its the mechanism for exporting rally verification into specified
system or formats.
"""

import abc

import jsonschema
import six

from rally.common.plugin import plugin
from rally import consts


configure = plugin.configure


REPORT_RESPONSE_SCHEMA = {
    "type": "object",
    "$schema": consts.JSON_SCHEMA,
    "properties": {
        "files": {
            "type": "object",
            "patternProperties": {
                ".{1,}": {"type": "string"}
            }
        },
        "open": {
            "type": "string",
        },
        "print": {
            "type": "string"
        }
    },
    "additionalProperties": False
}


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class VerificationReporter(plugin.Plugin):
    """Base class for all reporters for verifications."""

    def __init__(self, verifications, output_destination):
        """Init reporter

        :param verifications: list of results to generate report for
        :param output_destination: destination of report
        """
        super(VerificationReporter, self).__init__()
        self.verifications = verifications
        self.output_destination = output_destination

    @classmethod
    @abc.abstractmethod
    def validate(cls, output_destination):
        """Validate destination of report.

        :param output_destination: Destination of report
        """

    @abc.abstractmethod
    def generate(self):
        """Generate report

        :returns: a dict with 3 optional elements:

            - key "files" with a dictionary of files to save on disk.
              keys are paths, values are contents;
            - key "print" - data to print at CLI level
            - key "open" - path to file which should be open in case of
              --open flag
        """

    @staticmethod
    def make(reporter_cls, verifications, output_destination):
        """Initialize reporter, generate and validate report.

        It is a base method which is called from API layer. It cannot be
        overridden. Do not even try! :)

        :param reporter_cls: class of VerificationReporter to be used
        :param verifications: list of results to generate report for
        :param output_destination: destination of report
        """
        report = reporter_cls(verifications, output_destination).generate()

        jsonschema.validate(report, REPORT_RESPONSE_SCHEMA)

        return report
