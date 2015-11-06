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

import ddt
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


class FixDeploymentTestCase(test.DBTestCase):
    def setUp(self):
        super(FixDeploymentTestCase, self).setUp()

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
        db.task_result_create(task_id,
                              {task_id: task_id},
                              {task_id: task_id})
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

        for task_id in (task1, task2):
            db.task_result_create(task_id,
                                  {task_id: task_id},
                                  {task_id: task_id})

        for task_id in (task1, task2):
            res = db.task_result_get_all_by_uuid(task_id)
            data = {task_id: task_id}
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["key"], data)
            self.assertEqual(res[0]["data"], data)

    def test_task_get_detailed(self):
        task1 = self._create_task()
        key = {"name": "atata"}
        data = {"a": "b", "c": "d"}

        db.task_result_create(task1["uuid"], key, data)
        task1_full = db.task_get_detailed(task1["uuid"])
        results = task1_full["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["key"], key)
        self.assertEqual(results[0]["data"], data)

    def test_task_get_detailed_last(self):
        task1 = self._create_task()
        key = {"name": "atata"}
        data = {"a": "b", "c": "d"}

        db.task_result_create(task1["uuid"], key, data)
        task1_full = db.task_get_detailed_last()
        results = task1_full["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["key"], key)
        self.assertEqual(results[0]["data"], data)


class DeploymentTestCase(test.DBTestCase):
    def test_deployment_create(self):
        deploy = db.deployment_create({"config": {"opt": "val"}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploy["uuid"], deploys[0]["uuid"])
        self.assertEqual(deploy["status"], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy["config"], {"opt": "val"})

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
        deploy = db.deployment_create({})
        self.assertEqual(deploy["config"], {})
        update_deploy = db.deployment_update(deploy["uuid"],
                                             {"config": {"opt": "val"}})
        self.assertEqual(update_deploy["uuid"], deploy["uuid"])
        self.assertEqual(update_deploy["config"], {"opt": "val"})
        get_deploy = db.deployment_get(deploy["uuid"])
        self.assertEqual(get_deploy["uuid"], deploy["uuid"])
        self.assertEqual(get_deploy["config"], {"opt": "val"})

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


class VerificationTestCase(test.DBTestCase):
    def setUp(self):
        super(VerificationTestCase, self).setUp()
        self.deploy = db.deployment_create({})

    def _create_verification(self):
        deployment_uuid = self.deploy["uuid"]
        return db.verification_create(deployment_uuid)

    def test_creation_of_verification(self):
        verification = self._create_verification()
        db_verification = db.verification_get(verification["uuid"])

        self.assertEqual(verification["tests"], db_verification["tests"])
        self.assertEqual(verification["time"], db_verification["time"])
        self.assertEqual(verification["errors"], db_verification["errors"])
        self.assertEqual(verification["failures"], db_verification["failures"])

    def test_verification_get_not_found(self):
        self.assertRaises(exceptions.NotFoundException,
                          db.verification_get,
                          "fake_uuid")

    def test_verification_result_create_and_get(self):
        verification = self._create_verification()
        db_verification = db.verification_get(verification["uuid"])

        ver_result1 = db.verification_result_create(
            db_verification["uuid"], {})
        ver_result2 = db.verification_result_get(db_verification["uuid"])
        self.assertEqual(ver_result1["verification_uuid"],
                         ver_result2["verification_uuid"])


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
