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

"""Tests for db.task layer."""

import collections
import datetime as dt

import ddt
import mock

from rally.common import objects
from rally import consts
from rally import exceptions
from tests.unit import test


@ddt.ddt
class TaskTestCase(test.TestCase):
    def setUp(self):
        super(TaskTestCase, self).setUp()
        self.task = {
            "uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca1",
            "status": consts.TaskStatus.INIT,
            "validation_result": {},
        }

    @mock.patch("rally.common.objects.task.db.task_create")
    def test_init_with_create(self, mock_task_create):
        mock_task_create.return_value = self.task
        task = objects.Task(status=consts.TaskStatus.CRASHED)
        mock_task_create.assert_called_once_with({
            "status": consts.TaskStatus.CRASHED})
        self.assertEqual(task["uuid"], self.task["uuid"])

    @mock.patch("rally.common.objects.task.db.task_create")
    def test_init_without_create(self, mock_task_create):
        task = objects.Task(task=self.task)
        self.assertFalse(mock_task_create.called)
        self.assertEqual(task["uuid"], self.task["uuid"])

    @mock.patch("rally.common.objects.task.uuid.uuid4",
                return_value="some_uuid")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_init_with_fake_true(self, mock_task_create, mock_uuid4):
        task = objects.Task(temporary=True)
        self.assertFalse(mock_task_create.called)
        self.assertTrue(mock_uuid4.called)
        self.assertEqual(task["uuid"], mock_uuid4.return_value)

    @mock.patch("rally.common.db.api.task_get")
    def test_get(self, mock_task_get):
        mock_task_get.return_value = self.task
        task = objects.Task.get(self.task["uuid"])
        mock_task_get.assert_called_once_with(self.task["uuid"],
                                              detailed=False)
        self.assertEqual(task["uuid"], self.task["uuid"])

    @mock.patch("rally.common.objects.task.db.task_get_status")
    def test_get_status(self, mock_task_get_status):
        task = objects.Task(task=self.task)
        status = task.get_status(task["uuid"])
        self.assertEqual(status, mock_task_get_status.return_value)

    @mock.patch("rally.common.objects.task.db.task_delete")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_create_and_delete(self, mock_task_create, mock_task_delete):
        mock_task_create.return_value = self.task
        task = objects.Task()
        task.delete()
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=None)

    @mock.patch("rally.common.objects.task.db.task_delete")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_create_and_delete_status(self, mock_task_create,
                                      mock_task_delete):
        mock_task_create.return_value = self.task
        task = objects.Task()
        task.delete(status=consts.TaskStatus.FINISHED)
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.common.objects.task.db.task_delete")
    def test_delete_by_uuid(self, mock_task_delete):
        objects.Task.delete_by_uuid(self.task["uuid"])
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=None)

    @mock.patch("rally.common.objects.task.db.task_delete")
    def test_delete_by_uuid_status(self, mock_task_delete):
        objects.Task.delete_by_uuid(self.task["uuid"],
                                    consts.TaskStatus.FINISHED)
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.common.objects.task.db.task_list",
                return_value=[{"uuid": "a",
                               "created_at": "b",
                               "status": consts.TaskStatus.CRASHED,
                               "tag": "d",
                               "deployment_name": "some_name"}])
    def list(self, mock_db_task_list):
        tasks = objects.Task.list(status="somestatus")
        mock_db_task_list.assert_called_once_with("somestatus", None)
        self.assertIs(type(tasks), list)
        self.assertIsInstance(tasks[0], objects.Task)
        self.assertEqual(mock_db_task_list.return_value["uuis"],
                         tasks[0]["uuid"])

    @mock.patch("rally.common.objects.task.db.task_update")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_update(self, mock_task_create, mock_task_update):
        mock_task_create.return_value = self.task
        mock_task_update.return_value = {"opt": "val2"}
        deploy = objects.Task(opt="val1")
        deploy._update({"opt": "val2"})
        mock_task_update.assert_called_once_with(
            self.task["uuid"], {"opt": "val2"})
        self.assertEqual(deploy["opt"], "val2")

    @ddt.data(
        {
            "status": "some_status", "allowed_statuses": ("s_1", "s_2")
        },
        {
            "status": "some_status", "allowed_statuses": None
        }
    )
    @ddt.unpack
    @mock.patch("rally.common.objects.task.db.task_update_status")
    @mock.patch("rally.common.objects.task.db.task_update")
    def test_update_status(self, mock_task_update, mock_task_update_status,
                           status, allowed_statuses):
        task = objects.Task(task=self.task)
        task.update_status(consts.TaskStatus.FINISHED, allowed_statuses)
        if allowed_statuses:
            self.assertFalse(mock_task_update.called)
            mock_task_update_status.assert_called_once_with(
                self.task["uuid"],
                consts.TaskStatus.FINISHED,
                allowed_statuses
            )
        else:
            self.assertFalse(mock_task_update_status.called)
            mock_task_update.assert_called_once_with(
                self.task["uuid"],
                {"status": consts.TaskStatus.FINISHED},
            )

    @mock.patch("rally.common.objects.task.db.task_update")
    def test_update_verification_log(self, mock_task_update):
        mock_task_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.set_validation_failed({"a": "fake"})
        mock_task_update.assert_called_once_with(
            self.task["uuid"],
            {"status": consts.TaskStatus.VALIDATION_FAILED,
             "validation_result": {"a": "fake"}}
        )

    @mock.patch("rally.common.objects.task.db.env_get")
    def test_to_dict(self, mock_env_get):
        workloads = [{"created_at": dt.datetime.now(),
                      "updated_at": dt.datetime.now()}]
        self.task.update({"env_uuid": "deployment_uuid",
                          "deployment_uuid": "deployment_uuid",
                          "created_at": dt.datetime.now(),
                          "updated_at": dt.datetime.now()})

        mock_env_get.return_value = {"name": "deployment_name"}

        task = objects.Task(task=self.task)
        serialized_task = task.to_dict()

        mock_env_get.assert_called_once_with(self.task["env_uuid"])
        self.assertEqual(self.task, serialized_task)

        self.task["subtasks"] = [{"workloads": workloads}]

    @mock.patch("rally.common.db.api.task_get")
    def test_get_detailed(self, mock_task_get):
        mock_task_get.return_value = {"results": [{
            "created_at": dt.datetime.now(),
            "updated_at": dt.datetime.now()}]}
        task_detailed = objects.Task.get("task_id", detailed=True)
        mock_task_get.assert_called_once_with("task_id", detailed=True)
        self.assertEqual(mock_task_get.return_value, task_detailed.task)

    @mock.patch("rally.common.objects.task.db.task_update")
    def test_set_failed(self, mock_task_update):
        mock_task_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.set_failed("foo_type", "foo_error_message", "foo_trace")
        mock_task_update.assert_called_once_with(
            self.task["uuid"],
            {"status": consts.TaskStatus.CRASHED,
             "validation_result": {"etype": "foo_type",
                                   "msg": "foo_error_message",
                                   "trace": "foo_trace"}},
        )

    @mock.patch("rally.common.objects.task.Subtask")
    def test_add_subtask(self, mock_subtask):
        task = objects.Task(task=self.task)
        subtask = task.add_subtask(title="foo")
        mock_subtask.assert_called_once_with(
            self.task["uuid"], title="foo", contexts=None, description=None)
        self.assertIs(subtask, mock_subtask.return_value)

    @ddt.data(
        {
            "soft": True, "status": consts.TaskStatus.INIT
        },
        {
            "soft": True, "status": consts.TaskStatus.VALIDATING,
            "soft": True, "status": consts.TaskStatus.ABORTED
        },
        {
            "soft": True, "status": consts.TaskStatus.FINISHED
        },
        {
            "soft": True, "status": consts.TaskStatus.CRASHED
        },
        {
            "soft": False, "status": consts.TaskStatus.ABORTED
        },
        {
            "soft": False, "status": consts.TaskStatus.FINISHED
        },
        {
            "soft": False, "status": consts.TaskStatus.CRASHED
        }
    )
    @ddt.unpack
    def test_abort_with_finished_states(self, soft, status):
        task = objects.Task(mock.MagicMock(), fake=True)
        task.get_status = mock.MagicMock(return_value=status)
        task.update_status = mock.MagicMock()

        self.assertRaises(exceptions.RallyException, task.abort, soft)

        self.assertEqual(1, task.get_status.call_count)
        self.assertFalse(task.update_status.called)

    @ddt.data(True, False)
    def test_abort_with_running_state(self, soft):
        task = objects.Task(mock.MagicMock(), fake=True)
        task.get_status = mock.MagicMock(return_value="running")
        task.update_status = mock.MagicMock()

        task.abort(soft)
        if soft:
            status = consts.TaskStatus.SOFT_ABORTING
        else:
            status = consts.TaskStatus.ABORTING

        task.update_status.assert_called_once_with(
            status,
            allowed_statuses=(consts.TaskStatus.RUNNING,
                              consts.TaskStatus.SOFT_ABORTING)
        )

    @ddt.data(
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "output": {"additive": [], "complete": []},
                  "error": ["err1", "err2"], "atomic_actions": []},
         "expected": True},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 5.2, "children": []}]},
         "expected": True},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": ["a1", "a2"],
                                          "complete": ["c1", "c2"]},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 5.2, "children": []}]},
         "validate_output_calls": [("additive", "a1"), ("additive", "a2"),
                                   ("complete", "c1"), ("complete", "c2")],
         "expected": True},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": ["a1", "a2"],
                                          "complete": ["c1", "c2"]},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 5.2, "children": []}]},
         "validate_output_return_value": "validation error message"},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [42], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 5.2, "children": []}]}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "foo", "started_at": 10,
                                      "finished_at": 52, "children": []}]}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "non-float", "started_at": 1.0,
                                      "children": []}]}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 4.0,
                                      "children": [{"name": "foo1",
                                                    "started_at": 2.0,
                                                    "finished_at": 3.0,
                                                    "children": []}]}]},
         "expected": True},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 4.0,
                                      "children": [{"name": "foo1",
                                                    "started_at": 20,
                                                    "finished_at": 30,
                                                    "children": []}]}]}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": [{"name": "foo", "started_at": 1.0,
                                      "finished_at": 4.0,
                                      "children": [{"name": "foo1",
                                                    "started_at": 2.0,
                                                    "finished_at": 3.0}]}]}},
        {"data": {"duration": 1, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1,
                  "error": [], "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": "foo", "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {}, "atomic_actions": []}},
        {"data": {"timestamp": 1.0, "idle_duration": 1.0, "error": [],
                  "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "idle_duration": 1.0, "error": [],
                  "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "error": [],
                  "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "output": {"additive": [], "complete": []},
                  "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "atomic_actions": []}},
        {"data": {"duration": 1.0, "timestamp": 1.0, "idle_duration": 1.0,
                  "error": [], "output": {"additive": [], "complete": []}}},
        {"data": []},
        {"data": {}},
        {"data": "foo"})
    @ddt.unpack
    @mock.patch("rally.common.objects.task.LOG")
    @mock.patch("rally.common.objects.task.charts.validate_output")
    def test_result_has_valid_schema(self, mock_validate_output, mock_log,
                                     data, expected=False,
                                     validate_output_return_value=None,
                                     validate_output_calls=None):
        task = objects.Task(task=self.task)
        mock_validate_output.return_value = validate_output_return_value
        self.assertEqual(expected,
                         task.result_has_valid_schema(data),
                         message=repr(data))
        if validate_output_calls:
            mock_validate_output.assert_has_calls(
                [mock.call(*args) for args in validate_output_calls],
                any_order=True)


class SubtaskTestCase(test.TestCase):

    def setUp(self):
        super(SubtaskTestCase, self).setUp()
        self.subtask = {
            "task_uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca1",
            "uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca2",
            "title": "foo",
        }

    @mock.patch("rally.common.objects.task.db.subtask_create")
    def test_init(self, mock_subtask_create):
        mock_subtask_create.return_value = self.subtask
        subtask = objects.Subtask("bar", title="foo")
        mock_subtask_create.assert_called_once_with(
            "bar", title="foo", contexts=None, description=None)
        self.assertEqual(subtask["uuid"], self.subtask["uuid"])

    @mock.patch("rally.common.objects.task.db.subtask_update")
    @mock.patch("rally.common.objects.task.db.subtask_create")
    def test_update_status(self, mock_subtask_create, mock_subtask_update):
        mock_subtask_create.return_value = self.subtask
        subtask = objects.Subtask("bar", title="foo")
        subtask.update_status(consts.SubtaskStatus.FINISHED)
        mock_subtask_update.assert_called_once_with(
            self.subtask["uuid"], {"status": consts.SubtaskStatus.FINISHED})

    @mock.patch("rally.common.objects.task.Workload")
    @mock.patch("rally.common.objects.task.db.subtask_create")
    def test_add_workload(self, mock_subtask_create, mock_workload):
        mock_subtask_create.return_value = self.subtask
        subtask = objects.Subtask("bar", title="foo")

        name = "w"
        description = "descr"
        position = 0
        runner_type = "runner"
        runner = {}
        contexts = {"users": {}}
        sla = {"failure_rate": {"max": 0}}
        args = {"arg": "xxx"}
        hooks = [{"foo": "bar"}]

        workload = subtask.add_workload(
            name, description=description, position=position,
            runner_type=runner_type, runner=runner, contexts=contexts, sla=sla,
            args=args, hooks=hooks)
        mock_workload.assert_called_once_with(
            task_uuid=self.subtask["task_uuid"],
            subtask_uuid=self.subtask["uuid"], name=name,
            description=description, position=position,
            runner_type=runner_type, runner=runner,
            contexts=contexts, sla=sla, args=args,
            hooks=[{"config": h} for h in hooks])
        self.assertIs(workload, mock_workload.return_value)


class WorkloadTestCase(test.TestCase):

    def setUp(self):
        super(WorkloadTestCase, self).setUp()
        self.workload = {
            "task_uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca1",
            "subtask_uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca2",
            "uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca3",
        }

    @mock.patch("rally.common.objects.task.db.workload_create")
    def test_init(self, mock_workload_create):
        mock_workload_create.return_value = self.workload
        name = "w"
        description = "descr"
        position = 0
        runner_type = "constant"
        runner = {"times": 3}
        contexts = {"users": {}}
        sla = {"failure_rate": {"max": 0}}
        args = {"arg": "xxx"}
        hooks = [{"config": {"foo": "bar"}}]
        workload = objects.Workload("uuid1", "uuid2", name=name,
                                    description=description, position=position,
                                    runner=runner, runner_type=runner_type,
                                    contexts=contexts, sla=sla,
                                    args=args, hooks=hooks)
        mock_workload_create.assert_called_once_with(
            task_uuid="uuid1", subtask_uuid="uuid2", name=name, hooks=hooks,
            description=description, position=position, runner=runner,
            runner_type="constant", contexts=contexts, sla=sla, args=args)
        self.assertEqual(workload["uuid"], self.workload["uuid"])

    @mock.patch("rally.common.objects.task.db.workload_data_create")
    @mock.patch("rally.common.objects.task.db.workload_create")
    def test_add_workload_data(self, mock_workload_create,
                               mock_workload_data_create):
        mock_workload_create.return_value = self.workload
        workload = objects.Workload("uuid1", "uuid2", name="w",
                                    description="descr", position=0,
                                    runner_type="foo", runner={},
                                    contexts=None,
                                    sla=None, args=None, hooks=[])

        workload.add_workload_data(0, {"data": "foo"})
        mock_workload_data_create.assert_called_once_with(
            self.workload["task_uuid"], self.workload["uuid"],
            0, {"data": "foo"})

    @mock.patch("rally.common.objects.task.db.workload_set_results")
    @mock.patch("rally.common.objects.task.db.workload_create")
    def test_set_results(self, mock_workload_create,
                         mock_workload_set_results):
        mock_workload_create.return_value = self.workload
        name = "w"
        description = "descr"
        position = 0
        runner_type = "constant"
        runner = {"times": 3}
        contexts = {"users": {}}
        sla = {"failure_rate": {"max": 0}}
        args = {"arg": "xxx"}
        load_duration = 88
        full_duration = 99
        start_time = 1231231277.22
        sla_results = []
        hooks = []
        contexts_results = [{"name": "setup:something"}]
        workload = objects.Workload("uuid1", "uuid2", name=name,
                                    description=description, position=position,
                                    runner=runner, runner_type=runner_type,
                                    contexts=contexts, sla=sla, args=args,
                                    hooks=hooks)

        workload.set_results(load_duration=load_duration,
                             full_duration=full_duration,
                             start_time=start_time,
                             sla_results=sla_results,
                             contexts_results=contexts_results)
        mock_workload_set_results.assert_called_once_with(
            workload_uuid=self.workload["uuid"],
            subtask_uuid=self.workload["subtask_uuid"],
            task_uuid=self.workload["task_uuid"],
            load_duration=load_duration, full_duration=full_duration,
            start_time=start_time, sla_results=sla_results,
            contexts_results=contexts_results,
            hooks_results=None)

    def test_to_task(self):
        workload = {
            "id": 777,
            "uuid": "uuiiidd",
            "task_uuid": "task-uuid",
            "subtask_uuid": "subtask-uuid",
            "name": "Foo.bar",
            "description": "Make something useful (or not).",
            "position": 3,
            "runner_type": "constant",
            "runner": {"times": 3},
            "contexts": {"users": {}},
            "sla": {"failure_rate": {"max": 0}},
            "args": {"key1": "value1"},
            "hooks": [{"config": {
                "action": ["foo", {"arg1": "v1"}],
                "trigger": ["bar", {"arg2": "v2"}]
            }}],
            "sla_results": {"sla": []},
            "context_execution": {},
            "start_time": "2997.23.12",
            "load_duration": 42,
            "full_duration": 37,
            "min_duration": 1,
            "max_duration": 2,
            "total_iteration_count": 7,
            "failed_iteration_count": 2,
            "statistics": {},
            "pass_sla": False
        }
        expected_task = collections.OrderedDict([
            ("version", 2),
            ("title", "A cropped version of a bigger task."),
            ("description", "Auto-generated task from a single workload "
                            "(uuid=%s)" % workload["uuid"]),
            ("subtasks",
             [collections.OrderedDict([
                 ("title", workload["name"]),
                 ("description", workload["description"]),
                 ("scenario", {workload["name"]: workload["args"]}),
                 ("contexts", workload["contexts"]),
                 ("runner", {"constant": {"times": 3}}),
                 ("hooks", [{"action": {"foo": {"arg1": "v1"}},
                             "trigger": {"bar": {"arg2": "v2"}},
                             "description": None}]),
                 ("sla", workload["sla"])])])])
        self.assertEqual(expected_task, objects.Workload.to_task(workload))
