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
Exporter - its the mechanism for exporting rally tasks into some specified
system by connection string.
"""

import abc

import jsonschema
import six

from rally.common import logging
from rally.common.plugin import plugin
from rally.common import validation
from rally import consts


LOG = logging.getLogger(__name__)

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
class TaskExporter(plugin.Plugin, validation.ValidatablePluginMixin):
    """Plugin base for exporting tasks results to different systems&formats.

    This type of plugins is designed to provide the way to present results in
    different formats and send them to the different systems.

    To discover available plugins, call
      ``rally plugin list --plugin-base TaskExporter``.

    To export results of a task, call
      ``rally task export --uuid <task-uuid> --type <plugin-name> --to <dest>``

    """

    def __init__(self, tasks_results, output_destination, api=None):
        """Init reporter

        :param tasks_results: list of results to generate report for
        :param output_destination: destination of export
        :param api: an instance of rally.api.API object
        """
        super(TaskExporter, self).__init__()
        self.tasks_results = tasks_results
        self.output_destination = output_destination
        self.api = api

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
    def make(exporter_cls, task_results, output_destination, api=None):
        """Initialize exporter, generate and validate result.

        It is a base method which is called from API layer. It cannot be
        overridden. Do not even try! :)

        :param exporter_cls: class of TaskExporter to be used
        :param task_results: list of results to generate report for
        :param output_destination: destination of export
        :param api: an instance of rally.api.API object
        """
        report = exporter_cls(task_results, output_destination,
                              api).generate()

        jsonschema.validate(report, REPORT_RESPONSE_SCHEMA)

        return report
