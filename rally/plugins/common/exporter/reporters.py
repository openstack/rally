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

import itertools
import os

from rally.common.io import junit
from rally.task import exporter
from rally.task.processing import plot


@exporter.configure("html")
class HTMLExporter(exporter.TaskExporter):
    """Generates task report in HTML format."""
    INCLUDE_LIBS = False

    def _generate_results(self):
        results = []
        processed_names = {}
        for task in self.tasks_results:
            for workload in itertools.chain(
                    *[s["workloads"] for s in task["subtasks"]]):
                if workload["name"] in processed_names:
                    processed_names[workload["name"]] += 1
                    workload["position"] = processed_names[workload["name"]]
                else:
                    processed_names[workload["name"]] = 0
            results.append(task)
        return results

    def generate(self):
        report = plot.plot(self._generate_results(),
                           include_libs=self.INCLUDE_LIBS)

        if self.output_destination:
            return {"files": {self.output_destination: report},
                    "open": "file://" + os.path.abspath(
                        self.output_destination)}
        else:
            return {"print": report}


@exporter.configure("html-static")
class HTMLStaticExporter(HTMLExporter):
    """Generates task report in HTML format with embedded JS/CSS."""
    INCLUDE_LIBS = True


@exporter.configure("junit-xml")
class JUnitXMLExporter(exporter.TaskExporter):
    """Generates task report in JUnit-XML format.

    An example of the report (All dates, numbers, names appearing in this
    example are fictitious. Any resemblance to real things is purely
    coincidental):

      .. code-block:: xml

      <testsuite errors="0"
                 failures="0"
                 name="Rally test suite"
                 tests="1"
                 time="29.97">
        <testcase classname="CinderVolumes"
                  name="list_volumes"
                  time="29.97" />
      </testsuite>
    """

    def generate(self):
        test_suite = junit.JUnit("Rally test suite")
        for task in self.tasks_results:
            for workload in itertools.chain(
                    *[s["workloads"] for s in task["subtasks"]]):
                w_sla = workload["sla_results"].get("sla", [])

                message = ",".join([sla["detail"] for sla in w_sla
                                    if not sla["success"]])
                if message:
                    outcome = junit.JUnit.FAILURE
                else:
                    outcome = junit.JUnit.SUCCESS
                test_suite.add_test(workload["name"],
                                    workload["full_duration"], outcome,
                                    message)

        result = test_suite.to_xml()

        if self.output_destination:
            return {"files": {self.output_destination: result},
                    "open": "file://" + os.path.abspath(
                        self.output_destination)}
        else:
            return {"print": result}
