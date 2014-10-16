# Copyright 2014: Mirantis Inc.
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

import mock

from rally.benchmark.processing import plot
from tests.unit import test


class PlotTestCase(test.TestCase):
    @mock.patch("rally.benchmark.processing.plot.open", create=True)
    @mock.patch("rally.benchmark.processing.plot.mako.template.Template")
    @mock.patch("rally.benchmark.processing.plot.os.path.dirname")
    @mock.patch("rally.benchmark.processing.plot._process_results")
    def test_plot(self, mock_proc_results, mock_dirname, mock_template,
                  mock_open):
        mock_dirname.return_value = "abspath"
        mock_open.return_value = mock_open
        mock_open.__enter__.return_value = mock_open
        mock_open.read.return_value = "some_template"

        templ = mock.MagicMock()
        templ.render.return_value = "output"
        mock_template.return_value = templ
        mock_proc_results.return_value = [{"name": "a"}, {"name": "b"}]

        result = plot.plot(["abc"])

        self.assertEqual(result, templ.render.return_value)
        templ.render.assert_called_once_with(
            data=json.dumps(mock_proc_results.return_value)
        )
        mock_template.assert_called_once_with(mock_open.read.return_value)
        mock_open.assert_called_once_with("%s/src/index.mako"
                                          % mock_dirname.return_value)

    @mock.patch("rally.benchmark.processing.plot._prepare_data")
    @mock.patch("rally.benchmark.processing.plot._process_atomic")
    @mock.patch("rally.benchmark.processing.plot._process_main_duration")
    def test__process_results(self, mock_main_duration, mock_atomic,
                              mock_prepare):
        results = [
            {"key": {"name": "Klass.method_foo", "pos": 0, "kw": "config1"}},
            {"key": {"name": "Klass.method_foo", "pos": 1, "kw": "config2"}},
            {"key": {"name": "Klass.method_bar", "pos": 0, "kw": "config3"}}
        ]
        table_cols = ["action",
                      "min (sec)",
                      "avg (sec)",
                      "max (sec)",
                      "90 percentile",
                      "95 percentile",
                      "success",
                      "count"]

        mock_main_duration.return_value = "main_duration"
        mock_atomic.return_value = "main_atomic"

        output = plot._process_results(results)

        results = sorted(results, key=lambda r: "%s%s" % (r["key"]["name"],
                                                          r["key"]["pos"]))

        for i, r in enumerate(results):
            config = json.dumps({r["key"]["name"]: r["key"]["kw"]}, indent=2)
            pos = int(r["key"]["pos"])
            cls = r["key"]["name"].split(".")[0]
            met = r["key"]["name"].split(".")[1]
            name = "%s%s" % (met, (pos and " [%d]" % (pos + 1) or ""))
            self.assertEqual(output[i], {
                "cls": cls,
                "pos": r["key"]["pos"],
                "met": met,
                "name": name,
                "config": config,
                "duration": mock_main_duration.return_value,
                "atomic": mock_atomic.return_value,
                "table_cols": table_cols,
                "table_rows": [['total', None, None, None, None, None, 0, 0]]
            })

    def test__process_main_time(self):
        result = {
            "result": [
                {
                    "error": [],
                    "duration": 1,
                    "idle_duration": 2,
                    "atomic_actions": {}
                },
                {
                    "error": True,
                    "duration": 1,
                    "idle_duration": 1,
                    "atomic_actions": {}
                },
                {
                    "error": [],
                    "duration": 2,
                    "idle_duration": 3,
                    "atomic_actions": {}
                }
            ]
        }

        output = plot._process_main_duration(result,
                                             plot._prepare_data(result))

        self.assertEqual(output, {
            "pie": [
                {"key": "success", "value": 2},
                {"key": "errors", "value": 1}
            ],
            "iter": [
                {
                    "key": "duration",
                    "values": [(1, 1.0), (2, 1.0), (3, 2.0)]
                },
                {
                    "key": "idle_duration",
                    "values": [(1, 2.0), (2, 1.0), (3, 3.0)]
                }
            ],
            "histogram": [
                {
                    "key": "task",
                    "method": "Square Root Choice",
                    "values": [{"x": 1.0, "y": 1.0}, {"x": 1.0, "y": 0.0}]
                },
                {
                    "key": "task",
                    "method": "Sturges Formula",
                    "values": [{"x": 1.0, "y": 1.0}, {"x": 1.0, "y": 0.0}]
                },
                {
                    "key": "task",
                    "method": "Rice Rule",
                    "values": [{"x": 1.0, "y": 1.0}, {"x": 1.0, "y": 0.0},
                               {"x": 1.0, "y": 0.0}]
                },
                {
                    "key": "task",
                    "method": "One Half",
                    "values": [{"x": 2.0, "y": 2.0}]
                }
            ]
        })

    def test__process_atomic_time(self):
        result = {
            "result": [
                {
                    "error": [],
                    "atomic_actions": {
                        "action1": 1,
                        "action2": 2
                    }
                },
                {
                    "error": ["some", "error", "occurred"],
                    "atomic_actions": {
                        "action1": 1,
                        "action2": 2
                    }
                },
                {
                    "error": [],
                    "atomic_actions": {
                        "action1": 3,
                        "action2": 4
                    }
                }
            ]
        }

        data = {"atomic_durations": {
            "action1": [(1, 1.0), (2, 0.0), (3, 3.0)],
            "action2": [(1, 2.0), (2, 0.0), (3, 4.0)]}}

        output = plot._process_atomic(result, data)

        self.assertEqual(output, {
            "histogram": [
                [
                    {
                        "key": "action1",
                        "disabled": 0,
                        "method": "Square Root Choice",
                        "values": [{"x": 2, "y": 1}, {"x": 3, "y": 1}]
                    },
                    {
                        "key": "action1",
                        "disabled": 0,
                        "method": "Sturges Formula",
                        "values": [{"x": 2, "y": 1}, {"x": 3, "y": 1}]
                    },
                    {
                        "key": "action1",
                        "disabled": 0,
                        "method": "Rice Rule",
                        "values": [{"x": 1, "y": 1}, {"x": 1, "y": 0},
                                   {"x": 1, "y": 0}]
                    },
                    {
                        "key": "action1",
                        "disabled": 0,
                        "method": "One Half",
                        "values": [{"x": 3, "y": 2}]
                    },
                ],
                [
                    {
                        "key": "action2",
                        "disabled": 1,
                        "method": "Square Root Choice",
                        "values": [{"x": 3, "y": 1}, {"x": 4, "y": 1}]
                    },
                    {
                        "key": "action2",
                        "disabled": 1,
                        "method": "Sturges Formula",
                        "values": [{"x": 3, "y": 1}, {"x": 4, "y": 1}]
                    },
                    {
                        "key": "action2",
                        "disabled": 1,
                        "method": "Rice Rule",
                        "values": [{"x": 2, "y": 1}, {"x": 2, "y": 0},
                                   {"x": 2, "y": 0}]
                    },
                    {
                        "key": "action2",
                        "disabled": 1,
                        "method": "One Half",
                        "values": [{"x": 4, "y": 2}]
                    }
                ]
            ],
            "pie": [
                {"key": "action1", "value": 2.0},
                {"key": "action2", "value": 3.0}
            ],
            "iter": [
                {
                    "key": "action1",
                    "values": [(1, 1), (2, 0), (3, 3)]
                },
                {
                    "key": "action2",
                    "values": [(1, 2), (2, 0), (3, 4)]
                }
            ]
        })

    @mock.patch("rally.benchmark.processing.utils.compress")
    def test__prepare_data(self, mock_compress):

        mock_compress.side_effect = lambda i, **kv: i
        rows_range = 100
        limit = 10

        data = []
        for i in range(rows_range):
            atomic_actions = {
                "a1": i + 0.1,
                "a2": i + 0.8,
            }
            row = {
                "duration": i * 3.1,
                "idle_duration": i * 0.2,
                "error": [],
                "atomic_actions": atomic_actions,
            }
            data.append(row)

        data[42]["error"] = "foo error"
        data[52]["error"] = "bar error"

        values_atomic_a1 = [i + 0.1 for i in range(rows_range)]
        values_atomic_a2 = [i + 0.8 for i in range(rows_range)]
        values_duration = [i * 3.1 for i in range(rows_range)]
        values_idle = [i * 0.2 for i in range(rows_range)]
        num_errors = 2

        prepared_data = plot._prepare_data({"result": data},
                                           reduce_rows=limit)
        self.assertEqual(num_errors, prepared_data["num_errors"])

        calls = [mock.call(values_atomic_a1, limit=limit),
                 mock.call(values_atomic_a2, limit=limit),
                 mock.call(values_duration, limit=limit),
                 mock.call(values_idle, limit=limit)]
        mock_compress.assert_has_calls(calls)

        self.assertEqual({
            "total_durations": {"duration": values_duration,
                                "idle_duration": values_idle},
            "atomic_durations": {"a1": values_atomic_a1,
                                 "a2": values_atomic_a2},
            "num_errors": num_errors
        }, prepared_data)
