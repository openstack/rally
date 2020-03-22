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

from rally.cli import task_results_loader
from tests.unit import test

PATH = "rally.cli.task_results_loader"


class LoaderTestCase(test.TestCase):

    @mock.patch("%s._update_old_results" % PATH)
    @mock.patch("%s._update_new_results" % PATH)
    @mock.patch("%s.open" % PATH)
    def test_load(self, mock_open,
                  mock__update_new_results,
                  mock__update_old_results):
        r_file = mock_open.return_value.__enter__.return_value

        # case 1: the file contains invalid JSON
        r_file.read.return_value = ""

        self.assertRaises(task_results_loader.FailedToLoadResults,
                          task_results_loader.load,
                          "/some/path")
        self.assertFalse(mock__update_new_results.called)
        self.assertFalse(mock__update_old_results.called)
        mock__update_new_results.reset_mock()
        mock__update_old_results.reset_mock()

        # case 2: the file contains valid JSON with a dict that doesn't have
        #   'tasks' key
        r_file.read.return_value = "{}"

        self.assertRaises(task_results_loader.FailedToLoadResults,
                          task_results_loader.load,
                          "/some/path")
        self.assertFalse(mock__update_new_results.called)
        self.assertFalse(mock__update_old_results.called)
        mock__update_new_results.reset_mock()
        mock__update_old_results.reset_mock()

        # case 3: the file contains valid JSON with a dict that doesn't have
        #   'tasks' key
        r_file.read.return_value = "{\"tasks\": \"foo\"}"

        self.assertEqual(mock__update_new_results.return_value,
                         task_results_loader.load("/some/path"))
        mock__update_new_results.assert_called_once_with({"tasks": "foo"})
        self.assertFalse(mock__update_old_results.called)
        mock__update_new_results.reset_mock()
        mock__update_old_results.reset_mock()

        # case 4: the file contains valid JSON with a list
        r_file.read.return_value = "[\"foo\"]"

        self.assertEqual(mock__update_old_results.return_value,
                         task_results_loader.load("/some/path"))
        self.assertFalse(mock__update_new_results.called)
        mock__update_old_results.assert_called_once_with(["foo"], "/some/path")

    def test__update_new_results(self):
        results = {
            "tasks": [{
                "env_uuid": "env-uuid-1",
                "env_name": "env-name-1",
                "subtasks": [{
                    "workloads": [{
                        "contexts": {"xxx": {}},
                        "scenario": {"Foo.bar": {}},
                        "runner": {
                            "constant": {
                                "times": 100,
                                "concurrency": 5
                            }
                        },
                        "sla": {},
                        "sla_results": {},
                        "position": 0,
                        "pass_sla": True,
                        "statistics": {},
                        "data": [],
                        "full_duration": 5,
                        "load_duration": 2,
                        "total_iteration_count": 3,
                        "failed_iteration_count": 0
                    }]
                }]
            }]
        }

        self.assertEqual(
            [
                {
                    "env_uuid": "env-uuid-1",
                    "env_name": "env-name-1",
                    "subtasks": [{
                        "workloads": [{
                            "args": {},
                            "name": "Foo.bar",
                            "contexts": {"xxx": {}},
                            "contexts_results": [],
                            "runner_type": "constant",
                            "runner": {
                                "times": 100,
                                "concurrency": 5
                            },
                            "sla": {},
                            "sla_results": {},
                            "position": 0,
                            "pass_sla": True,
                            "statistics": {},
                            "data": [],
                            "full_duration": 5,
                            "load_duration": 2,
                            "total_iteration_count": 3,
                            "failed_iteration_count": 0
                        }]
                    }]
                }
            ],
            task_results_loader._update_new_results(results)
        )

    def test__update_old_results(self):

        workload = {
            "uuid": "n/a",
            "full_duration": 2, "load_duration": 1,
            "created_at": "2017-07-01T07:03:01",
            "updated_at": "2017-07-01T07:03:03",
            "total_iteration_count": 2,
            "failed_iteration_count": 1,
            "min_duration": 3,
            "max_duration": 5,
            "start_time": 1,
            "name": "Foo.bar", "description": "descr",
            "position": 2,
            "args": {"key1": "value1"},
            "runner_type": "constant",
            "runner": {"time": 3},
            "hooks": [{"config": {
                "description": "descr",
                "action": ("foo", {"arg1": "v1"}),
                "trigger": ("t", {"a2", "v2"})}}],
            "pass_sla": True,
            "sla": {"failure_rate": {"max": 0}},
            "sla_results": {"sla": [{"success": True}]},
            "contexts": {"users": {}},
            "contexts_results": [],
            "data": [{"timestamp": 1, "atomic_actions": {"foo": 1.0,
                                                         "bar": 1.0},
                      "duration": 5, "idle_duration": 0, "error": [{}]},
                     {"timestamp": 2, "atomic_actions": {"bar": 1.1},
                      "duration": 3, "idle_duration": 0, "error": []}],
            "statistics": {"durations": mock.ANY}
        }

        results = [{
            "hooks": [{
                "config": {
                    "name": "foo",
                    "args": {"arg1": "v1"},
                    "description": "descr",
                    "trigger": {"name": "t", "args": {"a2", "v2"}}}}],
            "key": {
                "name": workload["name"],
                "description": workload["description"],
                "pos": workload["position"],
                "kw": {
                    "args": workload["args"],
                    "runner": {"type": "constant", "time": 3},
                    "hooks": [{
                        "name": "foo",
                        "args": {"arg1": "v1"},
                        "description": "descr",
                        "trigger": {"name": "t", "args": {"a2", "v2"}}}],
                    "sla": workload["sla"],
                    "context": workload["contexts"]}},
            "sla": workload["sla_results"]["sla"],
            "result": workload["data"],
            "full_duration": workload["full_duration"],
            "load_duration": workload["load_duration"],
            "created_at": "2017-01-07T07:03:01"}
        ]

        self.assertEqual(
            [
                {
                    "version": 2,
                    "title": "Task loaded from a file.",
                    "description": "Auto-ported from task format V1.",
                    "uuid": "n/a",
                    "env_uuid": "n/a",
                    "env_name": "n/a",
                    "status": "finished",
                    "tags": [],
                    "subtasks": [{
                        "title": "A SubTask",
                        "description": "",
                        "workloads": [workload]}]
                }
            ],
            task_results_loader._update_old_results(results, "xxx")
        )

    def test__update_atomic_actions(self):
        atomic_actions = collections.OrderedDict(
            [("action_1", 1), ("action_2", 2)])
        self.assertEqual(
            [
                {
                    "name": "action_1",
                    "started_at": 1,
                    "finished_at": 2,
                    "children": []
                },
                {
                    "name": "action_2",
                    "started_at": 2,
                    "finished_at": 4,
                    "children": []
                }
            ],
            task_results_loader._update_atomic_actions(atomic_actions, 1)
        )
