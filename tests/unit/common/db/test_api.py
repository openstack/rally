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
import copy
import datetime as dt
import json

import ddt
import mock
from six import moves

from rally.common import db
from rally.common.db import api as db_api
import rally.common.db.sqlalchemy.api as s_api
from rally import consts
from rally import exceptions
from tests.unit import test


NOW = dt.datetime.now()


class FakeSerializable(object):
    def __init__(self, **kwargs):
        self.dict = {}
        self.dict.update(kwargs)

    def _as_dict(self):
        return self.dict


@ddt.ddt
class SerializeTestCase(test.DBTestCase):
    def setUp(self):
        super(SerializeTestCase, self).setUp()

    @ddt.data(
        {"data": 1, "serialized": 1},
        {"data": 1.1, "serialized": 1.1},
        {"data": "a string", "serialized": "a string"},
        {"data": NOW, "serialized": NOW},
        {"data": {"k1": 1, "k2": 2}, "serialized": {"k1": 1, "k2": 2}},
        {"data": [1, "foo"], "serialized": [1, "foo"]},
        {"data": ["foo", 1, {"a": "b"}], "serialized": ["foo", 1, {"a": "b"}]},
        {"data": FakeSerializable(a=1), "serialized": {"a": 1}},
        {"data": [FakeSerializable(a=1),
                  FakeSerializable(b=FakeSerializable(c=1))],
         "serialized": [{"a": 1}, {"b": {"c": 1}}]},
    )
    @ddt.unpack
    def test_serialize(self, data, serialized):

        @db_api.serialize
        def fake_method():
            return data

        results = fake_method()
        self.assertEqual(results, serialized)

    def test_serialize_value_error(self):

        @db_api.serialize
        def fake_method():
            class Fake(object):
                pass
            return Fake()

        self.assertRaises(ValueError, fake_method)


class ConnectionTestCase(test.DBTestCase):

    def test_schema_revision(self):
        rev = db.schema_revision()
        drev = db.schema_revision(detailed=True)
        self.assertEqual(drev["revision"], rev)
        self.assertEqual(drev["revision"], drev["current_head"])


class FixDeploymentTestCase(test.DBTestCase):
    def test_fix_deployment(self):
        deployment = {
            "credentials": [("bong", {"admin": "foo", "users": "bar"})]}

        expected = {
            "credentials": [("bong", {"admin": "foo", "users": "bar"})],
            "admin": "foo",
            "users": "bar"
        }

        @s_api.fix_deployment
        def get_deployment():
            return deployment

        fixed_deployment = get_deployment()
        self.assertEqual(fixed_deployment, expected)


