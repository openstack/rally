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

"""Tests for db.api layer."""

import datetime as dt

import mock
from six import moves

from rally.common import db
from rally import consts
from rally import exceptions
from tests.unit import test

NOW = dt.datetime.now()


class ConnectionTestCase(test.DBTestCase):
    def test_schema_revision(self):
        rev = db.schema.schema_revision()
        drev = db.schema.schema_revision(detailed=True)
        self.assertEqual(drev["revision"], rev)
        self.assertEqual(drev["revision"], drev["current_head"])


class TasksTestCase(test.DBTestCase):
    def setUp(self):
        super(TasksTestCase, self).setUp()
        self.env = db.env_create(self.id(), "INIT", "", {}, {}, {}, [])

    def _get_task(self, uuid):
        return db.task_get(uuid)

    def _get_task_status(self, uuid):
        return db.task_get_status(uuid)

    def _create_task(self, values=None):
        values = values or {}
        if "env_uuid" not in values:
            values["env_uuid"] = self.env["uuid"]
        return db.task_create(values)

    def test_task_get_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.task_get, "f885f435-f6ca-4f3e-9b3e-aeb6837080f2")

    def test_task_get_status_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.task_get_status,
                          "f885f435-f6ca-4f3e-9b3e-aeb6837080f2")

    def test_task_create(self):
        task = self._create_task()
        db_task = self._get_task(task["uuid"])
        self.assertIsNotNone(db_task["uuid"])
        self.assertIsNotNone(db_task["id"])
        self.assertEqual(consts.TaskStatus.INIT, db_task["status"])

    def test_task_create_with_tag(self):
        task = self._create_task(values={"tags": ["test_tag"]})
        db_task = self._get_task(task["uuid"])
        self.assertIsNotNone(db_task["uuid"])
        self.assertIsNotNone(db_task["id"])
        self.assertEqual(consts.TaskStatus.INIT, db_task["status"])
        self.assertEqual(["test_tag"], db_task["tags"])

    def test_task_create_without_uuid(self):
        _uuid = "19be8589-48b0-4af1-a369-9bebaaa563ab"
        task = self._create_task({"uuid": _uuid})
        db_task = self._get_task(task["uuid"])
        self.assertEqual(_uuid, db_task["uuid"])

    def test_task_update(self):
        task = self._create_task({})
        db.task_update(task["uuid"], {"status": consts.TaskStatus.CRASHED})
        db_task = self._get_task(task["uuid"])
        self.assertEqual(consts.TaskStatus.CRASHED, db_task["status"])

    def test_task_update_with_tag(self):
        task = self._create_task({})
        db.task_update(task["uuid"], {
            "status": consts.TaskStatus.CRASHED,
            "tags": ["test_tag"]
        })
        db_task = self._get_task(task["uuid"])
        self.assertEqual(consts.TaskStatus.CRASHED, db_task["status"])
        self.assertEqual(["test_tag"], db_task["tags"])

    def test_task_update_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.task_update,
                          "fake_uuid", {})

    def test_task_update_status(self):
        self.assertRaises(exceptions.RallyException,
                          db.task_update_status,
                          "fake_uuid", consts.TaskStatus.RUNNING,
                          [consts.TaskStatus.RUNNING])

    def test_task_update_all_stats(self):
        _uuid = self._create_task({})["uuid"]
        for status in consts.TaskStatus:
            db.task_update(_uuid, {"status": status})
            db_task = self._get_task(_uuid)
            self.assertEqual(status, db_task["status"])

    def test_task_list_empty(self):
        self.assertEqual([], db.task_list())

    def test_task_list(self):
        INIT = consts.TaskStatus.INIT
        task_init = sorted(self._create_task()["uuid"] for i in moves.range(3))
        FINISHED = consts.TaskStatus.FINISHED
        task_finished = sorted(self._create_task(
            {"status": FINISHED,
             "env_uuid": self.env["uuid"]}
        )["uuid"] for i in moves.range(3))

        task_all = sorted(task_init + task_finished)

        def get_uuids(status=None, env=None):
            tasks = db.task_list(status=status, env=env)
            return sorted(task["uuid"] for task in tasks)

        self.assertEqual(task_all, get_uuids(None))

        self.assertEqual(task_init, get_uuids(status=INIT))
        self.assertEqual(task_finished, get_uuids(status=FINISHED))
        self.assertRaises(exceptions.DBRecordNotFound,
                          get_uuids, env="non-existing-env")

        deleted_task_uuid = task_finished.pop()
        db.task_delete(deleted_task_uuid)
        self.assertEqual(task_init, get_uuids(INIT))
        self.assertEqual(sorted(task_finished), get_uuids(FINISHED))

    def test_task_delete(self):
        task1, task2 = self._create_task()["uuid"], self._create_task()["uuid"]
        db.task_delete(task1)
        self.assertRaises(exceptions.DBRecordNotFound, self._get_task, task1)
        self.assertEqual(task2, self._get_task(task2)["uuid"])

    def test_task_delete_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.task_delete,
                          "da6f820c-b133-4b9f-8534-4c3bcc40724b")

    def test_task_delete_by_uuid_and_status(self):
        values = {
            "status": consts.TaskStatus.FINISHED,
        }
        task1 = self._create_task(values=values)["uuid"]
        task2 = self._create_task(values=values)["uuid"]
        db.task_delete(task1, status=consts.TaskStatus.FINISHED)
        self.assertRaises(exceptions.DBRecordNotFound, self._get_task, task1)
        self.assertEqual(task2, self._get_task(task2)["uuid"])

    def test_task_delete_by_uuid_and_status_invalid(self):
        task = self._create_task(
            values={"status": consts.TaskStatus.INIT})["uuid"]
        self.assertRaises(exceptions.DBConflict, db.task_delete, task,
                          status=consts.TaskStatus.FINISHED)

    def test_task_delete_by_uuid_and_status_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.task_delete,
                          "fcd0483f-a405-44c4-b712-99c9e52254eb",
                          status=consts.TaskStatus.FINISHED)

    def test_task_create_and_get_detailed(self):
        validation_result = {
            "etype": "FooError",
            "msg": "foo message",
            "trace": "foo t/b",
        }
        task1 = self._create_task({"validation_result": validation_result,
                                   "tags": ["bar"]})
        w_name = "atata"
        w_description = "tatata"
        w_position = 0
        w_args = {"a": "A"}
        w_contexts = {"c": "C"}
        w_sla = {"s": "S"}
        w_runner = {"r": "R", "type": "T"}
        w_runner_type = "T"
        sla_results = [
            {"s": "S", "success": True},
            {"1": "2", "success": True},
            {"a": "A", "success": True}
        ]
        w_load_duration = 13.0
        w_full_duration = 42.0
        w_start_time = 33.77
        w_hooks = []
        w_ctx_results = [{"name": "setup:something"}]

        subtask = db.subtask_create(task1["uuid"], title="foo")
        workload = db.workload_create(task1["uuid"], subtask["uuid"],
                                      name=w_name, description=w_description,
                                      position=w_position, args=w_args,
                                      contexts=w_contexts, sla=w_sla,
                                      hooks=w_hooks, runner=w_runner,
                                      runner_type=w_runner_type)
        db.workload_data_create(task1["uuid"], workload["uuid"], 0,
                                {"raw": []})
        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=workload["subtask_uuid"],
                                task_uuid=workload["task_uuid"],
                                sla_results=sla_results,
                                load_duration=w_load_duration,
                                full_duration=w_full_duration,
                                start_time=w_start_time,
                                contexts_results=w_ctx_results)

        task1_full = db.task_get(task1["uuid"], detailed=True)
        self.assertEqual(validation_result, task1_full["validation_result"])
        self.assertEqual(["bar"], task1_full["tags"])
        workloads = task1_full["subtasks"][0]["workloads"]
        self.assertEqual(1, len(workloads))
        workloads[0].pop("uuid")
        workloads[0].pop("created_at")
        workloads[0].pop("updated_at")

        self.assertEqual(
            {"subtask_uuid": subtask["uuid"],
             "task_uuid": task1["uuid"],
             "name": w_name, "description": w_description,
             "id": 1, "position": w_position,
             "data": [],
             "args": w_args,
             "contexts": w_contexts,
             "contexts_results": w_ctx_results,
             "hooks": w_hooks,
             "runner": w_runner, "runner_type": w_runner_type,
             "full_duration": w_full_duration,
             "load_duration": w_load_duration,
             "start_time": w_start_time,
             "max_duration": None, "min_duration": None,
             "failed_iteration_count": 0, "total_iteration_count": 0,
             "pass_sla": True, "sla": w_sla, "statistics": mock.ANY,
             "sla_results": {"sla": sla_results}}, workloads[0])

    def test_task_multiple_raw_result_create(self):
        task_id = self._create_task()["uuid"]
        subtask = db.subtask_create(task_id, title="foo")
        workload = db.workload_create(task_id, subtask["uuid"], name="atata",
                                      description="foo", position=0, args={},
                                      contexts={}, sla={}, runner={},
                                      runner_type="r", hooks=[])

        db.workload_data_create(task_id, workload["uuid"], 0, {
            "raw": [
                {"error": "anError",
                 "duration": 1,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 1,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 2,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 3,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
            ],
        })

        db.workload_data_create(task_id, workload["uuid"], 1, {
            "raw": [
                {"error": "anError2",
                 "timestamp": 10,
                 "duration": 1,
                 "idle_duration": 0,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 6,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 5,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 4,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
            ],
        })

        db.workload_data_create(task_id, workload["uuid"], 2, {
            "raw": [
                {"error": None,
                 "duration": 7,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
                {"error": None,
                 "duration": 8,
                 "timestamp": 10,
                 "idle_duration": 1,
                 "atomic_actions": []},
            ],
        })

        sla_results = [{"s": "S", "success": True},
                       {"1": "2", "success": True},
                       {"a": "A", "success": True}]
        load_duration = 13
        full_duration = 42
        start_time = 33.33
        w_ctx_results = [{"name": "setup:something"}]

        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=workload["subtask_uuid"],
                                task_uuid=workload["task_uuid"],
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results,
                                contexts_results=w_ctx_results)

        detailed_task = db.task_get(task_id, detailed=True)
        self.assertEqual(1, len(detailed_task["subtasks"]))
        self.assertEqual(1, len(detailed_task["subtasks"][0]["workloads"]))
        workload = detailed_task["subtasks"][0]["workloads"][0]
        self.assertEqual([
            {"error": "anError", "timestamp": 10, "duration": 1,
             "idle_duration": 1, "atomic_actions": []},
            {"error": None, "duration": 1, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": None, "duration": 2, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": None, "duration": 3, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": "anError2", "timestamp": 10, "duration": 1,
             "idle_duration": 0, "atomic_actions": []},
            {"error": None, "duration": 6, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": None, "duration": 5, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": None, "duration": 4, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": None, "duration": 7, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []},
            {"error": None, "duration": 8, "timestamp": 10, "idle_duration": 1,
             "atomic_actions": []}], workload["data"])
        self.assertTrue(workload["pass_sla"])
        self.assertEqual(sla_results, workload["sla_results"]["sla"])
        self.assertEqual(load_duration, workload["load_duration"])
        self.assertEqual(full_duration, workload["full_duration"])
        self.assertEqual(start_time, workload["start_time"])
        self.assertEqual(2, workload["failed_iteration_count"])
        self.assertEqual(10, workload["total_iteration_count"])
        self.assertEqual(w_ctx_results, workload["contexts_results"])

        db.task_delete(task_id)


class SubtaskTestCase(test.DBTestCase):
    def setUp(self):
        super(SubtaskTestCase, self).setUp()
        self.env = db.env_create(self.id(), "INIT", "", {}, {}, {}, [])
        self.task = db.task_create({"env_uuid": self.env["uuid"]})

    def test_subtask_create(self):
        subtask = db.subtask_create(self.task["uuid"], title="foo")
        self.assertEqual("foo", subtask["title"])
        self.assertEqual(self.task["uuid"], subtask["task_uuid"])

    def test_subtask_update(self):
        subtask = db.subtask_create(self.task["uuid"], title="foo")
        subtask = db.subtask_update(subtask["uuid"], {
            "title": "bar",
            "status": consts.SubtaskStatus.FINISHED})
        self.assertEqual("bar", subtask["title"])
        self.assertEqual(consts.SubtaskStatus.FINISHED, subtask["status"])


class WorkloadTestCase(test.DBTestCase):
    def setUp(self):
        super(WorkloadTestCase, self).setUp()
        self.env = db.env_create(self.id(), "INIT", "", {}, {}, {}, [])
        self.task = db.task_create({"env_uuid": self.env["uuid"]})
        self.task_uuid = self.task["uuid"]
        self.subtask = db.subtask_create(self.task_uuid, title="foo")
        self.subtask_uuid = self.subtask["uuid"]

    def test_workload_create(self):
        w_name = "atata"
        w_description = "tatata"
        w_position = 0
        w_args = {"a": "A"}
        w_contexts = {"c": "C"}
        w_sla = {"s": "S"}
        w_runner = {"r": "R", "type": "T"}
        w_runner_type = "T"
        w_hooks = []

        workload = db.workload_create(self.task_uuid, self.subtask_uuid,
                                      name=w_name, description=w_description,
                                      position=w_position, args=w_args,
                                      contexts=w_contexts, sla=w_sla,
                                      hooks=w_hooks, runner=w_runner,
                                      runner_type=w_runner_type)

        workload.pop("uuid")
        workload.pop("created_at")
        workload.pop("updated_at")

        self.assertEqual(
            {"_profiling_data": "",
             "statistics": {},
             "subtask_uuid": self.subtask_uuid,
             "task_uuid": self.task_uuid,
             "name": w_name, "description": w_description,
             "id": 1, "position": w_position,
             "args": w_args, "hooks": w_hooks,
             "contexts": w_contexts, "contexts_results": [],
             "runner": w_runner, "runner_type": w_runner_type,
             "full_duration": 0.0, "load_duration": 0.0,
             "failed_iteration_count": 0, "total_iteration_count": 0,
             "pass_sla": True, "sla": w_sla,
             "sla_results": {}}, workload)

    def test_workload_set_results_with_raw_data(self):
        workload = db.workload_create(self.task_uuid, self.subtask_uuid,
                                      name="foo", description="descr",
                                      position=0, args={},
                                      contexts={}, sla={},
                                      hooks=[], runner={},
                                      runner_type="foo")
        raw_data = {
            "raw": [
                {"error": "anError",
                 "duration": 1,
                 "idle_duration": 0,
                 "timestamp": 1,
                 "atomic_actions": [
                     {"name": "foo",
                      "started_at": 1,
                      "finished_at": 3,
                      "children": []}]},
                {"error": None,
                 "duration": 2,
                 "idle_duration": 0,
                 "timestamp": 1,
                 "atomic_actions": [
                     {"name": "foo",
                      "started_at": 1,
                      "finished_at": 2,
                      "children": []}]},
                {"error": None,
                 "duration": 0,
                 "idle_duration": 0,
                 "timestamp": 2,
                 "atomic_actions": [
                     {"name": "foo",
                      "started_at": 1,
                      "finished_at": 10,
                      "children": []}]}
            ],
        }
        sla_results = [{"s": "S", "success": True},
                       {"1": "2", "success": True},
                       {"a": "A", "success": True}]
        load_duration = 13
        full_duration = 42
        start_time = 33.33
        w_ctx_results = [{"name": "setup:something"}]

        db.workload_data_create(self.task_uuid, workload["uuid"], 0, raw_data)
        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=self.subtask_uuid,
                                task_uuid=self.task_uuid,
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results,
                                contexts_results=w_ctx_results)
        workload = db.workload_get(workload["uuid"])

        self.assertEqual(13, workload["load_duration"])
        self.assertEqual(42, workload["full_duration"])
        self.assertEqual(0, workload["min_duration"])
        self.assertEqual(2, workload["max_duration"])
        self.assertEqual(3, workload["total_iteration_count"])
        self.assertEqual(1, workload["failed_iteration_count"])
        self.assertTrue(workload["pass_sla"])
        self.assertEqual([], workload["hooks"])
        self.assertEqual(sla_results, workload["sla_results"]["sla"])
        self.assertEqual(load_duration, workload["load_duration"])
        self.assertEqual(full_duration, workload["full_duration"])
        self.assertEqual(start_time, workload["start_time"])
        self.assertEqual(self.task_uuid, workload["task_uuid"])
        self.assertEqual(self.subtask_uuid, workload["subtask_uuid"])

    def test_workload_set_results_empty_raw_data(self):
        workload = db.workload_create(self.task_uuid, self.subtask_uuid,
                                      name="foo", description="descr",
                                      position=0, args={},
                                      contexts={}, sla={},
                                      hooks=[], runner={},
                                      runner_type="foo")
        sla_results = [{"s": "S", "success": False},
                       {"1": "2", "success": True},
                       {"a": "A", "success": True}]
        load_duration = 13
        full_duration = 42
        start_time = 33.33
        w_ctx_results = [{"name": "setup:something"}]

        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=self.subtask_uuid,
                                task_uuid=self.task_uuid,
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results,
                                contexts_results=w_ctx_results)
        workload = db.workload_get(workload["uuid"])
        self.assertIsNone(workload["min_duration"])
        self.assertIsNone(workload["max_duration"])
        self.assertEqual(0, workload["total_iteration_count"])
        self.assertEqual(0, workload["failed_iteration_count"])
        self.assertFalse(workload["pass_sla"])
        self.assertEqual(sla_results, workload["sla_results"]["sla"])
        self.assertEqual(load_duration, workload["load_duration"])
        self.assertEqual(full_duration, workload["full_duration"])
        self.assertEqual(start_time, workload["start_time"])
        self.assertEqual(self.task_uuid, workload["task_uuid"])
        self.assertEqual(self.subtask_uuid, workload["subtask_uuid"])


class WorkloadDataTestCase(test.DBTestCase):
    def setUp(self):
        super(WorkloadDataTestCase, self).setUp()
        self.env = db.env_create(self.id(), "INIT", "", {}, {}, {}, [])
        self.task = db.task_create({"env_uuid": self.env["uuid"]})
        self.task_uuid = self.task["uuid"]
        self.subtask = db.subtask_create(self.task_uuid, title="foo")
        self.subtask_uuid = self.subtask["uuid"]
        self.workload = db.workload_create(
            self.task_uuid, self.subtask_uuid, name="atata", description="foo",
            position=0, args={}, contexts={}, sla={}, runner={},
            runner_type="r", hooks={})
        self.workload_uuid = self.workload["uuid"]

    def test_workload_data_create(self):
        data = {
            "raw": [
                {"error": "anError", "duration": 0, "timestamp": 1},
                {"duration": 1, "timestamp": 1},
                {"duration": 2, "timestamp": 2}
            ]
        }
        workload_data = db.workload_data_create(self.task_uuid,
                                                self.workload_uuid, 0, data)
        self.assertEqual(3, workload_data["iteration_count"])
        self.assertEqual(1, workload_data["failed_iteration_count"])
        self.assertEqual(dt.datetime.fromtimestamp(1),
                         workload_data["started_at"])
        self.assertEqual(dt.datetime.fromtimestamp(4),
                         workload_data["finished_at"])
        self.assertEqual(data, workload_data["chunk_data"])
        self.assertEqual(self.task_uuid, workload_data["task_uuid"])
        self.assertEqual(self.workload_uuid, workload_data["workload_uuid"])

    @mock.patch("time.time")
    def test_workload_data_create_empty(self, mock_time):
        mock_time.return_value = 10
        data = {"raw": []}
        workload_data = db.workload_data_create(self.task_uuid,
                                                self.workload_uuid, 0, data)
        self.assertEqual(0, workload_data["iteration_count"])
        self.assertEqual(0, workload_data["failed_iteration_count"])
        self.assertEqual(dt.datetime.fromtimestamp(10),
                         workload_data["started_at"])
        self.assertEqual(dt.datetime.fromtimestamp(10),
                         workload_data["finished_at"])
        self.assertEqual(data, workload_data["chunk_data"])
        self.assertEqual(self.task_uuid, workload_data["task_uuid"])
        self.assertEqual(self.workload_uuid, workload_data["workload_uuid"])


class EnvTestCase(test.DBTestCase):

    def test_env_get(self):
        env1 = db.env_create("name", "STATUS42", "descr", {}, {}, {}, [])
        env2 = db.env_create("name2", "STATUS42", "descr", {}, {}, {}, [])

        self.assertEqual(env1, db.env_get(env1["uuid"]))
        self.assertEqual(env1, db.env_get(env1["name"]))
        self.assertEqual(env2, db.env_get(env2["uuid"]))
        self.assertEqual(env2, db.env_get(env2["name"]))

    def test_env_get_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.env_get, "non-existing-env")

    def test_env_get_status(self):
        env = db.env_create("name", "STATUS42", "descr", {}, {}, {}, [])
        self.assertEqual("STATUS42", db.env_get_status(env["uuid"]))

    def test_env_get_status_non_existing(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.env_get_status, "non-existing-env")

    def test_env_list(self):
        for i in range(3):
            db.env_create("name %s" % i, "STATUS42", "descr", {}, {}, {}, [])
            self.assertEqual(i + 1, len(db.env_list()))

        all_ = db.env_list()
        self.assertIsInstance(all_, list)
        for env in all_:
            self.assertIsInstance(env, dict)

        self.assertEqual(set("name %s" % i for i in range(3)),
                         set(e["name"] for e in db.env_list()))

    def test_env_list_filter_by_status(self):
        db.env_create("name 1", "STATUS42", "descr", {}, {}, {}, [])
        db.env_create("name 2", "STATUS42", "descr", {}, {}, {}, [])
        db.env_create("name 3", "STATUS43", "descr", {}, {}, {}, [])

        result = db.env_list("STATUS42")
        self.assertEqual(2, len(result))
        self.assertEqual(set(["name 1", "name 2"]),
                         set(r["name"] for r in result))
        result = db.env_list("STATUS43")
        self.assertEqual(1, len(result))
        self.assertEqual("name 3", result[0]["name"])

    def test_env_create(self):
        env = db.env_create(
            "name", "status", "descr",
            {"extra": "test"}, {"conf": "c1"}, {"spec": "spec"}, [])

        self.assertIsInstance(env, dict)
        self.assertIsNotNone(env["uuid"])
        self.assertEqual(env, db.env_get(env["uuid"]))
        self.assertEqual("name", env["name"])
        self.assertEqual("status", env["status"])
        self.assertEqual("descr", env["description"])
        self.assertEqual({"conf": "c1"}, env["config"])
        self.assertEqual({"extra": "test"}, env["extras"])
        self.assertEqual({"spec": "spec"}, env["spec"])

    def test_env_create_duplicate_env(self):
        db.env_create("name", "status", "descr", {}, {}, {}, [])
        self.assertRaises(
            exceptions.DBRecordExists,
            db.env_create, "name", "status", "descr", {}, {}, {}, [])

    def teet_env_create_with_platforms(self):
        platforms = [
            {
                "status": "ANY",
                "plugin_name": "plugin_%s@plugin" % i,
                "plugin_spec": {},
                "platform_name": "plugin"
            }
            for i in range(3)
        ]
        env = db.env_create("name", "status", "descr", {}, {}, {}, platforms)
        db_platforms = db.platforms_list(env["uuid"])
        self.assertEqual(3, len(db_platforms))

    def test_env_rename(self):
        env = db.env_create("name", "status", "descr",
                            {"extra": "test"}, {"spec": "spec"}, {}, [])

        self.assertTrue(db.env_rename(env["uuid"], env["name"], "name2"))
        self.assertEqual("name2", db.env_get(env["uuid"])["name"])

    def test_env_rename_duplicate(self):
        env1 = db.env_create("name", "status", "descr", {}, {}, {}, [])
        env2 = db.env_create("name2", "status", "descr", {}, {}, {}, [])
        self.assertRaises(
            exceptions.DBRecordExists,
            db.env_rename, env1["uuid"], env1["name"], env2["name"])

    def test_env_update(self):
        env = db.env_create("name", "status", "descr", {}, {}, {}, [])
        self.assertTrue(db.env_update(env["uuid"]))
        self.assertTrue(
            db.env_update(env["uuid"], "another_descr", {"e": 123}, {"c": 1}))

        env = db.env_get(env["uuid"])
        self.assertEqual("another_descr", env["description"])
        self.assertEqual({"e": 123}, env["extras"])
        self.assertEqual({"c": 1}, env["config"])

    def test_evn_set_status(self):
        env = db.env_create("name", "status", "descr", {}, {}, {}, [])

        self.assertRaises(
            exceptions.DBConflict,
            db.env_set_status, env["uuid"], "wrong_old_status", "new_status")
        env = db.env_get(env["uuid"])
        self.assertEqual("status", env["status"])

        self.assertTrue(
            db.env_set_status(env["uuid"], "status", "new_status"))

        env = db.env_get(env["uuid"])
        self.assertEqual("new_status", env["status"])

    def test_env_delete_cascade(self):
        platforms = [
            {
                "status": "ANY",
                "plugin_name": "plugin_%s@plugin" % i,
                "plugin_spec": {},
                "platform_name": "plugin"
            }
            for i in range(3)
        ]
        env = db.env_create("name", "status", "descr", {}, {}, {}, platforms)
        db.env_delete_cascade(env["uuid"])

        self.assertEqual(0, len(db.env_list()))
        self.assertEqual(0, len(db.platforms_list(env["uuid"])))


