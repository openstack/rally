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

import mock

from rally import exceptions
from rally.task import task_cfg
from tests.unit import test


class TaskConfigTestCase(test.TestCase):

    def test_init_empty_config(self):
        config = None
        exception = self.assertRaises(Exception,  # noqa
                                      task_cfg.TaskConfig, config)
        self.assertIn("Input task is empty", str(exception))

    @mock.patch("jsonschema.validate")
    def test_validate_json(self, mock_validate):
        config = {}
        task_cfg.TaskConfig(config)
        mock_validate.assert_has_calls([
            mock.call(config, task_cfg.TaskConfig.CONFIG_SCHEMA_V1)])

    @mock.patch("jsonschema.validate")
    def test_validate_json_v2(self, mock_validate):
        config = {"version": 2, "subtasks": []}
        task_cfg.TaskConfig(config)
        mock_validate.assert_has_calls([
            mock.call(config, task_cfg.TaskConfig.CONFIG_SCHEMA_V2)])

    @mock.patch("rally.task.task_cfg.TaskConfig._get_version")
    @mock.patch("rally.task.task_cfg.TaskConfig._validate_json")
    def test_validate_version(self, mock_task_config__validate_json,
                              mock_task_config__get_version):
        mock_task_config__get_version.return_value = 1
        task_cfg.TaskConfig(mock.MagicMock())

    @mock.patch("rally.task.task_cfg.TaskConfig._get_version")
    @mock.patch("rally.task.task_cfg.TaskConfig._validate_json")
    def test_validate_version_wrong_version(
            self, mock_task_config__validate_json,
            mock_task_config__get_version):

        mock_task_config__get_version.return_value = "wrong"
        self.assertRaises(exceptions.InvalidTaskException, task_cfg.TaskConfig,
                          mock.MagicMock)

    def test__adopt_task_format_v1(self):

        # mock all redundant checks :)
        class TaskConfig(task_cfg.TaskConfig):
            def __init__(self):
                pass

        config = collections.OrderedDict()
        config["a.task"] = [{"s": 1, "context": {"foo": "bar"}}, {"s": 2}]
        config["b.task"] = [{"s": 3, "sla": {"key": "value"}}]
        config["c.task"] = [{"s": 5,
                             "hooks": [{"name": "foo",
                                        "args": "bar",
                                        "description": "DESCR!!!",
                                        "trigger": {
                                            "name": "mega-trigger",
                                            "args": {"some": "thing"}
                                        }}]
                             }]
        self.assertEqual(
            {"title": "Task (adopted from task format v1)",
             "subtasks": [
                 {
                     "title": "a.task",
                     "scenario": {"a.task": {}},
                     "s": 1,
                     "contexts": {"foo": "bar"}
                 },
                 {
                     "title": "a.task",
                     "s": 2,
                     "scenario": {"a.task": {}},
                     "contexts": {}
                 },
                 {
                     "title": "b.task",
                     "s": 3,
                     "scenario": {"b.task": {}},
                     "sla": {"key": "value"},
                     "contexts": {}
                 },
                 {
                     "title": "c.task",
                     "s": 5,
                     "scenario": {"c.task": {}},
                     "contexts": {},
                     "hooks": [
                         {"description": "DESCR!!!",
                          "action": {"foo": "bar"},
                          "trigger": {"mega-trigger": {"some": "thing"}}}
                     ]
                 }]},
            TaskConfig._adopt_task_format_v1(config))

    def test_hook_config_compatibility(self):
        cfg = {
            "title": "foo",
            "version": 2,
            "subtasks": [
                {
                    "title": "foo",
                    "scenario": {"xxx": {}},
                    "runner": {"yyy": {}},
                    "hooks": [
                        {"description": "descr",
                         "name": "hook_action",
                         "args": {"k1": "v1"},
                         "trigger": {
                             "name": "hook_trigger",
                             "args": {"k2": "v2"}
                         }}
                    ]
                }
            ]
        }
        task = task_cfg.TaskConfig(cfg)
        workload = task.subtasks[0]["workloads"][0]
        self.assertEqual(
            {"description": "descr",
             "action": ("hook_action", {"k1": "v1"}),
             "trigger": ("hook_trigger", {"k2": "v2"})},
            workload["hooks"][0])