class TasksTestCase(test.DBTestCase):
    def setUp(self):
        super(TasksTestCase, self).setUp()
        self.deploy = db.deployment_create({})

    def _get_task(self, uuid):
        return db.task_get(uuid)

    def _get_task_status(self, uuid):
        return db.task_get_status(uuid)

    def _create_task(self, values=None):
        values = values or {}
        if "deployment_uuid" not in values:
            values["deployment_uuid"] = self.deploy["uuid"]
        return db.task_create(values)

    def test_task_get_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_get, "f885f435-f6ca-4f3e-9b3e-aeb6837080f2")

    def test_task_get_status_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_get_status,
                          "f885f435-f6ca-4f3e-9b3e-aeb6837080f2")

    def test_task_create(self):
        task = self._create_task()
        db_task = self._get_task(task["uuid"])
        self.assertIsNotNone(db_task["uuid"])
        self.assertIsNotNone(db_task["id"])
        self.assertEqual(db_task["status"], consts.TaskStatus.INIT)

    def test_task_create_with_tag(self):
        task = self._create_task(values={"tag": "test_tag"})
        db_task = self._get_task(task["uuid"])
        self.assertIsNotNone(db_task["uuid"])
        self.assertIsNotNone(db_task["id"])
        self.assertEqual(db_task["status"], consts.TaskStatus.INIT)
        self.assertEqual(db_task["tag"], "test_tag")

    def test_task_create_without_uuid(self):
        _uuid = "19be8589-48b0-4af1-a369-9bebaaa563ab"
        task = self._create_task({"uuid": _uuid})
        db_task = self._get_task(task["uuid"])
        self.assertEqual(db_task["uuid"], _uuid)

    def test_task_update(self):
        task = self._create_task({})
        db.task_update(task["uuid"], {"status": consts.TaskStatus.FAILED})
        db_task = self._get_task(task["uuid"])
        self.assertEqual(db_task["status"], consts.TaskStatus.FAILED)

    def test_task_update_with_tag(self):
        task = self._create_task({})
        db.task_update(task["uuid"], {
            "status": consts.TaskStatus.FAILED,
            "tag": "test_tag"
        })
        db_task = self._get_task(task["uuid"])
        self.assertEqual(db_task["status"], consts.TaskStatus.FAILED)
        self.assertEqual(db_task["tag"], "test_tag")

    def test_task_update_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
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
            self.assertEqual(db_task["status"], status)

    def test_task_list_empty(self):
        self.assertEqual([], db.task_list())

    def test_task_list(self):
        INIT = consts.TaskStatus.INIT
        task_init = sorted(self._create_task()["uuid"] for i in moves.range(3))
        FINISHED = consts.TaskStatus.FINISHED
        task_finished = sorted(self._create_task(
            {"status": FINISHED,
             "deployment_uuid": self.deploy["uuid"]}
        )["uuid"] for i in moves.range(3))

        task_all = sorted(task_init + task_finished)

        def get_uuids(status=None, deployment=None):
            tasks = db.task_list(status=status, deployment=deployment)
            return sorted(task["uuid"] for task in tasks)

        self.assertEqual(task_all, get_uuids(None))

        self.assertEqual(task_init, get_uuids(status=INIT))
        self.assertEqual(task_finished, get_uuids(status=FINISHED))
        self.assertRaises(exceptions.DeploymentNotFound,
                          get_uuids, deployment="non-existing-deployment")

        deleted_task_uuid = task_finished.pop()
        db.task_delete(deleted_task_uuid)
        self.assertEqual(task_init, get_uuids(INIT))
        self.assertEqual(sorted(task_finished), get_uuids(FINISHED))

    def test_task_delete(self):
        task1, task2 = self._create_task()["uuid"], self._create_task()["uuid"]
        db.task_delete(task1)
        self.assertRaises(exceptions.TaskNotFound, self._get_task, task1)
        self.assertEqual(task2, self._get_task(task2)["uuid"])

    def test_task_delete_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_delete,
                          "da6f820c-b133-4b9f-8534-4c3bcc40724b")

    def test_task_delete_with_results(self):
        task_id = self._create_task()["uuid"]
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"}
            }
        }
        data = {
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42
        }
        subtask = db.subtask_create(task_id, title="foo")
        workload = db.workload_create(task_id, subtask["uuid"], key)
        db.workload_data_create(task_id, workload["uuid"], 0, {"raw": []})
        db.workload_set_results(workload["uuid"], data)

        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(len(res), 1)
        db.task_delete(task_id)
        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(len(res), 0)

    def test_task_delete_by_uuid_and_status(self):
        values = {
            "status": consts.TaskStatus.FINISHED,
        }
        task1 = self._create_task(values=values)["uuid"]
        task2 = self._create_task(values=values)["uuid"]
        db.task_delete(task1, status=consts.TaskStatus.FINISHED)
        self.assertRaises(exceptions.TaskNotFound, self._get_task, task1)
        self.assertEqual(task2, self._get_task(task2)["uuid"])

    def test_task_delete_by_uuid_and_status_invalid(self):
        task = self._create_task(
            values={"status": consts.TaskStatus.INIT})["uuid"]
        self.assertRaises(exceptions.TaskInvalidStatus, db.task_delete, task,
                          status=consts.TaskStatus.FINISHED)

    def test_task_delete_by_uuid_and_status_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_delete,
                          "fcd0483f-a405-44c4-b712-99c9e52254eb",
                          status=consts.TaskStatus.FINISHED)

    def test_task_result_get_all_by_uuid(self):
        task1 = self._create_task()["uuid"]
        task2 = self._create_task()["uuid"]
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"task_id": "task_id"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"},
                "hooks": [],
            }
        }
        data = {
            "sla": [{"success": True}],
            "load_duration": 13,
            "full_duration": 42,
            "hooks": [],
        }

        for task_id in (task1, task2):
            key["kw"]["args"]["task_id"] = task_id
            data["sla"][0] = {"success": True}
            subtask = db.subtask_create(task_id, title="foo")
            workload = db.workload_create(task_id, subtask["uuid"], key)
            db.workload_data_create(task_id, workload["uuid"], 0, {"raw": []})
            db.workload_set_results(workload["uuid"], data)

        for task_id in (task1, task2):
            res = db.task_result_get_all_by_uuid(task_id)
            key["kw"]["args"]["task_id"] = task_id
            data["sla"][0] = {"success": True}
            data["raw"] = []
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["key"], key)
            self.assertEqual(res[0]["data"], data)

    def test_task_get_detailed(self):
        validation_result = {
            "etype": "FooError",
            "msg": "foo message",
            "trace": "foo t/b",
        }
        task1 = self._create_task({"validation_result": validation_result,
                                   "tag": "bar"})
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"},
                "hooks": [],
            }
        }
        data = {
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42,
            "hooks": [],
        }

        subtask = db.subtask_create(task1["uuid"], title="foo")
        workload = db.workload_create(task1["uuid"], subtask["uuid"], key)
        db.workload_data_create(
            task1["uuid"], workload["uuid"], 0, {"raw": []})
        db.workload_set_results(workload["uuid"], data)

        task1_full = db.task_get_detailed(task1["uuid"])
        self.assertEqual(validation_result,
                         json.loads(task1_full["verification_log"]))
        self.assertEqual("bar", task1_full["tag"])
        results = task1_full["results"]
        self.assertEqual(1, len(results))
        self.assertEqual(key, results[0]["key"])
        self.assertEqual({
            "raw": [],
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42,
            "hooks": [],
        }, results[0]["data"])

    def test_task_get_detailed_last(self):
        task1 = self._create_task()
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"},
                "hooks": [],
            }
        }
        data = {
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42,
            "hooks": [],
        }

        subtask = db.subtask_create(task1["uuid"], title="foo")
        workload = db.workload_create(task1["uuid"], subtask["uuid"], key)
        db.workload_data_create(
            task1["uuid"], workload["uuid"], 0, {"raw": []})
        db.workload_set_results(workload["uuid"], data)

        task1_full = db.task_get_detailed_last()
        results = task1_full["results"]
        self.assertEqual(1, len(results))
        self.assertEqual(key, results[0]["key"])
        self.assertEqual({
            "raw": [],
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42,
            "hooks": [],
        }, results[0]["data"])

    def test_task_result_create(self):
        task_id = self._create_task()["uuid"]
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "hooks": [{"name": "foo_hook", "args": "bar",
                           "trigger": {"name": "foo_trigger", "args": "baz"}}],
                "runner": {"r": "R", "type": "T"}
            }
        }
        raw_data = {
            "raw": [
                {"error": "anError", "duration": 0, "timestamp": 1},
                {"duration": 1, "timestamp": 1},
                {"duration": 2, "timestamp": 2}
            ],
        }
        data = {
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42,
            "hooks": [
                {"config": {"name": "foo_hook", "args": "bar",
                            "trigger": {"name": "foo_trigger", "args": "baz"}},
                 "results": [
                    {"status": "success", "started_at": 10.0,
                     "finished_at": 11.0, "triggered_by": {"time": 5}}],
                 "summary": {}}
            ],
        }

        subtask = db.subtask_create(task_id, title="foo")
        workload = db.workload_create(task_id, subtask["uuid"], key)
        db.workload_data_create(task_id, workload["uuid"], 0, raw_data)
        db.workload_set_results(workload["uuid"], data)

        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(1, len(res))
        self.assertEqual(raw_data["raw"], res[0]["data"]["raw"])
        self.assertEqual(key, res[0]["key"])

    def test_task_multiple_raw_result_create(self):
        task_id = self._create_task()["uuid"]
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"},
                "hooks": [],
            }
        }

        subtask = db.subtask_create(task_id, title="foo")
        workload = db.workload_create(task_id, subtask["uuid"], key)

        db.workload_data_create(task_id, workload["uuid"], 0, {
            "raw": [
                {"error": "anError", "timestamp": 10, "duration": 1},
                {"duration": 1, "timestamp": 10, "duration": 1},
                {"duration": 2, "timestamp": 10, "duration": 1},
                {"duration": 3, "timestamp": 10, "duration": 1},
            ],
        })

        db.workload_data_create(task_id, workload["uuid"], 1, {
            "raw": [
                {"error": "anError2", "timestamp": 10, "duration": 1},
                {"duration": 6, "timestamp": 10, "duration": 1},
                {"duration": 5, "timestamp": 10, "duration": 1},
                {"duration": 4, "timestamp": 10, "duration": 1},
            ],
        })

        db.workload_data_create(task_id, workload["uuid"], 2, {
            "raw": [
                {"duration": 7, "timestamp": 10, "duration": 1},
                {"duration": 8, "timestamp": 10, "duration": 1},
            ],
        })

        db.workload_set_results(workload["uuid"], {
            "sla": [{"success": True}],
            "load_duration": 13,
            "full_duration": 42
        })

        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["key"], key)
        self.assertEqual(res[0]["data"], {
            "raw": [
                {"error": "anError", "timestamp": 10, "duration": 1},
                {"duration": 1, "timestamp": 10, "duration": 1},
                {"duration": 2, "timestamp": 10, "duration": 1},
                {"duration": 3, "timestamp": 10, "duration": 1},
                {"error": "anError2", "timestamp": 10, "duration": 1},
                {"duration": 6, "timestamp": 10, "duration": 1},
                {"duration": 5, "timestamp": 10, "duration": 1},
                {"duration": 4, "timestamp": 10, "duration": 1},
                {"duration": 7, "timestamp": 10, "duration": 1},
                {"duration": 8, "timestamp": 10, "duration": 1},
            ],
            "sla": [{"success": True}],
            "hooks": [],
            "load_duration": 13,
            "full_duration": 42
        })

        db.task_delete(task_id)
        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(len(res), 0)


