# Copyright 2018: ZTE Inc.
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

import os

from rally.task import exporter
from rally.task.processing import plot


@exporter.configure("trends-html")
class TrendsExporter(exporter.TaskExporter):
    """Generates task trends report in HTML format."""
    INCLUDE_LIBS = False

    def generate(self):
        report = plot.trends(self.tasks_results, self.INCLUDE_LIBS)
        if self.output_destination:
            return {"files": {self.output_destination: report},
                    "open": "file://" + os.path.abspath(
                        self.output_destination)}
        else:
            return {"print": report}


@exporter.configure("trends-html-static")
class TrendsStaticExport(TrendsExporter):
    """Generates task trends report in HTML format with embedded JS/CSS."""
    INCLUDE_LIBS = True
