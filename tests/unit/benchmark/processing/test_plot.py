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
    @mock.patch("rally.benchmark.processing.plot.ui_utils")
    @mock.patch("rally.benchmark.processing.plot._process_results")
    def test_plot(self, mock_proc_results, mock_utils):
        mock_render = mock.Mock(return_value="plot_html")
        mock_utils.get_template = mock.Mock(
            return_value=mock.Mock(render=mock_render))

        mock_proc_results.return_value = [{"name": "a"}, {"name": "b"}]

        result = plot.plot(["abc"])

        self.assertEqual(result, "plot_html")
        mock_render.assert_called_once_with(
            data=json.dumps(mock_proc_results.return_value)
        )
        mock_utils.get_template.assert_called_once_with("task/report.mako")

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
        table_cols = ["Action",
                      "Min (sec)",
                      "Avg (sec)",
                      "Max (sec)",
                      "90 percentile",
                      "95 percentile",
                      "Success",
                      "Count"]

        mock_prepare.side_effect = lambda i: {"errors": "errors_list",
                                              "output": [],
                                              "output_errors": [],
                                              "sla": "foo_sla",
                                              "duration": 12345.67}
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
                "table_rows": [["total", None, None, None, None, None, 0, 0]],
                "errors": "errors_list",
                "output": [],
                "output_errors": [],
                "sla": "foo_sla",
                "total_duration": 12345.67
            })

    def test__process_main_time(self):
        result = {
            "result": [
                {
                    "error": [],
                    "duration": 1,
                    "idle_duration": 2,
                    "atomic_actions": {},
                    "scenario_output": {"errors": [], "data": {}}
                },
                {
                    "error": ["some", "error", "occurred"],
                    "duration": 1,
                    "idle_duration": 1,
                    "atomic_actions": {},
                    "scenario_output": {"errors": [], "data": {}}
                },
                {
                    "error": [],
                    "duration": 2,
                    "idle_duration": 3,
                    "atomic_actions": {},
                    "scenario_output": {"errors": [], "data": {}}
                }
            ],
            "sla": "foo_sla",
            "duration": 12345.67
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
                    },
                    "scenario_output": {"errors": [], "data": {}}
                },
                {
                    "error": ["some", "error", "occurred"],
                    "atomic_actions": {
                        "action1": 1,
                        "action2": 2
                    },
                    "scenario_output": {"errors": [], "data": {}}
                },
                {
                    "error": [],
                    "atomic_actions": {
                        "action1": 3,
                        "action2": 4
                    },
                    "scenario_output": {"errors": [], "data": {}}
                }
            ]
        }

        data = {
            "atomic_durations": {
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
        rows_num = 100
        total_duration = 12345.67
        sla = [{"foo": "bar"}]
        data = []
        for i in range(rows_num):
            atomic_actions = {
                "a1": i + 0.1,
                "a2": i + 0.8,
            }
            row = {
                "duration": i * 3.1,
                "idle_duration": i * 0.2,
                "error": [],
                "atomic_actions": atomic_actions,
                "scenario_output": {"errors": ["err"],
                                    "data": {"out_key": "out_value"}}
            }
            data.append(row)

        data[42]["error"] = ["foo", "bar", "spam"]
        data[52]["error"] = ["spam", "bar", "foo"]

        values_atomic_a1 = [i + 0.1 for i in range(rows_num)]
        values_atomic_a2 = [i + 0.8 for i in range(rows_num)]
        values_duration = [i * 3.1 for i in range(rows_num)]
        values_idle = [i * 0.2 for i in range(rows_num)]

        prepared_data = plot._prepare_data({"result": data,
                                            "duration": total_duration,
                                            "sla": sla,
                                            "key": "foo_key"})
        self.assertEqual(2, len(prepared_data["errors"]))

        calls = [mock.call(values_atomic_a1),
                 mock.call(values_atomic_a2),
                 mock.call(values_duration),
                 mock.call(values_idle)]
        mock_compress.assert_has_calls(calls)

        expected_output = [{"key": "out_key",
                            "values": ["out_value"] * rows_num}]
        expected_output_errors = [(i, [e])
                                  for i, e in enumerate(["err"] * rows_num)]
        self.assertEqual({
            "total_durations": {"duration": values_duration,
                                "idle_duration": values_idle},
            "atomic_durations": {"a1": values_atomic_a1,
                                 "a2": values_atomic_a2},
            "errors": [{"iteration": 42,
                        "message": "bar",
                        "traceback": "spam",
                        "type": "foo"},
                       {"iteration": 52,
                        "message": "bar",
                        "traceback": "foo",
                        "type": "spam"}],
            "output": expected_output,
            "output_errors": expected_output_errors,
            "duration": total_duration,
            "sla": sla,
        }, prepared_data)
