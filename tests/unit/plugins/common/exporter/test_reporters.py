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

import mock

from rally.plugins.common.exporter import reporters
from tests.unit import test

PATH = "rally.plugins.common.exporter.reporters"


def get_tasks_results():
    return [{"created_at": "2017-06-04T05:14:44",
             "updated_at": "2017-06-04T05:15:14",
             "task_uuid": "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8",
             "key": {
                 "kw": {},
                 "pos": 0,
                 "name": "CinderVolumes.list_volumes",
                 "description": "List all volumes."
             },
             "data": {
                 "raw": [],
                 "full_duration": 29.969523191452026,
                 "sla": [],
                 "load_duration": 2.03029203414917,
                 "hooks": []
             },
             "id": 3}]


class OldJSONResultsMixinTestCase(test.TestCase):

    def test__generate_tasks_results(self):

        class DummyReport(reporters.OldJSONResultsMixin):
            def __init__(self, raw_tasks_results):
                self.tasks_results = raw_tasks_results

        reporter = DummyReport(get_tasks_results())
        results = reporter._generate_tasks_results()
        self.assertEqual(
            [
                {
                    "hooks": [],
                    "created_at": "2017-06-04T05:14:44",
                    "load_duration": 2.03029203414917,
                    "result": [],
                    "key": {
                        "kw": {},
                        "pos": 0,
                        "name": "CinderVolumes.list_volumes",
                        "description": "List all volumes."
                    },
                    "full_duration": 29.969523191452026,
                    "sla": []
                }
            ],
            results
        )


class HTMLExporterTestCase(test.TestCase):

    def test_validate(self):
        # nothing should fail
        reporters.HTMLExporter.validate(mock.Mock())
        reporters.HTMLExporter.validate("")
        reporters.HTMLExporter.validate(None)

    def test__generate(self):
        tasks_results = get_tasks_results()
        tasks_results.extend(get_tasks_results())
        reporter = reporters.HTMLExporter(tasks_results, None)
        results = reporter._generate()
        self.assertEqual(
            [
                {
                    "hooks": [],
                    "created_at": "2017-06-04T05:14:44",
                    "load_duration": 2.03029203414917,
                    "result": [],
                    "key": {
                        "kw": {},
                        "pos": 0,
                        "name": "CinderVolumes.list_volumes",
                        "description": "List all volumes."
                    },
                    "full_duration": 29.969523191452026,
                    "sla": []
                },
                {
                    "hooks": [],
                    "created_at": "2017-06-04T05:14:44",
                    "load_duration": 2.03029203414917,
                    "result": [],
                    "key": {
                        "kw": {},
                        "pos": 1,
                        "name": "CinderVolumes.list_volumes",
                        "description": "List all volumes."
                    },
                    "full_duration": 29.969523191452026,
                    "sla": []
                }], results)

    @mock.patch("%s.HTMLExporter._generate" % PATH,
                return_value="task_results")
    @mock.patch("%s.plot.plot" % PATH, return_value="html")
    def test_generate(self, mock_plot, mock__generate):
        reporter = reporters.HTMLExporter([], output_destination=None)
        self.assertEqual({"print": "html"}, reporter.generate())
        mock__generate.assert_called_once_with()
        mock_plot.assert_called_once_with("task_results",
                                          include_libs=False)

        mock__generate.reset_mock()
        mock_plot.reset_mock()
        reporter = reporters.HTMLExporter([], output_destination="path")
        reporter.INCLUDE_LIBS = True
        self.assertEqual({"files": {"path": "html"},
                          "open": "file://" + os.path.abspath("path")},
                         reporter.generate())
        mock__generate.assert_called_once_with()
        mock_plot.assert_called_once_with("task_results",
                                          include_libs=True)


class JUnitXMLExporterTestCase(test.TestCase):
    def test_generate(self):
        content = ("<testsuite errors=\"0\""
                   " failures=\"0\""
                   " name=\"Rally test suite\""
                   " tests=\"1\""
                   " time=\"29.97\">"
                   "<testcase classname=\"CinderVolumes\""
                   " name=\"list_volumes\""
                   " time=\"29.97\" />"
                   "</testsuite>")

        reporter = reporters.JUnitXMLExporter(get_tasks_results(),
                                              output_destination=None)
        self.assertEqual({"print": content}, reporter.generate())

        reporter = reporters.JUnitXMLExporter(get_tasks_results(),
                                              output_destination="path")
        self.assertEqual({"files": {"path": content},
                          "open": "file://" + os.path.abspath("path")},
                         reporter.generate())

    def test_generate_fail(self):
        tasks_results = get_tasks_results()
        tasks_results[0]["data"]["sla"] = [{"success": False,
                                            "detail": "error"}]
        content = ("<testsuite errors=\"0\""
                   " failures=\"1\""
                   " name=\"Rally test suite\""
                   " tests=\"1\""
                   " time=\"29.97\">"
                   "<testcase classname=\"CinderVolumes\""
                   " name=\"list_volumes\""
                   " time=\"29.97\">"
                   "<failure message=\"error\" /></testcase>"
                   "</testsuite>")
        reporter = reporters.JUnitXMLExporter(tasks_results,
                                              output_destination=None)
        self.assertEqual({"print": content}, reporter.generate())