class PlatformTestCase(test.DBTestCase):

    def setUp(self):
        super(PlatformTestCase, self).setUp()
        platforms = [
            {
                "status": "ANY",
                "plugin_name": "plugin_%s@plugin" % i,
                "plugin_spec": {},
                "platform_name": "plugin"
            }
            for i in range(5)
        ]
        self.env1 = db.env_create(
            "env1", "init", "", {}, {}, {}, platforms[:2])
        self.env2 = db.env_create(
            "env2", "init", "", {}, {}, {}, platforms[2:])

    def test_platform_get(self):
        for p in db.platforms_list(self.env1["uuid"]):
            self.assertEqual(p, db.platform_get(p["uuid"]))

    def test_platform_get_not_found(self):
        self.assertRaises(exceptions.DBRecordNotFound,
                          db.platform_get, "non_existing")

    def test_platforms_list(self):
        self.assertEqual(0, len(db.platforms_list("non_existing")))
        self.assertEqual(2, len(db.platforms_list(self.env1["uuid"])))
        self.assertEqual(3, len(db.platforms_list(self.env2["uuid"])))

    def test_platform_set_status(self):
        platforms = db.platforms_list(self.env1["uuid"])

        self.assertRaises(
            exceptions.DBConflict,
            db.platform_set_status,
            platforms[0]["uuid"], "OTHER", "NEW_STATUS")
        self.assertEqual("ANY",
                         db.platform_get(platforms[0]["uuid"])["status"])

        self.assertTrue(db.platform_set_status(
            platforms[0]["uuid"], "ANY", "NEW_STATUS"))
        self.assertEqual("NEW_STATUS",
                         db.platform_get(platforms[0]["uuid"])["status"])

        self.assertEqual("ANY",
                         db.platform_get(platforms[1]["uuid"])["status"])

    def test_platform_set_data(self):
        platforms = db.platforms_list(self.env1["uuid"])
        uuid = platforms[0]["uuid"]

        self.assertTrue(db.platform_set_data(uuid))
        self.assertTrue(
            db.platform_set_data(uuid, platform_data={"platform": "data"}))
        in_db = db.platform_get(uuid)
        self.assertEqual({"platform": "data"}, in_db["platform_data"])
        self.assertEqual({}, in_db["plugin_data"])

        self.assertTrue(
            db.platform_set_data(uuid, plugin_data={"plugin": "data"}))
        in_db = db.platform_get(uuid)
        self.assertEqual({"platform": "data"}, in_db["platform_data"])
        self.assertEqual({"plugin": "data"}, in_db["plugin_data"])

        self.assertTrue(
            db.platform_set_data(uuid, platform_data={"platform": "data2"}))
        in_db = db.platform_get(uuid)
        self.assertEqual({"platform": "data2"}, in_db["platform_data"])
        self.assertEqual({"plugin": "data"}, in_db["plugin_data"])

        self.assertFalse(db.platform_set_data(
            "non_existing", platform_data={}))
        in_db = db.platform_get(uuid)
        # just check that nothing changed after wrong uuid passed
        self.assertEqual({"platform": "data2"}, in_db["platform_data"])


