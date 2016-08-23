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

import six

from rally.common.plugin import plugin


configure = plugin.configure


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Exporter(plugin.Plugin):

    def __init__(self, connection_string):
        self.connection_string = connection_string

    @abc.abstractmethod
    def export(self, task_uuid):
        """Export results of the task to the task storage.

        :param task_uuid: uuid of task results
        """

    @abc.abstractmethod
    def validate(self):
        """Used to validate connection string."""

TaskExporter = Exporter
