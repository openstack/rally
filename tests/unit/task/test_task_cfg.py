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
from rally.task import task_cfg
from tests.unit import test


class TaskConfigTestCase(test.TestCase):

    def test_init_empty_config(self):
        config = None
        e = self.assertRaises(exceptions.InvalidTaskException,
                              task_cfg.TaskConfig, config)
        self.assertEqual("It is empty", e.kwargs["message"])

    def test_validate_version(self):
        p1001 = mock.Mock()
        p1002 = mock.Mock()

        valid_cfg = {"version": 0, "title": "", "subtasks": []}

        class TaskConfig(task_cfg.TaskConfig):
            def _process_1001(self, config):
                p1001()
                return valid_cfg

            def _process_1002(self, config):
                p1002()
                return valid_cfg

        TaskConfig({"version": 1001})
        p1001.assert_called_once_with()
        self.assertFalse(p1002.called)

        p1001.reset_mock()

        TaskConfig({"version": 1002})
        p1002.assert_called_once_with()
        self.assertFalse(p1001.called)

    def test__process_1(self):

        config = collections.OrderedDict()
        config["a.task"] = [{"context": {"foo": "bar"}}, {}]
        config["b.task"] = [{"sla": {"key": "value"}}]
        config["c.task"] = [{"hooks": [{"name": "foo",
                                        "args": "bar",
                                        "description": "DESCR!!!",
                                        "trigger": {
                                            "name": "mega-trigger",
                                            "args": {"some": "thing"}
                                        }}]
                             }]
        self.assertEqual(
            {"title": "Task (adopted from task format v1)",
             "version": 2,
             "description": "",
             "tags": [],
             "subtasks": [
                 {
                     "title": "a.task",
                     "description": "",
                     "tags": [],
                     "workloads": [
                         {
                             "scenario": {"a.task": {}},
                             "contexts": {"foo": "bar"},
                             "hooks": [],
                             "sla": {"failure_rate": {"max": 0}},
                             "runner": {"serial": {}}
                         },
                         {
                             "scenario": {"a.task": {}},
                             "contexts": {},
                             "hooks": [],
                             "sla": {"failure_rate": {"max": 0}},
                             "runner": {"serial": {}}
                         }
                     ],
                 },
                 {
                     "title": "b.task",
                     "description": "",
                     "tags": [],
                     "workloads": [
                         {
                             "scenario": {"b.task": {}},
                             "contexts": {},
                             "hooks": [],
                             "runner": {"serial": {}},
                             "sla": {"key": "value"},
                         }
                     ],
                 },
                 {
                     "title": "c.task",
                     "description": "",
                     "tags": [],
                     "workloads": [
                         {
                             "scenario": {"c.task": {}},
                             "contexts": {},
                             "hooks": [{
                                 "description": "DESCR!!!",
                                 "action": {"foo": "bar"},
                                 "trigger": {
                                     "mega-trigger": {"some": "thing"}}}
                             ],
                             "sla": {"failure_rate": {"max": 0}},
                             "runner": {"serial": {}}
                         }
                     ],
                 }]},
            task_cfg.TaskConfig(config).to_dict())

    def test__process_2(self):

        config = {
            "version": 2,
            "title": "foo",
            "subtasks": [
                {
                    "title": "subtask1",
                    "workloads": [
                        {
                            "scenario": {"workload1": {}},
                            "runner": {"constant": {}},
                            "sla": {"key": "value"}
                        },
                        {
                            "scenario": {"workload2": {}},
                        }
                    ]
                },
                {
                    "title": "subtask2",
                    "scenario": {"workload1": {}}
                },
            ]
        }

        self.assertEqual(
            {"title": "foo",
             "version": 2,
             "description": "",
             "tags": [],
             "subtasks": [
                 {
                     "title": "subtask1",
                     "description": "",
                     "tags": [],
                     "workloads": [
                         {
                             "scenario": {"workload1": {}},
                             "contexts": {},
                             "hooks": [],
                             "sla": {"key": "value"},
                             "runner": {"constant": {}}
                         },
                         {
                             "scenario": {"workload2": {}},
                             "contexts": {},
                             "hooks": [],
                             "sla": {"failure_rate": {"max": 0}},
                             "runner": {"serial": {}}
                         }
                     ],
                 },
                 {
                     "title": "subtask2",
                     "description": "",
                     "tags": [],
                     "workloads": [
                         {
                             "scenario": {"workload1": {}},
                             "contexts": {},
                             "hooks": [],
                             "runner": {"serial": {}},
                             "sla": {"failure_rate": {"max": 0}},
                         }
                     ],
                 }]},
            task_cfg.TaskConfig(config).to_dict())

    def test_hook_config_compatibility(self):
        cfg = {
            "xxx": [{
                "args": {},
                "runner": {"type": "yyy"},
                "hooks": [
                    {
                        "description": "descr",
                        "name": "hook_action",
                        "args": {"k1": "v1"},
                        "trigger": {
                            "name": "hook_trigger",
                            "args": {"k2": "v2"}
                        }
                    }
                ]
            }]
        }
        task = task_cfg.TaskConfig(cfg)
        workload = task.subtasks[0]["workloads"][0]
        self.assertEqual(
            {"description": "descr",
             "action": ("hook_action", {"k1": "v1"}),
             "trigger": ("hook_trigger", {"k2": "v2"})},
            workload["hooks"][0])

    # NOTE(andreykurilin): For a long time, we had a single JSON Schema for
    #   checking the task config. It was so complex that validation errors were
    #   unable to say anything helpful to end-users. The purpose of the
    #   following negative tests is to ensure that UX is on the good level.

    def test_validate_wrong_version(self):
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 5})
        self.assertEqual(
            "Task configuration version 5 is not supported. "
            "Supported versions: 1, 2",
            e.kwargs["message"])

    def test_v2_invalid_top_level(self):
        # single missed property
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "subtasks": []})
        self.assertEqual(
            "'title' is a required property, but it is missed.",
            e.kwargs["message"])
        # multiple missed properties (msg should be different)
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2})
        self.assertEqual(
            "'subtasks', 'title' are required properties, but they are "
            "missed.", e.kwargs["message"])

        # single redundant property
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": "", "subtasks": [],
                                  "foo": "bar"})
        self.assertEqual(
            "Additional properties are not allowed ('foo' was unexpected).",
            e.kwargs["message"]
        )
        # multiple redundant properties (msg should be different)
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": "", "subtasks": [],
                                  "foo": "bar", "xxx": "yyy"})
        self.assertEqual(
            "Additional properties are not allowed ('foo', 'xxx' were "
            "unexpected).",
            e.kwargs["message"]
        )

    def test_v2_title(self):
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": {}, "subtasks": []})
        self.assertEqual(
            "Title should be a string, but 'dict' is found.",
            e.kwargs["message"]
        )

        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": "a" * 300,
                                  "subtasks": []})
        self.assertEqual(
            "Title should not be longer then 254 char. Use 'description' field"
            " for longer text.",
            e.kwargs["message"]
        )

    def test_v2_tags(self):
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": "", "subtasks": [],
                                  "tags": {}})
        self.assertEqual(
            "Tags should be an array(list) of strings, but 'dict' is "
            "found.",
            e.kwargs["message"]
        )

        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": "", "subtasks": [],
                                  "tags": [1]})
        self.assertEqual(
            "Tag '1' should be a string, but 'int' is found.",
            e.kwargs["message"]
        )

    def test_v2_subtask(self):
        e = self.assertRaises(
            exceptions.InvalidTaskException,
            task_cfg.TaskConfig, {"version": 2, "title": "", "subtasks": {}})
        self.assertEqual(
            "Property 'subtasks' should be an array(list), but 'dict' "
            "is found.",
            e.kwargs["message"]
        )