class VerifierTestCase(test.DBTestCase):
    def test_verifier_create(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        self.assertEqual("a", v["name"])

    def test_verifier_get(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        self.assertEqual("a", db.verifier_get(v["uuid"])["name"])

    def test_verifier_get_raise_exc(self):
        self.assertRaises(exceptions.DBRecordNotFound, db.verifier_get, "1234")

    def test_verifier_list(self):
        v1 = db.verifier_create("a1", "b1", "c1", "d1", "e1", False)
        v2 = db.verifier_create("a2", "b2", "c2", "d2", "e2", False)
        vs = db.verifier_list()
        self.assertEqual(sorted([v1["uuid"], v2["uuid"]]),
                         sorted([v["uuid"] for v in vs]))

        v1 = db.verifier_update(v1["uuid"], status="foo")
        vs = db.verifier_list(status="foo")
        self.assertEqual(1, len(vs))
        self.assertEqual(v1["uuid"], vs[0]["uuid"])

    def test_verifier_delete(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        db.verifier_delete(v["uuid"])
        self.assertRaises(exceptions.DBRecordNotFound, db.verifier_delete,
                          v["uuid"])

    def test_verification_update(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        v = db.verifier_update(v["uuid"], source="foo", version="bar")
        self.assertEqual("foo", v["source"])
        self.assertEqual("bar", v["version"])


class VerificationTestCase(test.DBTestCase):
    def setUp(self):
        super(VerificationTestCase, self).setUp()

        self.verifier = db.verifier_create("a", "b", "c", "d", "e", False)
        self.env = db.env_create(self.id(), "INIT", "", {}, {}, {}, [])

    def _create_verification(self, tags=None, env_uuid=None):
        tags = tags or []
        verifier_uuid = self.verifier["uuid"]
        env_uuid = env_uuid or self.env["uuid"]
        return db.verification_create(verifier_uuid, env_uuid, tags, {})

    def test_verification_create(self):
        v = self._create_verification()
        self.assertEqual(self.verifier["uuid"], v["verifier_uuid"])
        self.assertEqual(self.env["uuid"], v["env_uuid"])

    def test_verification_get(self):
        v = db.verification_get(self._create_verification()["uuid"])
        self.assertEqual(self.verifier["uuid"], v["verifier_uuid"])
        self.assertEqual(self.env["uuid"], v["env_uuid"])

    def test_verification_get_raise_exc(self):
        self.assertRaises(exceptions.DBRecordNotFound, db.verification_get,
                          "1234")

    def test_verification_list(self):
        another_env = db.env_create(
            self.id() + "2", "INIT", "", {}, {}, {}, [])
        v1 = self._create_verification(tags=["foo", "bar"],
                                       env_uuid=another_env["uuid"])
        v2 = self._create_verification()

        vs = db.verification_list(self.verifier["uuid"])
        self.assertEqual(sorted([v1["uuid"], v2["uuid"]]),
                         sorted([v["uuid"] for v in vs]))

        vs = db.verification_list(self.verifier["uuid"], another_env["uuid"])
        self.assertEqual(1, len(vs))
        self.assertEqual(v1["uuid"], vs[0]["uuid"])

        vs = db.verification_list(tags=["bar"])
        self.assertEqual(1, len(vs))
        self.assertEqual(v1["uuid"], vs[0]["uuid"])

        v2 = db.verification_update(v2["uuid"], status="foo")
        vs = db.verification_list(status="foo")
        self.assertEqual(1, len(vs))
        self.assertEqual(v2["uuid"], vs[0]["uuid"])

    def test_verification_delete(self):
        v = self._create_verification()
        db.verification_delete(v["uuid"])
        self.assertRaises(exceptions.DBRecordNotFound, db.verification_delete,
                          v["uuid"])

    def test_verification_update(self):
        v = self._create_verification()
        v = db.verification_update(v["uuid"], status="foo", tests_count=10)
        self.assertEqual("foo", v["status"])
        self.assertEqual(10, v["tests_count"])
