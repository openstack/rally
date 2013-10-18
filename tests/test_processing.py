# Copyright 2013: Mirantis Inc.
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

import mock

from rally import exceptions
from rally import processing
from rally import test


class ProcessingTestCase(test.TestCase):

    def setUp(self):
        super(ProcessingTestCase, self).setUp()
        self.fake_task = {
            "results": [
                {
                    "data": {"raw": [{"error": None, "time": 10.5},
                                     {"error": None, "time": 12.5}]},
                    "key": {"name": "scenario_1",
                            "kw": {"config": {"active_users": 1}}}
                },
                {
                    "data": {"raw": [{"error": None, "time": 4.3}]},
                    "key": {"name": "scenario_2",
                            "kw": {"config": {"active_users": 1}}}
                },
                {
                    "data": {"raw": [{"error": None, "time": 1.2},
                                     {"error": None, "time": 3.4},
                                     {"error": None, "time": 5.6}]},
                    "key": {"name": "scenario_1",
                            "kw": {"config": {"active_users": 2}}}
                }
            ],
        }
        self.fake_task_aggregated_by_concurrency = {
            "scenario_1": {1: [10.5, 12.5], 2: [1.2, 3.4, 5.6]},
            "scenario_2": {1: [4.3]}
        }
        self.fake_task_invalid_no_aggregated_field = {
            "results": [
                {
                    "data": {"raw": [{"error": None, "time": 10.5},
                                     {"error": None, "time": 12.5}]},
                    "key": {"name": "scenario_1",
                            "kw": {"config": {"active_users": 1}}}
                },
                {
                    "data": {"raw": [{"error": None, "time": 4.3}]},
                    "key": {"name": "scenario_2",
                            "kw": {"config": {"times": 1}}}
                }
            ],
        }

    def test_aggregated_plot(self):
        with mock.patch("rally.processing.db.task_get_detailed") as mock_task:
            mock_task.return_value = self.fake_task_invalid_no_aggregated_field
            with mock.patch("rally.processing.plt") as mock_plot:
                with mock.patch("rally.processing.ticker"):
                    self.assertRaises(exceptions.NoSuchConfigField,
                                      processing.aggregated_plot,
                                      "task", "active_users")
            mock_task.return_value = self.fake_task
            with mock.patch("rally.processing.plt") as mock_plot:
                with mock.patch("rally.processing.ticker"):
                    processing.aggregated_plot("task", "active_users")

        expected_plot_calls = []
        expected_show_calls = []

        for scenario in self.fake_task_aggregated_by_concurrency:

            scenario_data = self.fake_task_aggregated_by_concurrency[scenario]

            active_users_vals = sorted(scenario_data.keys())

            mins = [min(scenario_data[c]) for c in active_users_vals]
            avgs = [sum(scenario_data[c]) / len(scenario_data[c])
                    for c in active_users_vals]
            maxes = [max(scenario_data[c]) for c in active_users_vals]

            expected_plot_calls.append(mock.call(active_users_vals, maxes,
                                                 "r-", label="max",
                                                 linewidth=2))
            expected_plot_calls.append(mock.call(active_users_vals, avgs,
                                                 "b-", label="avg",
                                                 linewidth=2))
            expected_plot_calls.append(mock.call(active_users_vals, mins,
                                                 "g-", label="min",
                                                 linewidth=2))
            expected_show_calls.append(mock.call.show())

        self.assertEqual(mock_plot.plot.mock_calls, expected_plot_calls)
        self.assertEqual(mock_plot.show.mock_calls, expected_show_calls)
