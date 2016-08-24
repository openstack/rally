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
class VerifyExporter(plugin.Plugin):

    @abc.abstractmethod
    def export(self, verification_uuid, connection_string):
        """Export results of the task to the task storage.

        :param verification_uuid: uuid of verification results
        :param connection_string: string used to connect
                                  to the external system
        """
