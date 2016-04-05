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


import json
import os

from six.moves.urllib import parse as urlparse

from rally import api
from rally.common import logging
from rally import exceptions
from rally.task import exporter


LOG = logging.getLogger(__name__)


@exporter.configure(name="file")
class FileExporter(exporter.Exporter):

    def validate(self):
        """Validate connection string.

        The format of connection string in file plugin is
            file:///<path>.<type-of-output>
        """

        parse_obj = urlparse.urlparse(self.connection_string)

        available_formats = ("json",)
        available_formats_str = ", ".join(available_formats)
        if self.connection_string is None or parse_obj.path == "":
            raise exceptions.InvalidConnectionString(
                "It should be `file:///<path>.<type-of-output>`.")
        if self.type not in available_formats:
            raise exceptions.InvalidConnectionString(
                "Type of the exported task is not available. The available "
                "formats are %s." %
                available_formats_str)

    def __init__(self, connection_string):
        super(FileExporter, self).__init__(connection_string)
        self.path = os.path.expanduser(urlparse.urlparse(
            connection_string).path[1:])
        self.type = connection_string.split(".")[-1]
        self.validate()

    def export(self, uuid):
        """Export results of the task to the file.

        :param uuid: uuid of the task object
        """
        task = api.Task.get(uuid)

        LOG.debug("Got the task object by it's uuid %s. " % uuid)

        task_results = [{"key": x["key"], "result": x["data"]["raw"],
                         "sla": x["data"]["sla"],
                         "load_duration": x["data"]["load_duration"],
                         "full_duration": x["data"]["full_duration"]}
                        for x in task.get_results()]

        if self.type == "json":
            if task_results:
                res = json.dumps(task_results, sort_keys=True, indent=4)
                LOG.debug("Got the task %s results." % uuid)
            else:
                msg = ("Task %s results would be available when it will "
                       "finish." % uuid)
                raise exceptions.RallyException(msg)

        if os.path.dirname(self.path) and (not os.path.exists(os.path.dirname(
                self.path))):
            raise IOError("There is no such directory: %s" %
                          os.path.dirname(self.path))
        with open(self.path, "w") as f:
            LOG.debug("Writing task %s results to the %s." % (
                uuid, self.connection_string))
            f.write(res)
            LOG.debug("Task %s results was written to the %s." % (
                uuid, self.connection_string))


@exporter.configure(name="file-exporter")
class DeprecatedFileExporter(FileExporter):
    """DEPRECATED."""
    def __init__(self, connection_string):
        super(DeprecatedFileExporter, self).__init__(connection_string)
        import warnings
        warnings.warn("'file-exporter' plugin is deprecated. Use 'file' "
                      "instead.")