class SubtaskTestCase(test.DBTestCase):
    def setUp(self):
        super(SubtaskTestCase, self).setUp()
        self.deploy = db.deployment_create({})
        self.task = db.task_create({"deployment_uuid": self.deploy["uuid"]})

    def test_subtask_create(self):
        subtask = db.subtask_create(self.task["uuid"], title="foo")
        self.assertEqual("foo", subtask["title"])
        self.assertEqual(self.task["uuid"], subtask["task_uuid"])


class WorkloadTestCase(test.DBTestCase):
    def setUp(self):
        super(WorkloadTestCase, self).setUp()
        self.deploy = db.deployment_create({})
        self.task = db.task_create({"deployment_uuid": self.deploy["uuid"]})
        self.task_uuid = self.task["uuid"]
        self.subtask = db.subtask_create(self.task_uuid, title="foo")
        self.subtask_uuid = self.subtask["uuid"]

    def test_workload_create(self):
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"}
            }
        }
        workload = db.workload_create(self.task_uuid, self.subtask_uuid, key)
        self.assertEqual("atata", workload["name"])
        self.assertEqual(0, workload["position"])
        self.assertEqual({"a": "A"}, workload["args"])
        self.assertEqual({"c": "C"}, workload["context"])
        self.assertEqual({"s": "S"}, workload["sla"])
        self.assertEqual({"r": "R", "type": "T"}, workload["runner"])
        self.assertEqual("T", workload["runner_type"])
        self.assertEqual(self.task_uuid, workload["task_uuid"])
        self.assertEqual(self.subtask_uuid, workload["subtask_uuid"])

    def test_workload_set_results_with_raw_data(self):
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"}
            }
        }
        raw_data = {
            "raw": [
                {"error": "anError", "duration": 0, "timestamp": 1},
                {"duration": 1, "timestamp": 1},
                {"duration": 2, "timestamp": 2}
            ],
        }
        data = {
            "sla": [
                {"s": "S", "success": True},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42
        }

        workload = db.workload_create(self.task_uuid, self.subtask_uuid, key)
        db.workload_data_create(self.task_uuid, workload["uuid"], 0, raw_data)
        workload = db.workload_set_results(workload["uuid"], data)
        self.assertEqual("atata", workload["name"])
        self.assertEqual(0, workload["position"])
        self.assertEqual({"a": "A"}, workload["args"])
        self.assertEqual({"c": "C"}, workload["context"])
        self.assertEqual({"s": "S"}, workload["sla"])
        self.assertEqual({"r": "R", "type": "T"}, workload["runner"])
        self.assertEqual("T", workload["runner_type"])
        self.assertEqual(13, workload["load_duration"])
        self.assertEqual(42, workload["full_duration"])
        self.assertEqual(0, workload["min_duration"])
        self.assertEqual(2, workload["max_duration"])
        self.assertEqual(3, workload["total_iteration_count"])
        self.assertEqual(1, workload["failed_iteration_count"])
        self.assertTrue(workload["pass_sla"])
        self.assertEqual([], workload["hooks"])
        self.assertEqual(data["sla"], workload["sla_results"]["sla"])
        self.assertEqual(self.task_uuid, workload["task_uuid"])
        self.assertEqual(self.subtask_uuid, workload["subtask_uuid"])

    def test_workload_set_results_empty_raw_data(self):
        key = {
            "name": "atata",
            "pos": 0,
            "kw": {
                "args": {"a": "A"},
                "context": {"c": "C"},
                "sla": {"s": "S"},
                "runner": {"r": "R", "type": "T"}
            }
        }
        data = {
            "sla": [
                {"s": "S", "success": False},
                {"1": "2", "success": True},
                {"a": "A", "success": True}
            ],
            "load_duration": 13,
            "full_duration": 42
        }

        workload = db.workload_create(self.task_uuid, self.subtask_uuid, key)
        workload = db.workload_set_results(workload["uuid"], data)
        self.assertEqual("atata", workload["name"])
        self.assertEqual(0, workload["position"])
        self.assertEqual({"a": "A"}, workload["args"])
        self.assertEqual({"c": "C"}, workload["context"])
        self.assertEqual({"s": "S"}, workload["sla"])
        self.assertEqual({"r": "R", "type": "T"}, workload["runner"])
        self.assertEqual("T", workload["runner_type"])
        self.assertEqual(13, workload["load_duration"])
        self.assertEqual(42, workload["full_duration"])
        self.assertEqual(0, workload["min_duration"])
        self.assertEqual(0, workload["max_duration"])
        self.assertEqual(0, workload["total_iteration_count"])
        self.assertEqual(0, workload["failed_iteration_count"])
        self.assertFalse(workload["pass_sla"])
        self.assertEqual([], workload["hooks"])
        self.assertEqual(data["sla"], workload["sla_results"]["sla"])
        self.assertEqual(self.task_uuid, workload["task_uuid"])
        self.assertEqual(self.subtask_uuid, workload["subtask_uuid"])


class WorkloadDataTestCase(test.DBTestCase):
    def setUp(self):
        super(WorkloadDataTestCase, self).setUp()
        self.deploy = db.deployment_create({})
        self.task = db.task_create({"deployment_uuid": self.deploy["uuid"]})
        self.task_uuid = self.task["uuid"]
        self.subtask = db.subtask_create(self.task_uuid, title="foo")
        self.subtask_uuid = self.subtask["uuid"]
        self.key = {"name": "atata", "pos": 0, "kw": {"runner": {"r": "R",
                                                                 "type": "T"}}}
        self.workload = db.workload_create(self.task_uuid, self.subtask_uuid,
                                           self.key)
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


class DeploymentTestCase(test.DBTestCase):
    def test_deployment_create(self):
        deploy = db.deployment_create({"config": {"opt": "val"}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploy["uuid"], deploys[0]["uuid"])
        self.assertEqual(deploy["status"], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy["config"], {"opt": "val"})
        self.assertEqual(deploy["credentials"],
                         [["openstack", {"admin": None, "users": []}]])

    def test_deployment_create_several(self):
        # Create a deployment
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 0)
        deploy_one = db.deployment_create({"config": {"opt1": "val1"}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploy_one["uuid"], deploys[0]["uuid"])
        self.assertEqual(deploy_one["status"], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy_one["config"], {"opt1": "val1"})

        # Create another deployment and sure that they are different
        deploy_two = db.deployment_create({"config": {"opt2": "val2"}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 2)
        self.assertEqual(set([deploy_one["uuid"], deploy_two["uuid"]]),
                         set([deploy["uuid"] for deploy in deploys]))
        self.assertNotEqual(deploy_one["uuid"], deploy_two["uuid"])
        self.assertEqual(deploy_two["status"], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy_two["config"], {"opt2": "val2"})

    def test_deployment_update(self):
        credentials = {"admin": {"foo": "bar"}, "users": ["foo_user"]}
        deploy = db.deployment_create(copy.deepcopy(credentials))
        self.assertEqual(deploy["config"], {})
        self.assertEqual(deploy["credentials"], [["openstack", credentials]])
        update_deploy = db.deployment_update(deploy["uuid"],
                                             {"config": {"opt": "val"}})
        self.assertEqual(update_deploy["uuid"], deploy["uuid"])
        self.assertEqual(update_deploy["config"], {"opt": "val"})
        self.assertEqual(update_deploy["credentials"],
                         [["openstack", credentials]])
        get_deploy = db.deployment_get(deploy["uuid"])
        self.assertEqual(get_deploy["uuid"], deploy["uuid"])
        self.assertEqual(get_deploy["config"], {"opt": "val"})
        self.assertEqual(update_deploy["credentials"],
                         [["openstack", credentials]])

    def test_deployment_update_several(self):
        # Create a deployment and update it
        deploy_one = db.deployment_create({})
        self.assertEqual(deploy_one["config"], {})
        update_deploy_one = db.deployment_update(
            deploy_one["uuid"], {"config": {"opt1": "val1"}})
        self.assertEqual(update_deploy_one["uuid"], deploy_one["uuid"])
        self.assertEqual(update_deploy_one["config"], {"opt1": "val1"})
        get_deploy_one = db.deployment_get(deploy_one["uuid"])
        self.assertEqual(get_deploy_one["uuid"], deploy_one["uuid"])
        self.assertEqual(get_deploy_one["config"], {"opt1": "val1"})

        # Create another deployment
        deploy_two = db.deployment_create({})
        update_deploy_two = db.deployment_update(
            deploy_two["uuid"], {"config": {"opt2": "val2"}})
        self.assertEqual(update_deploy_two["uuid"], deploy_two["uuid"])
        self.assertEqual(update_deploy_two["config"], {"opt2": "val2"})
        get_deploy_one_again = db.deployment_get(deploy_one["uuid"])
        self.assertEqual(get_deploy_one_again["uuid"], deploy_one["uuid"])
        self.assertEqual(get_deploy_one_again["config"], {"opt1": "val1"})

    def test_deployment_get(self):
        deploy_one = db.deployment_create({"config": {"opt1": "val1"}})
        deploy_two = db.deployment_create({"config": {"opt2": "val2"}})
        get_deploy_one = db.deployment_get(deploy_one["uuid"])
        get_deploy_two = db.deployment_get(deploy_two["uuid"])
        self.assertNotEqual(get_deploy_one["uuid"], get_deploy_two["uuid"])
        self.assertEqual(get_deploy_one["config"], {"opt1": "val1"})
        self.assertEqual(get_deploy_two["config"], {"opt2": "val2"})

    def test_deployment_get_not_found(self):
        self.assertRaises(exceptions.DeploymentNotFound,
                          db.deployment_get,
                          "852e932b-9552-4b2d-89e3-a5915780a5e3")

    def test_deployment_list(self):
        deploy_one = db.deployment_create({})
        deploy_two = db.deployment_create({})
        deploys = db.deployment_list()
        self.assertEqual(sorted([deploy_one["uuid"], deploy_two["uuid"]]),
                         sorted([deploy["uuid"] for deploy in deploys]))

    def test_deployment_list_with_status_and_name(self):
        deploy_one = db.deployment_create({})
        deploy_two = db.deployment_create({
            "config": {},
            "status": consts.DeployStatus.DEPLOY_FAILED,
        })
        deploy_three = db.deployment_create({"name": "deployment_name"})
        deploys = db.deployment_list(status=consts.DeployStatus.DEPLOY_INIT)
        deploys.sort(key=lambda x: x["id"])
        self.assertEqual(len(deploys), 2)
        self.assertEqual(deploys[0]["uuid"], deploy_one["uuid"])
        deploys = db.deployment_list(status=consts.DeployStatus.DEPLOY_FAILED)
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploys[0]["uuid"], deploy_two["uuid"])
        deploys = db.deployment_list(
            status=consts.DeployStatus.DEPLOY_FINISHED)
        self.assertEqual(len(deploys), 0)
        deploys = db.deployment_list(name="deployment_name")
        self.assertEqual(deploys[0]["uuid"], deploy_three["uuid"])
        self.assertEqual(len(deploys), 1)

    def test_deployment_list_parent(self):
        deploy = db.deployment_create({})
        subdeploy1 = db.deployment_create({"parent_uuid": deploy["uuid"]})
        subdeploy2 = db.deployment_create({"parent_uuid": deploy["uuid"]})
        self.assertEqual(
            [deploy["uuid"]], [d["uuid"] for d in db.deployment_list()])
        subdeploys = db.deployment_list(parent_uuid=deploy["uuid"])
        self.assertEqual(set([subdeploy1["uuid"], subdeploy2["uuid"]]),
                         set([d["uuid"] for d in subdeploys]))

    def test_deployment_delete(self):
        deploy_one = db.deployment_create({})
        deploy_two = db.deployment_create({})
        db.deployment_delete(deploy_two["uuid"])
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploys[0]["uuid"], deploy_one["uuid"])

    def test_deployment_delete_not_found(self):
        self.assertRaises(exceptions.DeploymentNotFound,
                          db.deployment_delete,
                          "5f2883be-46c8-4c4b-a4fe-988ad0c6b20a")

    def test_deployment_delete_is_busy(self):
        deployment = db.deployment_create({})
        db.resource_create({"deployment_uuid": deployment["uuid"]})
        db.resource_create({"deployment_uuid": deployment["uuid"]})
        self.assertRaises(exceptions.DeploymentIsBusy, db.deployment_delete,
                          deployment["uuid"])


class ResourceTestCase(test.DBTestCase):
    def test_create(self):
        deployment = db.deployment_create({})
        resource = db.resource_create({
            "deployment_uuid": deployment["uuid"],
            "provider_name": "fakeprovider",
            "type": "faketype",
        })
        resources = db.resource_get_all(deployment["uuid"])
        self.assertTrue(resource["id"])
        self.assertEqual(len(resources), 1)
        self.assertTrue(resource["id"], resources[0]["id"])
        self.assertEqual(resource["deployment_uuid"], deployment["uuid"])
        self.assertEqual(resource["provider_name"], "fakeprovider")
        self.assertEqual(resource["type"], "faketype")

    def test_delete(self):
        deployment = db.deployment_create({})
        res = db.resource_create({"deployment_uuid": deployment["uuid"]})
        db.resource_delete(res["id"])
        resources = db.resource_get_all(deployment["uuid"])
        self.assertEqual(len(resources), 0)

    def test_delete_not_found(self):
        self.assertRaises(exceptions.ResourceNotFound,
                          db.resource_delete, 123456789)

    def test_get_all(self):
        deployment0 = db.deployment_create({})
        deployment1 = db.deployment_create({})
        res0 = db.resource_create({"deployment_uuid": deployment0["uuid"]})
        res1 = db.resource_create({"deployment_uuid": deployment1["uuid"]})
        res2 = db.resource_create({"deployment_uuid": deployment1["uuid"]})
        resources = db.resource_get_all(deployment1["uuid"])
        self.assertEqual(sorted([res1["id"], res2["id"]]),
                         sorted([r["id"] for r in resources]))
        resources = db.resource_get_all(deployment0["uuid"])
        self.assertEqual(len(resources), 1)
        self.assertEqual(res0["id"], resources[0]["id"])

    def test_get_all_by_provider_name(self):
        deployment = db.deployment_create({})
        res_one = db.resource_create({
            "deployment_uuid": deployment["uuid"],
            "provider_name": "one",
        })
        res_two = db.resource_create({
            "deployment_uuid": deployment["uuid"],
            "provider_name": "two",
        })
        resources = db.resource_get_all(deployment["uuid"],
                                        provider_name="one")
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_one["id"], resources[0]["id"])
        resources = db.resource_get_all(deployment["uuid"],
                                        provider_name="two")
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_two["id"], resources[0]["id"])

    def test_get_all_by_provider_type(self):
        deployment = db.deployment_create({})
        res_one = db.resource_create({
            "deployment_uuid": deployment["uuid"],
            "type": "one",
        })
        res_two = db.resource_create({
            "deployment_uuid": deployment["uuid"],
            "type": "two",
        })
        resources = db.resource_get_all(deployment["uuid"], type="one")
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_one["id"], resources[0]["id"])
        resources = db.resource_get_all(deployment["uuid"], type="two")
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_two["id"], resources[0]["id"])


