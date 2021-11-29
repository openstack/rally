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

import collections
from unittest import mock

from rally import exceptions
from rally.plugins.task.exporters import old_json_results
from tests.unit.plugins.task.exporters import dummy_data
from tests.unit import test

PATH = "rally.plugins.task.exporters.old_json_results"


class OldJSONResultsTestCase(test.TestCase):

    def test___init__(self):
        old_json_results.OldJSONExporter([1], None)

        self.assertRaises(
            exceptions.RallyException,
            old_json_results.OldJSONExporter, [1, 2], None
        )

    @mock.patch("%s.json.dumps" % PATH, return_value="json")
    def test_generate(self, mock_json_dumps):
        tasks_results = dummy_data.get_tasks_results()

        # print
        exporter = old_json_results.OldJSONExporter(tasks_results, None)
        exporter._get_report = mock.MagicMock()

        self.assertEqual({"print": "json"}, exporter.generate())

        exporter._get_report.assert_called_once_with()
        mock_json_dumps.assert_called_once_with(
            exporter._get_report.return_value, sort_keys=False, indent=4)

        # export to file
        exporter = old_json_results.OldJSONExporter(
            tasks_results, output_destination="path")
        exporter._get_report = mock.MagicMock()
        self.assertEqual({"files": {"path": "json"},
                          "open": "file://path"}, exporter.generate())

    def test__get_report(self):
        tasks_results = dummy_data.get_tasks_results()
        exporter = old_json_results.OldJSONExporter(tasks_results, None)

        self.assertEqual(
            [
                {
                    "created_at": "2017-04-06T05:14:44",
                    "full_duration": 29.969523191452026,
                    "hooks": [],
                    "key": {
                        "description": "List all volumes.",
                        "kw": {"args": {},
                               "context": {},
                               "hooks": [],
                               "runner": {"type": "runner_type"},
                               "sla": {}},
                        "name": "CinderVolumes.list_volumes",
                        "pos": 0
                    },
                    "load_duration": 2.03029203414917,
                    "result": [
                        {
                            "atomic_actions": collections.OrderedDict([
                                ("foo", 0.250424861907959)]),
                            "duration": 0.2504892349243164,
                            "error": [],
                            "idle_duration": 0.0,
                            "output": {"additive": [], "complete": []},
                            "timestamp": 1584551892.7336202
                        },
                        {
                            "atomic_actions": collections.OrderedDict([
                                ("foo", 0.250380277633667)]),
                            "duration": 0.25043749809265137,
                            "error": [],
                            "idle_duration": 0.0,
                            "output": {"additive": [], "complete": []},
                            "timestamp": 1584551892.7363858}],
                    "sla": []
                }
            ], exporter._get_report())

    def test__to_old_atomic_actions_format(self):
        actions = [
            {
                "name": "foo",
                "started_at": 0,
                "finished_at": 1,
                "children": []
            },
            {
                "name": "foo",
                "started_at": 1,
                "finished_at": 2,
                "children": []
            },
            {
                "name": "foo",
                "started_at": 2,
                "finished_at": 3,
                "children": []
            },
            {
                "name": "bar",
                "started_at": 3,
                "finished_at": 5,
                "children": [
                    {
                        "name": "xxx",
                        "started_at": 3,
                        "finished_at": 4,
                        "children": []
                    },
                    {
                        "name": "xxx",
                        "started_at": 4,
                        "finished_at": 5,
                        "children": []
                    }
                ]
            }
        ]

        actual = old_json_results._to_old_atomic_actions_format(actions)
        self.assertIsInstance(actual, collections.OrderedDict)
        # it is easier to compare list instead of constructing an ordered dict
        actual = list(actual.items())
        self.assertEqual(
            [("foo", 1), ("foo (2)", 1), ("foo (3)", 1), ("bar", 2)],
            actual
        )
