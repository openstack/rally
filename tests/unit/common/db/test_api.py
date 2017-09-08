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

import mock
from six import moves

from rally.common import db
from rally import consts
from rally import exceptions
from tests.unit import test

NOW = dt.datetime.now()


class ConnectionTestCase(test.DBTestCase):
    def test_schema_revision(self):
        rev = db.schema_revision()
        drev = db.schema_revision(detailed=True)
        self.assertEqual(drev["revision"], rev)
        self.assertEqual(drev["revision"], drev["current_head"])


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
            self.assertEqual(status, db_task["status"])

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
        w_context = {"c": "C"}
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

        subtask = db.subtask_create(task1["uuid"], title="foo")
        workload = db.workload_create(task1["uuid"], subtask["uuid"],
                                      name=w_name, description=w_description,
                                      position=w_position, args=w_args,
                                      context=w_context, sla=w_sla,
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
                                start_time=w_start_time)

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
             "args": w_args, "context": w_context, "hooks": w_hooks,
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
                                      context={}, sla={}, runner={},
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

        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=workload["subtask_uuid"],
                                task_uuid=workload["task_uuid"],
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results)

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

        db.task_delete(task_id)


class SubtaskTestCase(test.DBTestCase):
    def setUp(self):
        super(SubtaskTestCase, self).setUp()
        self.deploy = db.deployment_create({})
        self.task = db.task_create({"deployment_uuid": self.deploy["uuid"]})

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
        self.deploy = db.deployment_create({})
        self.task = db.task_create({"deployment_uuid": self.deploy["uuid"]})
        self.task_uuid = self.task["uuid"]
        self.subtask = db.subtask_create(self.task_uuid, title="foo")
        self.subtask_uuid = self.subtask["uuid"]

    def test_workload_create(self):
        w_name = "atata"
        w_description = "tatata"
        w_position = 0
        w_args = {"a": "A"}
        w_context = {"c": "C"}
        w_sla = {"s": "S"}
        w_runner = {"r": "R", "type": "T"}
        w_runner_type = "T"
        w_hooks = []

        workload = db.workload_create(self.task_uuid, self.subtask_uuid,
                                      name=w_name, description=w_description,
                                      position=w_position, args=w_args,
                                      context=w_context, sla=w_sla,
                                      hooks=w_hooks, runner=w_runner,
                                      runner_type=w_runner_type)

        workload.pop("uuid")
        workload.pop("created_at")
        workload.pop("updated_at")

        self.assertEqual(
            {"context_execution": {},
             "statistics": {},
             "subtask_uuid": self.subtask_uuid,
             "task_uuid": self.task_uuid,
             "name": w_name, "description": w_description,
             "id": 1, "position": w_position,
             "args": w_args, "context": w_context, "hooks": w_hooks,
             "runner": w_runner, "runner_type": w_runner_type,
             "full_duration": 0.0, "load_duration": 0.0,
             "failed_iteration_count": 0, "total_iteration_count": 0,
             "pass_sla": True, "sla": w_sla,
             "sla_results": {}}, workload)

    def test_workload_set_results_with_raw_data(self):
        workload = db.workload_create(self.task_uuid, self.subtask_uuid,
                                      name="foo", description="descr",
                                      position=0, args={},
                                      context={}, sla={},
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

        db.workload_data_create(self.task_uuid, workload["uuid"], 0, raw_data)
        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=self.subtask_uuid,
                                task_uuid=self.task_uuid,
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results)
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
                                      context={}, sla={},
                                      hooks=[], runner={},
                                      runner_type="foo")
        sla_results = [{"s": "S", "success": False},
                       {"1": "2", "success": True},
                       {"a": "A", "success": True}]
        load_duration = 13
        full_duration = 42
        start_time = 33.33

        db.workload_set_results(workload_uuid=workload["uuid"],
                                subtask_uuid=self.subtask_uuid,
                                task_uuid=self.task_uuid,
                                load_duration=load_duration,
                                full_duration=full_duration,
                                start_time=start_time,
                                sla_results=sla_results)
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
        self.deploy = db.deployment_create({})
        self.task = db.task_create({"deployment_uuid": self.deploy["uuid"]})
        self.task_uuid = self.task["uuid"]
        self.subtask = db.subtask_create(self.task_uuid, title="foo")
        self.subtask_uuid = self.subtask["uuid"]
        self.workload = db.workload_create(
            self.task_uuid, self.subtask_uuid, name="atata", description="foo",
            position=0, args={}, context={}, sla={}, runner={},
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


class DeploymentTestCase(test.DBTestCase):
    def test_deployment_create(self):
        deploy = db.deployment_create({"config": {"opt": "val"}})
        deploys = db.deployment_list()
        self.assertEqual(1, len(deploys))
        self.assertEqual(deploys[0]["uuid"], deploy["uuid"])
        self.assertEqual(consts.DeployStatus.DEPLOY_INIT, deploy["status"])
        self.assertEqual({"opt": "val"}, deploy["config"])
        self.assertEqual({}, deploy["credentials"])

    def test_deployment_create_several(self):
        # Create a deployment
        deploys = db.deployment_list()
        self.assertEqual(0, len(deploys))
        deploy_one = db.deployment_create({"config": {"opt1": "val1"}})
        deploys = db.deployment_list()
        self.assertEqual(1, len(deploys))
        self.assertEqual(deploys[0]["uuid"], deploy_one["uuid"])
        self.assertEqual(consts.DeployStatus.DEPLOY_INIT, deploy_one["status"])
        self.assertEqual({"opt1": "val1"}, deploy_one["config"])

        # Create another deployment and sure that they are different
        deploy_two = db.deployment_create({"config": {"opt2": "val2"}})
        deploys = db.deployment_list()
        self.assertEqual(2, len(deploys))
        self.assertEqual(set([deploy_one["uuid"], deploy_two["uuid"]]),
                         set([deploy["uuid"] for deploy in deploys]))
        self.assertNotEqual(deploy_one["uuid"], deploy_two["uuid"])
        self.assertEqual(consts.DeployStatus.DEPLOY_INIT, deploy_two["status"])
        self.assertEqual({"opt2": "val2"}, deploy_two["config"])

    def test_deployment_update(self):
        credentials = {
            "openstack": [{"admin": {"foo": "bar"}, "users": ["foo_user"]}]}
        deploy = db.deployment_create({})
        self.assertEqual({}, deploy["config"])
        self.assertEqual({}, deploy["credentials"])
        update_deploy = db.deployment_update(
            deploy["uuid"], {"config": {"opt": "val"},
                             "credentials": copy.deepcopy(credentials)})
        self.assertEqual(deploy["uuid"], update_deploy["uuid"])
        self.assertEqual({"opt": "val"}, update_deploy["config"])
        self.assertEqual(credentials, update_deploy["credentials"])
        get_deploy = db.deployment_get(deploy["uuid"])
        self.assertEqual(deploy["uuid"], get_deploy["uuid"])
        self.assertEqual({"opt": "val"}, get_deploy["config"])
        self.assertEqual(credentials, update_deploy["credentials"])

    def test_deployment_update_several(self):
        # Create a deployment and update it
        deploy_one = db.deployment_create({})
        self.assertEqual({}, deploy_one["config"])
        update_deploy_one = db.deployment_update(
            deploy_one["uuid"], {"config": {"opt1": "val1"}})
        self.assertEqual(deploy_one["uuid"], update_deploy_one["uuid"])
        self.assertEqual({"opt1": "val1"}, update_deploy_one["config"])
        get_deploy_one = db.deployment_get(deploy_one["uuid"])
        self.assertEqual(deploy_one["uuid"], get_deploy_one["uuid"])
        self.assertEqual({"opt1": "val1"}, get_deploy_one["config"])

        # Create another deployment
        deploy_two = db.deployment_create({})
        update_deploy_two = db.deployment_update(
            deploy_two["uuid"], {"config": {"opt2": "val2"}})
        self.assertEqual(deploy_two["uuid"], update_deploy_two["uuid"])
        self.assertEqual({"opt2": "val2"}, update_deploy_two["config"])
        get_deploy_one_again = db.deployment_get(deploy_one["uuid"])
        self.assertEqual(deploy_one["uuid"], get_deploy_one_again["uuid"])
        self.assertEqual({"opt1": "val1"}, get_deploy_one_again["config"])

    def test_deployment_get(self):
        deploy_one = db.deployment_create({"config": {"opt1": "val1"}})
        deploy_two = db.deployment_create({"config": {"opt2": "val2"}})
        get_deploy_one = db.deployment_get(deploy_one["uuid"])
        get_deploy_two = db.deployment_get(deploy_two["uuid"])
        self.assertNotEqual(get_deploy_one["uuid"], get_deploy_two["uuid"])
        self.assertEqual({"opt1": "val1"}, get_deploy_one["config"])
        self.assertEqual({"opt2": "val2"}, get_deploy_two["config"])

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
        self.assertEqual(2, len(deploys))
        self.assertEqual(deploy_one["uuid"], deploys[0]["uuid"])
        deploys = db.deployment_list(status=consts.DeployStatus.DEPLOY_FAILED)
        self.assertEqual(1, len(deploys))
        self.assertEqual(deploy_two["uuid"], deploys[0]["uuid"])
        deploys = db.deployment_list(
            status=consts.DeployStatus.DEPLOY_FINISHED)
        self.assertEqual(0, len(deploys))
        deploys = db.deployment_list(name="deployment_name")
        self.assertEqual(deploy_three["uuid"], deploys[0]["uuid"])
        self.assertEqual(1, len(deploys))

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
        self.assertEqual(1, len(deploys))
        self.assertEqual(deploy_one["uuid"], deploys[0]["uuid"])

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
        self.assertEqual(1, len(resources))
        self.assertTrue(resources[0]["id"], resource["id"])
        self.assertEqual(deployment["uuid"], resource["deployment_uuid"])
        self.assertEqual("fakeprovider", resource["provider_name"])
        self.assertEqual("faketype", resource["type"])

    def test_delete(self):
        deployment = db.deployment_create({})
        res = db.resource_create({"deployment_uuid": deployment["uuid"]})
        db.resource_delete(res["id"])
        resources = db.resource_get_all(deployment["uuid"])
        self.assertEqual(0, len(resources))

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
        self.assertEqual(1, len(resources))
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
        self.assertEqual(1, len(resources))
        self.assertEqual(res_one["id"], resources[0]["id"])
        resources = db.resource_get_all(deployment["uuid"],
                                        provider_name="two")
        self.assertEqual(1, len(resources))
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
        self.assertEqual(1, len(resources))
        self.assertEqual(res_one["id"], resources[0]["id"])
        resources = db.resource_get_all(deployment["uuid"], type="two")
        self.assertEqual(1, len(resources))
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
        self.assertEqual(1, len(vs))
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
        return db.verification_create(verifier_uuid, deployment_uuid, [], {})

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
        v1 = db.verification_create(
            self.verifier["uuid"], deploy["uuid"], ["foo", "bar"], {})
        v2 = self._create_verification()

        vs = db.verification_list(self.verifier["uuid"])
        self.assertEqual(sorted([v1["uuid"], v2["uuid"]]),
                         sorted([v["uuid"] for v in vs]))

        vs = db.verification_list(self.verifier["uuid"], deploy["uuid"])
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