class VerifierTestCase(test.DBTestCase):

    def test_verifier_create(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        self.assertEqual("a", v["name"])

    def test_verifier_get(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        self.assertEqual("a", db.verifier_get(v["uuid"])["name"])

    def test_verifier_get_raise_exc(self):
        self.assertRaises(exceptions.ResourceNotFound, db.verifier_get, "1234")

    def test_verifier_list(self):
        v1 = db.verifier_create("a1", "b1", "c1", "d1", "e1", False)
        v2 = db.verifier_create("a2", "b2", "c2", "d2", "e2", False)
        vs = db.verifier_list()
        self.assertEqual(sorted([v1["uuid"], v2["uuid"]]),
                         sorted([v["uuid"] for v in vs]))

        v1 = db.verifier_update(v1["uuid"], status="foo")
        vs = db.verifier_list(status="foo")
        self.assertEqual(len(vs), 1)
        self.assertEqual(v1["uuid"], vs[0]["uuid"])

    def test_verifier_delete(self):
        v = db.verifier_create("a", "b", "c", "d", "e", False)
        db.verifier_delete(v["uuid"])
        self.assertRaises(exceptions.ResourceNotFound, db.verifier_delete,
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
        self.deploy = db.deployment_create({})

    def _create_verification(self):
        verifier_uuid = self.verifier["uuid"]
        deployment_uuid = self.deploy["uuid"]
        return db.verification_create(verifier_uuid, deployment_uuid, {})

    def test_verification_create(self):
        v = self._create_verification()
        self.assertEqual(self.verifier["uuid"], v["verifier_uuid"])
        self.assertEqual(self.deploy["uuid"], v["deployment_uuid"])

    def test_verification_get(self):
        v = db.verification_get(self._create_verification()["uuid"])
        self.assertEqual(self.verifier["uuid"], v["verifier_uuid"])
        self.assertEqual(self.deploy["uuid"], v["deployment_uuid"])

    def test_verification_get_raise_exc(self):
        self.assertRaises(exceptions.ResourceNotFound, db.verification_get,
                          "1234")

    def test_verification_list(self):
        deploy = db.deployment_create({})
        v1 = db.verification_create(self.verifier["uuid"], deploy["uuid"], {})
        v2 = self._create_verification()

        vs = db.verification_list(self.verifier["uuid"])
        self.assertEqual(sorted([v1["uuid"], v2["uuid"]]),
                         sorted([v["uuid"] for v in vs]))

        vs = db.verification_list(self.verifier["uuid"], deploy["uuid"])
        self.assertEqual(len(vs), 1)
        self.assertEqual(v1["uuid"], vs[0]["uuid"])

        v2 = db.verification_update(v2["uuid"], status="foo")
        vs = db.verification_list(status="foo")
        self.assertEqual(len(vs), 1)
        self.assertEqual(v2["uuid"], vs[0]["uuid"])

    def test_verification_delete(self):
        v = self._create_verification()
        db.verification_delete(v["uuid"])
        self.assertRaises(exceptions.ResourceNotFound, db.verification_delete,
                          v["uuid"])

    def test_verification_update(self):
        v = self._create_verification()
        v = db.verification_update(v["uuid"], status="foo", tests_count=10)
        self.assertEqual("foo", v["status"])
        self.assertEqual(10, v["tests_count"])


class WorkerTestCase(test.DBTestCase):
    def setUp(self):
        super(WorkerTestCase, self).setUp()
        self.worker = db.register_worker({"hostname": "test"})

    def test_register_worker_duplicate(self):
        self.assertRaises(exceptions.WorkerAlreadyRegistered,
                          db.register_worker, {"hostname": "test"})

    def test_get_worker(self):
        worker = db.get_worker("test")
        self.assertEqual(self.worker["id"], worker["id"])
        self.assertEqual(self.worker["hostname"], worker["hostname"])

    def test_get_worker_not_found(self):
        self.assertRaises(exceptions.WorkerNotFound, db.get_worker, "notfound")

    def test_unregister_worker(self):
        db.unregister_worker("test")
        self.assertRaises(exceptions.WorkerNotFound, db.get_worker, "test")

    def test_unregister_worker_not_found(self):
        self.assertRaises(exceptions.WorkerNotFound,
                          db.unregister_worker, "fake")

    def test_update_worker(self):
        db.update_worker("test")
        worker = db.get_worker("test")
        self.assertNotEqual(self.worker["updated_at"], worker["updated_at"])

    def test_update_worker_not_found(self):
        self.assertRaises(exceptions.WorkerNotFound, db.update_worker, "fake")
