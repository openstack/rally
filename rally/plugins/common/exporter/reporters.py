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

from rally.common.io import junit
from rally.task import exporter
from rally.task.processing import plot


class OldJSONResultsMixin(object):
    """Generates task report in old JSON format.

    An example of the report (All dates, numbers, names appearing in this
    example are fictitious. Any resemblance to real things is purely
    coincidental):

      .. code-block:: json

      [
          {
              "hooks": [],
              "created_at": "2017-06-04T05:14:44",
              "load_duration": 2.03029203414917,
              "result": [
                  {
                      "timestamp": 1496553301.578394,
                      "error": [],
                      "duration": 1.0232760906219482,
                      "output": {
                          "additive": [],
                          "complete": []
                      },
                      "idle_duration": 0.0,
                      "atomic_actions": [
                          {
                              "finished_at": 1496553302.601537,
                              "started_at": 1496553301.57868,
                              "name": "cinder_v2.list_volumes",
                              "children": []
                          }
                      ]
                  },
                  {
                      "timestamp": 1496553302.608502,
                      "error": [],
                      "duration": 1.0001840591430664,
                      "output": {
                          "additive": [],
                          "complete": []
                      },
                      "idle_duration": 0.0,
                      "atomic_actions": [
                          {
                              "finished_at": 1496553303.608628,
                              "started_at": 1496553302.608545,
                              "name": "cinder_v2.list_volumes",
                              "children": []
                          }
                      ]
                  }
              ],
              "key": {
                  "kw": {
                      "runner": {
                          "type": "constant",
                          "times": 2,
                          "concurrency": 1
                      },
                      "hooks": [],
                      "args": {
                          "detailed": true
                      },
                      "sla": {},
                      "context": {
                          "volumes": {
                              "size": 1,
                              "volumes_per_tenant": 4
                          }
                      }
                  },
                  "pos": 0,
                  "name": "CinderVolumes.list_volumes",
                  "description": "List all volumes."
              },
              "full_duration": 29.969523191452026,
              "sla": []
          }
      ]
    """

    def _generate_tasks_results(self):
        """Prepare raw report."""
        results = [{"key": x["key"], "result": x["data"]["raw"],
                    "sla": x["data"]["sla"],
                    "hooks": x["data"].get("hooks", []),
                    "load_duration": x["data"]["load_duration"],
                    "full_duration": x["data"]["full_duration"],
                    "created_at": x["created_at"]}
                   for x in self.tasks_results]
        return results


@exporter.configure("html")
class HTMLExporter(exporter.TaskExporter, OldJSONResultsMixin):
    """Generates task report in HTML format."""
    INCLUDE_LIBS = False

    @classmethod
    def validate(cls, output_destination):
        """Validate destination of report.

        :param output_destination: Destination of report
        """
        # nothing to check :)
        pass

    def _generate(self):
        results = []
        processed_names = {}
        tasks_results = self._generate_tasks_results()
        for task_result in tasks_results:
            if task_result["key"]["name"] in processed_names:
                processed_names[task_result["key"]["name"]] += 1
                task_result["key"]["pos"] = processed_names[
                    task_result["key"]["name"]]
            else:
                processed_names[task_result["key"]["name"]] = 0
            results.append(task_result)
        return results

    def generate(self):
        results = self._generate()
        report = plot.plot(results,
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
class JUnitXMLExporter(HTMLExporter):
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
        results = self._generate()
        test_suite = junit.JUnit("Rally test suite")
        for result in results:
            if isinstance(result["sla"], list):
                message = ",".join([sla["detail"] for sla in
                                    result["sla"] if not sla["success"]])
            if message:
                outcome = junit.JUnit.FAILURE
            else:
                outcome = junit.JUnit.SUCCESS
            test_suite.add_test(result["key"]["name"],
                                result["full_duration"], outcome, message)
        result = test_suite.to_xml()

        if self.output_destination:
            return {"files": {self.output_destination: result},
                    "open": "file://" + os.path.abspath(
                        self.output_destination)}
        else:
            return {"print": result}
