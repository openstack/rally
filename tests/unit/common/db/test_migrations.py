# Copyright (c) 2016 Mirantis Inc.
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

"""Tests for DB migration."""

import copy
import json
import pprint
import uuid

import alembic
import mock
from oslo_db.sqlalchemy import test_migrations
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import timeutils
import six
import sqlalchemy as sa

import rally
from rally.common import db
from rally.common.db.sqlalchemy import api
from rally.common.db.sqlalchemy import models
from rally import consts
from rally.deployment.engines import existing
from tests.unit.common.db import test_migrations_base
from tests.unit import test as rtest


class MigrationTestCase(rtest.DBTestCase,
                        test_migrations.ModelsMigrationsSync):
    """Test for checking of equality models state and migrations.

    For the opportunistic testing you need to set up a db named
    'openstack_citest' with user 'openstack_citest' and password
    'openstack_citest' on localhost.
    The test will then use that db and user/password combo to run the tests.

    For PostgreSQL on Ubuntu this can be done with the following commands::

        sudo -u postgres psql
        postgres=# create user openstack_citest with createdb login password
                  'openstack_citest';
        postgres=# create database openstack_citest with owner
                   openstack_citest;

    For MySQL on Ubuntu this can be done with the following commands::

        mysql -u root
        >create database openstack_citest;
        >grant all privileges on openstack_citest.* to
         openstack_citest@localhost identified by 'openstack_citest';

    Output is a list that contains information about differences between db and
    models. Output example::

       [('add_table',
         Table('bat', MetaData(bind=None),
               Column('info', String(), table=<bat>), schema=None)),
        ('remove_table',
         Table(u'bar', MetaData(bind=None),
               Column(u'data', VARCHAR(), table=<bar>), schema=None)),
        ('add_column',
         None,
         'foo',
         Column('data', Integer(), table=<foo>)),
        ('remove_column',
         None,
         'foo',
         Column(u'old_data', VARCHAR(), table=None)),
        [('modify_nullable',
          None,
          'foo',
          u'x',
          {'existing_server_default': None,
          'existing_type': INTEGER()},
          True,
          False)]]

    * ``remove_*`` means that there is extra table/column/constraint in db;

    * ``add_*`` means that it is missing in db;

    * ``modify_*`` means that on column in db is set wrong
      type/nullable/server_default. Element contains information:

        - what should be modified,
        - schema,
        - table,
        - column,
        - existing correct column parameters,
        - right value,
        - wrong value.
    """

    def setUp(self):
        # we change DB metadata in tests so we reload
        # models to refresh the metadata to it's original state
        six.moves.reload_module(rally.common.db.sqlalchemy.models)
        super(MigrationTestCase, self).setUp()
        self.alembic_config = api._alembic_config()
        self.engine = api.get_engine()
        # remove everything from DB and stamp it as 'base'
        # so that migration (i.e. upgrade up to 'head')
        # will actually take place
        db.schema_cleanup()
        db.schema_stamp("base")

    def db_sync(self, engine):
        db.schema_upgrade()

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return models.BASE.metadata

    def include_object(self, object_, name, type_, reflected, compare_to):
        if type_ == "table" and name == "alembic_version":
                return False

        return super(MigrationTestCase, self).include_object(
            object_, name, type_, reflected, compare_to)

    def _create_fake_model(self, table_name):
        type(
            "FakeModel",
            (models.BASE, models.RallyBase),
            {"__tablename__": table_name,
             "id": sa.Column(sa.Integer, primary_key=True,
                             autoincrement=True)}
        )

    def _get_metadata_diff(self):
        with self.get_engine().connect() as conn:
            opts = {
                "include_object": self.include_object,
                "compare_type": self.compare_type,
                "compare_server_default": self.compare_server_default,
            }
            mc = alembic.migration.MigrationContext.configure(conn, opts=opts)

            # compare schemas and fail with diff, if it"s not empty
            diff = self.filter_metadata_diff(
                alembic.autogenerate.compare_metadata(mc, self.get_metadata()))

        return diff

    @mock.patch("rally.common.db.sqlalchemy.api.Connection.schema_stamp")
    def test_models_sync(self, mock_connection_schema_stamp):
        # drop all tables after a test run
        self.addCleanup(db.schema_cleanup)

        # run migration scripts
        self.db_sync(self.get_engine())

        diff = self._get_metadata_diff()
        if diff:
            msg = pprint.pformat(diff, indent=2, width=20)
            self.fail(
                "Models and migration scripts aren't in sync:\n%s" % msg)

    @mock.patch("rally.common.db.sqlalchemy.api.Connection.schema_stamp")
    def test_models_sync_negative__missing_table_in_script(
            self, mock_connection_schema_stamp):
        # drop all tables after a test run
        self.addCleanup(db.schema_cleanup)

        self._create_fake_model("fake_model")

        # run migration scripts
        self.db_sync(self.get_engine())

        diff = self._get_metadata_diff()

        self.assertEqual(1, len(diff))
        action, object = diff[0]
        self.assertEqual("add_table", action)
        self.assertIsInstance(object, sa.Table)
        self.assertEqual("fake_model", object.name)

    @mock.patch("rally.common.db.sqlalchemy.api.Connection.schema_stamp")
    def test_models_sync_negative__missing_model_in_metadata(
            self, mock_connection_schema_stamp):
        # drop all tables after a test run
        self.addCleanup(db.schema_cleanup)

        table = self.get_metadata().tables["workers"]
        self.get_metadata().remove(table)

        # run migration scripts
        self.db_sync(self.get_engine())

        diff = self._get_metadata_diff()

        self.assertEqual(1, len(diff))
        action, object = diff[0]
        self.assertEqual("remove_table", action)
        self.assertIsInstance(object, sa.Table)
        self.assertEqual("workers", object.name)


class MigrationWalkTestCase(rtest.DBTestCase,
                            test_migrations_base.BaseWalkMigrationMixin):
    """Test case covers upgrade method in migrations."""

    def setUp(self):
        super(MigrationWalkTestCase, self).setUp()
        self.engine = api.get_engine()

    def assertColumnExists(self, engine, table, column):
        t = db_utils.get_table(engine, table)
        self.assertIn(column, t.c)

    def assertColumnsExists(self, engine, table, columns):
        for column in columns:
            self.assertColumnExists(engine, table, column)

    def assertColumnCount(self, engine, table, columns):
        t = db_utils.get_table(engine, table)
        self.assertEqual(len(t.columns), len(columns))

    def assertColumnNotExists(self, engine, table, column):
        t = db_utils.get_table(engine, table)
        self.assertNotIn(column, t.c)

    def assertIndexExists(self, engine, table, index):
        t = db_utils.get_table(engine, table)
        index_names = [idx.name for idx in t.indexes]
        self.assertIn(index, index_names)

    def assertColumnType(self, engine, table, column, sqltype):
        t = db_utils.get_table(engine, table)
        col = getattr(t.c, column)
        self.assertIsInstance(col.type, sqltype)

    def assertIndexMembers(self, engine, table, index, members):
        self.assertIndexExists(engine, table, index)

        t = db_utils.get_table(engine, table)
        index_columns = None
        for idx in t.indexes:
            if idx.name == index:
                index_columns = idx.columns.keys()
                break

        self.assertEqual(sorted(members), sorted(index_columns))

    def test_walk_versions(self):
        self.walk_versions(self.engine)

    def _check_3177d36ea270(self, engine, data):
        self.assertEqual(
            "3177d36ea270", api.get_backend().schema_revision(engine=engine))
        self.assertColumnExists(engine, "deployments", "credentials")
        self.assertColumnNotExists(engine, "deployments", "admin")
        self.assertColumnNotExists(engine, "deployments", "users")

    def _pre_upgrade_54e844ebfbc3(self, engine):
        self._54e844ebfbc3_deployments = {
            # right config which should not be changed after migration
            "should-not-be-changed-1": {
                "admin": {"username": "admin",
                          "password": "passwd",
                          "project_name": "admin"},
                "auth_url": "http://example.com:5000/v3",
                "region_name": "RegionOne",
                "type": "ExistingCloud"},
            # right config which should not be changed after migration
            "should-not-be-changed-2": {
                "admin": {"username": "admin",
                          "password": "passwd",
                          "tenant_name": "admin"},
                "users": [{"username": "admin",
                           "password": "passwd",
                          "tenant_name": "admin"}],
                "auth_url": "http://example.com:5000/v2.0",
                "region_name": "RegionOne",
                "type": "ExistingCloud"},
            # not ExistingCloud config which should not be changed
            "should-not-be-changed-3": {
                "url": "example.com",
                "type": "Something"},
            # normal config created with "fromenv" feature
            "from-env": {
                "admin": {"username": "admin",
                          "password": "passwd",
                          "tenant_name": "admin",
                          "project_domain_name": "",
                          "user_domain_name": ""},
                "auth_url": "http://example.com:5000/v2.0",
                "region_name": "RegionOne",
                "type": "ExistingCloud"},
            # public endpoint + keystone v3 config with tenant_name
            "ksv3_public": {
                "admin": {"username": "admin",
                          "password": "passwd",
                          "tenant_name": "admin",
                          "user_domain_name": "bla",
                          "project_domain_name": "foo"},
                "auth_url": "http://example.com:5000/v3",
                "region_name": "RegionOne",
                "type": "ExistingCloud",
                "endpoint_type": "public"},
            # internal endpoint + existing_users
            "existing_internal": {
                "admin": {"username": "admin",
                          "password": "passwd",
                          "tenant_name": "admin"},
                "users": [{"username": "admin",
                           "password": "passwd",
                           "tenant_name": "admin",
                           "project_domain_name": "",
                           "user_domain_name": ""}],
                "auth_url": "http://example.com:5000/v2.0",
                "region_name": "RegionOne",
                "type": "ExistingCloud",
                "endpoint_type": "internal"},
        }
        deployment_table = db_utils.get_table(engine, "deployments")

        deployment_status = consts.DeployStatus.DEPLOY_FINISHED
        with engine.connect() as conn:
            for deployment in self._54e844ebfbc3_deployments:
                conf = json.dumps(self._54e844ebfbc3_deployments[deployment])
                conn.execute(
                    deployment_table.insert(),
                    [{"uuid": deployment, "name": deployment,
                      "config": conf,
                      "enum_deployments_status": deployment_status,
                      "credentials": six.b(json.dumps([])),
                      "users": six.b(json.dumps([]))
                      }])

    def _check_54e844ebfbc3(self, engine, data):
        self.assertEqual("54e844ebfbc3",
                         api.get_backend().schema_revision(engine=engine))

        original_deployments = self._54e844ebfbc3_deployments

        deployment_table = db_utils.get_table(engine, "deployments")

        with engine.connect() as conn:
            deployments_found = conn.execute(
                deployment_table.select()).fetchall()
            for deployment in deployments_found:
                # check deployment
                self.assertIn(deployment.uuid, original_deployments)
                self.assertIn(deployment.name, original_deployments)

                config = json.loads(deployment.config)
                if config != original_deployments[deployment.uuid]:
                    if deployment.uuid.startswith("should-not-be-changed"):
                        self.fail("Config of deployment '%s' is changes, but "
                                  "should not." % deployment.uuid)

                    endpoint_type = (original_deployments[
                                     deployment.uuid].get("endpoint_type"))
                    if endpoint_type in (None, "public"):
                        self.assertNotIn("endpoint_type", config)
                    else:
                        self.assertIn("endpoint_type", config)
                        self.assertEqual(endpoint_type,
                                         config["endpoint_type"])

                    existing.ExistingCloud({"config": config}).validate()
                else:
                    if not deployment.uuid.startswith("should-not-be-changed"):
                        self.fail("Config of deployment '%s' is not changes, "
                                  "but should." % deployment.uuid)

                # this deployment created at _pre_upgrade step is not needed
                # anymore and we can remove it
                conn.execute(
                    deployment_table.delete().where(
                        deployment_table.c.uuid == deployment.uuid)
                )

    def _pre_upgrade_08e1515a576c(self, engine):
        self._08e1515a576c_logs = [
            {"pre": "No such file name",
             "post": {"etype": IOError.__name__, "msg": "No such file name"}},
            {"pre": "Task config is invalid: bla",
             "post": {"etype": "InvalidTaskException",
                      "msg": "Task config is invalid: bla"}},
            {"pre": "Failed to load task foo",
             "post": {"etype": "FailedToLoadTask",
                      "msg": "Failed to load task foo"}},
            {"pre": ["SomeCls", "msg", json.dumps(
                ["File some1.py, line ...\n",
                 "File some2.py, line ...\n"])],
             "post": {"etype": "SomeCls",
                      "msg": "msg",
                      "trace": "Traceback (most recent call last):\n"
                               "File some1.py, line ...\n"
                               "File some2.py, line ...\nSomeCls: msg"}},
        ]

        deployment_table = db_utils.get_table(engine, "deployments")
        task_table = db_utils.get_table(engine, "tasks")

        self._08e1515a576c_deployment_uuid = "08e1515a576c-uuuu-uuuu-iiii-dddd"
        with engine.connect() as conn:
            conn.execute(
                deployment_table.insert(),
                [{"uuid": self._08e1515a576c_deployment_uuid,
                  "name": self._08e1515a576c_deployment_uuid,
                  "config": six.b("{}"),
                  "enum_deployments_status":
                      consts.DeployStatus.DEPLOY_FINISHED,
                  "credentials": six.b(json.dumps([])),
                  "users": six.b(json.dumps([]))
                  }])
            for i in range(0, len(self._08e1515a576c_logs)):
                log = json.dumps(self._08e1515a576c_logs[i]["pre"])
                conn.execute(
                    task_table.insert(),
                    [{"uuid": i,
                      "verification_log": log,
                      "status": consts.TaskStatus.FAILED,
                      "enum_tasks_status": consts.TaskStatus.FAILED,
                      "deployment_uuid": self._08e1515a576c_deployment_uuid
                      }])

    def _check_08e1515a576c(self, engine, data):
        self.assertEqual("08e1515a576c",
                         api.get_backend().schema_revision(engine=engine))

        tasks = self._08e1515a576c_logs

        deployment_table = db_utils.get_table(engine, "deployments")
        task_table = db_utils.get_table(engine, "tasks")

        with engine.connect() as conn:
            tasks_found = conn.execute(task_table.select()).fetchall()
            for task in tasks_found:
                actual_log = json.loads(task.verification_log)
                self.assertIsInstance(actual_log, dict)
                expected = tasks[int(task.uuid)]["post"]
                for key in expected:
                    self.assertEqual(expected[key], actual_log[key])

                conn.execute(
                    task_table.delete().where(task_table.c.uuid == task.uuid))

            deployment_uuid = self._08e1515a576c_deployment_uuid
            conn.execute(
                deployment_table.delete().where(
                    deployment_table.c.uuid == deployment_uuid))

    def _pre_upgrade_e654a0648db0(self, engine):
        deployment_table = db_utils.get_table(engine, "deployments")
        task_table = db_utils.get_table(engine, "tasks")
        taskresult_table = db_utils.get_table(engine, "task_results")

        self._e654a0648db0_task_uuid = str(uuid.uuid4())
        self._e654a0648db0_deployment_uuid = str(uuid.uuid4())

        with engine.connect() as conn:
            conn.execute(
                deployment_table.insert(),
                [{
                    "uuid": self._e654a0648db0_deployment_uuid,
                    "name": self._e654a0648db0_deployment_uuid,
                    "config": "{}",
                    "enum_deployments_status": consts.DeployStatus.DEPLOY_INIT,
                    "credentials": six.b(json.dumps([])),
                    "users": six.b(json.dumps([]))
                }]
            )

            conn.execute(
                task_table.insert(),
                [{
                    "uuid": self._e654a0648db0_task_uuid,
                    "created_at": timeutils.utcnow(),
                    "updated_at": timeutils.utcnow(),
                    "status": consts.TaskStatus.FINISHED,
                    "verification_log": json.dumps({}),
                    "tag": "test_tag",
                    "deployment_uuid": self._e654a0648db0_deployment_uuid
                }]
            )

            conn.execute(
                taskresult_table.insert(), [
                    {
                        "task_uuid": self._e654a0648db0_task_uuid,
                        "created_at": timeutils.utcnow(),
                        "updated_at": timeutils.utcnow(),
                        "key": json.dumps({
                            "name": "test_scenario",
                            "pos": 0,
                            "kw": {
                                "args": {"a": "A"},
                                "runner": {"type": "theRunner"},
                                "context": {"c": "C"},
                                "sla": {"s": "S"}
                            }
                        }),
                        "data": json.dumps({
                            "raw": [
                                {"error": "e", "duration": 3},
                                {"duration": 1},
                                {"duration": 8},
                            ],
                            "load_duration": 42,
                            "full_duration": 142,
                            "sla": [{"success": True}, {"success": False}]
                        })
                    }
                ]
            )

    def _check_e654a0648db0(self, engine, data):
        self.assertEqual(
            "e654a0648db0", api.get_backend().schema_revision(engine=engine))

        task_table = db_utils.get_table(engine, "tasks")
        subtask_table = db_utils.get_table(engine, "subtasks")
        workload_table = db_utils.get_table(engine, "workloads")
        workloaddata_table = db_utils.get_table(engine, "workloaddata")
        tag_table = db_utils.get_table(engine, "tags")
        deployment_table = db_utils.get_table(engine, "deployments")

        with engine.connect() as conn:

            # Check task

            tasks_found = conn.execute(
                task_table.select().
                where(task_table.c.uuid == self._e654a0648db0_task_uuid)
            ).fetchall()

            self.assertEqual(len(tasks_found), 1)

            task_found = tasks_found[0]
            self.assertEqual(task_found.uuid, self._e654a0648db0_task_uuid)
            self.assertEqual(task_found.deployment_uuid,
                             self._e654a0648db0_deployment_uuid)
            self.assertEqual(task_found.status, consts.TaskStatus.FINISHED)
            # NOTE(ikhudoshyn): if for all workloads success == True
            self.assertEqual(task_found.pass_sla, False)
            # NOTE(ikhudoshyn): sum of all full_durations of all workloads
            self.assertEqual(task_found.task_duration, 142)
            # NOTE(ikhudoshyn): we have no info on validation duration in old
            # schema
            self.assertEqual(task_found.validation_duration, 0)
            self.assertEqual(json.loads(task_found.validation_result), {})

            # Check subtask

            subtasks_found = conn.execute(
                subtask_table.select().
                where(subtask_table.c.task_uuid ==
                      self._e654a0648db0_task_uuid)
            ).fetchall()

            self.assertEqual(len(subtasks_found), 1)

            subtask_found = subtasks_found[0]
            self.assertEqual(subtask_found.task_uuid,
                             self._e654a0648db0_task_uuid)

            # NOTE(ikhudoshyn): if for all workloads success == True
            self.assertEqual(subtask_found.pass_sla, False)
            # NOTE(ikhudoshyn): sum of all full_durations of all workloads
            self.assertEqual(subtask_found.duration, 142)

            self._e654a0648db0_subtask_uuid = subtask_found.uuid

            # Check tag

            tags_found = conn.execute(
                tag_table.select().
                where(tag_table.c.uuid == self._e654a0648db0_task_uuid)
            ).fetchall()

            self.assertEqual(len(tags_found), 1)
            self.assertEqual(tags_found[0].tag, "test_tag")
            self.assertEqual(tags_found[0].type, consts.TagType.TASK)

            # Check workload

            workloads_found = conn.execute(
                workload_table.select().
                where(workload_table.c.task_uuid ==
                      self._e654a0648db0_task_uuid)
            ).fetchall()

            self.assertEqual(len(workloads_found), 1)

            workload_found = workloads_found[0]

            self.assertEqual(workload_found.task_uuid,
                             self._e654a0648db0_task_uuid)

            self.assertEqual(workload_found.subtask_uuid,
                             self._e654a0648db0_subtask_uuid)

            self.assertEqual(workload_found.name, "test_scenario")
            self.assertEqual(workload_found.position, 0)
            self.assertEqual(workload_found.runner_type, "theRunner")
            self.assertEqual(workload_found.runner,
                             json.dumps({"type": "theRunner"}))
            self.assertEqual(workload_found.sla,
                             json.dumps({"s": "S"}))
            self.assertEqual(workload_found.args,
                             json.dumps({"a": "A"}))
            self.assertEqual(workload_found.context,
                             json.dumps({"c": "C"}))
            self.assertEqual(workload_found.sla_results,
                             json.dumps({
                                 "sla": [
                                     {"success": True},
                                     {"success": False}
                                 ]
                             }))
            self.assertEqual(workload_found.context_execution,
                             json.dumps({}))
            self.assertEqual(workload_found.load_duration, 42)
            self.assertEqual(workload_found.full_duration, 142)
            self.assertEqual(workload_found.min_duration, 1)
            self.assertEqual(workload_found.max_duration, 8)
            self.assertEqual(workload_found.total_iteration_count, 3)
            self.assertEqual(workload_found.failed_iteration_count, 1)
            self.assertEqual(workload_found.pass_sla, False)

            self._e654a0648db0_workload_uuid = workload_found.uuid

            # Check workloadData

            workloaddata_found = conn.execute(
                workloaddata_table.select().
                where(workloaddata_table.c.task_uuid ==
                      self._e654a0648db0_task_uuid)
            ).fetchall()

            self.assertEqual(len(workloaddata_found), 1)

            wloaddata_found = workloaddata_found[0]

            self.assertEqual(wloaddata_found.task_uuid,
                             self._e654a0648db0_task_uuid)

            self.assertEqual(wloaddata_found.workload_uuid,
                             self._e654a0648db0_workload_uuid)

            self.assertEqual(wloaddata_found.chunk_order, 0)
            self.assertEqual(wloaddata_found.chunk_size, 0)
            self.assertEqual(wloaddata_found.compressed_chunk_size, 0)
            self.assertEqual(wloaddata_found.iteration_count, 3)
            self.assertEqual(wloaddata_found.failed_iteration_count, 1)
            self.assertEqual(
                wloaddata_found.chunk_data,
                json.dumps(
                    {
                        "raw": [
                            {"error": "e", "duration": 3},
                            {"duration": 1},
                            {"duration": 8},
                        ]
                    }
                )
            )

            # Delete all stuff created at _pre_upgrade step

            conn.execute(
                tag_table.delete().
                where(tag_table.c.uuid == self._e654a0648db0_task_uuid)
            )

            conn.execute(
                workloaddata_table.delete().
                where(workloaddata_table.c.task_uuid ==
                      self._e654a0648db0_task_uuid)
            )

            conn.execute(
                workload_table.delete().
                where(workload_table.c.task_uuid ==
                      self._e654a0648db0_task_uuid)
            )
            conn.execute(
                subtask_table.delete().
                where(subtask_table.c.task_uuid ==
                      self._e654a0648db0_task_uuid)
            )

            conn.execute(
                task_table.delete().
                where(task_table.c.uuid == self._e654a0648db0_task_uuid)
            )

            conn.execute(
                deployment_table.delete().
                where(deployment_table.c.uuid ==
                      self._e654a0648db0_deployment_uuid)
            )

    def _pre_upgrade_6ad4f426f005(self, engine):
        deployment_table = db_utils.get_table(engine, "deployments")
        task_table = db_utils.get_table(engine, "tasks")
        task_result_table = db_utils.get_table(engine, "task_results")
        with engine.connect() as conn:
            # create deployment
            conf = {
                "admin": {"username": "admin",
                          "password": "passwd",
                          "project_name": "admin"},
                "auth_url": "http://example.com:5000/v3",
                "region_name": "RegionOne",
                "type": "ExistingCloud"
            }
            deployment_status = consts.DeployStatus.DEPLOY_FINISHED
            conn.execute(
                deployment_table.insert(),
                [{
                    "uuid": "my_deployment",
                    "name": "my_deployment",
                    "config": json.dumps(conf),
                    "enum_deployments_status": deployment_status,
                    "credentials": six.b(json.dumps([])),
                    "users": six.b(json.dumps([]))
                }])

            # create task
            conn.execute(
                task_table.insert(),
                [{
                    "uuid": "my_task",
                    "deployment_uuid": "my_deployment",
                    "status": consts.TaskStatus.INIT,
                }])

            # create task result with empty data
            conn.execute(
                task_result_table.insert(),
                [{
                    "task_uuid": "my_task",
                    "key": json.dumps({}),
                    "data": json.dumps({}),
                }]
            )

    def _check_6ad4f426f005(self, engine, data):
        self.assertEqual("6ad4f426f005",
                         api.get_backend().schema_revision(engine=engine))

        deployment_table = db_utils.get_table(engine, "deployments")
        task_table = db_utils.get_table(engine, "tasks")
        task_result_table = db_utils.get_table(engine, "task_results")
        with engine.connect() as conn:
            task_results = conn.execute(task_result_table.select()).fetchall()
            self.assertEqual(1, len(task_results))
            task_result = task_results[0]

            # check that "hooks" field added
            self.assertEqual({"hooks": []}, json.loads(task_result.data))

            # Remove task result
            conn.execute(
                task_result_table.delete().where(
                    task_result_table.c.id == task_result.id)
            )

            # Remove task
            conn.execute(
                task_table.delete().where(task_table.c.uuid == "my_task"))

            # Remove deployment
            conn.execute(
                deployment_table.delete().where(
                    deployment_table.c.uuid == "my_deployment")
            )

    def _pre_upgrade_32fada9b2fde(self, engine):
            self._32fada9b2fde_deployments = {
                # right config which should not be changed after migration
                "should-not-be-changed-1": {
                    "admin": {"username": "admin",
                              "password": "passwd",
                              "project_name": "admin"},
                    "auth_url": "http://example.com:5000/v3",
                    "region_name": "RegionOne",
                    "type": "ExistingCloud"},
                # right config which should not be changed after migration
                "should-not-be-changed-2": {
                    "admin": {"username": "admin",
                              "password": "passwd",
                              "tenant_name": "admin"},
                    "users": [{"username": "admin",
                               "password": "passwd",
                              "tenant_name": "admin"}],
                    "auth_url": "http://example.com:5000/v2.0",
                    "region_name": "RegionOne",
                    "type": "ExistingCloud"},
                # not ExistingCloud config which should not be changed
                "should-not-be-changed-3": {
                    "url": "example.com",
                    "type": "Something"},
                # with `admin_domain_name` field
                "with_admin_domain_name": {
                    "admin": {"username": "admin",
                              "password": "passwd",
                              "project_name": "admin",
                              "admin_domain_name": "admin"},
                    "auth_url": "http://example.com:5000/v3",
                    "region_name": "RegionOne",
                    "type": "ExistingCloud"},
            }
            deployment_table = db_utils.get_table(engine, "deployments")

            deployment_status = consts.DeployStatus.DEPLOY_FINISHED
            with engine.connect() as conn:
                for deployment in self._32fada9b2fde_deployments:
                    conf = json.dumps(
                        self._32fada9b2fde_deployments[deployment])
                    conn.execute(
                        deployment_table.insert(),
                        [{"uuid": deployment, "name": deployment,
                          "config": conf,
                          "enum_deployments_status": deployment_status,
                          "credentials": six.b(json.dumps([])),
                          "users": six.b(json.dumps([]))
                          }])

    def _check_32fada9b2fde(self, engine, data):
        self.assertEqual("32fada9b2fde",
                         api.get_backend().schema_revision(engine=engine))

        original_deployments = self._32fada9b2fde_deployments

        deployment_table = db_utils.get_table(engine, "deployments")

        with engine.connect() as conn:
            deployments_found = conn.execute(
                deployment_table.select()).fetchall()
            for deployment in deployments_found:
                # check deployment
                self.assertIn(deployment.uuid, original_deployments)
                self.assertIn(deployment.name, original_deployments)

                config = json.loads(deployment.config)
                if config != original_deployments[deployment.uuid]:
                    if deployment.uuid.startswith("should-not-be-changed"):
                        self.fail("Config of deployment '%s' is changes, but "
                                  "should not." % deployment.uuid)
                    if "admin_domain_name" in deployment.config:
                        self.fail("Config of deployment '%s' should not "
                                  "contain `admin_domain_name` field." %
                                  deployment.uuid)

                    endpoint_type = (original_deployments[
                                     deployment.uuid].get("endpoint_type"))
                    if endpoint_type in (None, "public"):
                        self.assertNotIn("endpoint_type", config)
                    else:
                        self.assertIn("endpoint_type", config)
                        self.assertEqual(endpoint_type,
                                         config["endpoint_type"])

                    existing.ExistingCloud({"config": config}).validate()
                else:
                    if not deployment.uuid.startswith("should-not-be-changed"):
                        self.fail("Config of deployment '%s' is not changes, "
                                  "but should." % deployment.uuid)

                # this deployment created at _pre_upgrade step is not needed
                # anymore and we can remove it
                conn.execute(
                    deployment_table.delete().where(
                        deployment_table.c.uuid == deployment.uuid)
                )

    def _pre_upgrade_484cd9413e66(self, engine):
            self._484cd9413e66_deployment_uuid = "484cd9413e66-deploy"

            self._484cd9413e66_verifications = [
                {"total": {"time": 1.0,
                           "failures": 2,
                           "skipped": 3,
                           "success": 4,
                           "errors": 0,
                           "tests": 2
                           },
                 "test_cases": {"test1": {"status": "OK"},
                                "test2": {"status": "FAIL",
                                          "failure": {"log": "trace"}}},
                 "set_name": "full"},
                {"total": {"time": 2.0,
                           "failures": 3,
                           "skipped": 4,
                           "success": 5,
                           "unexpected_success": 6,
                           "expected_failures": 7,
                           "tests": 2
                           },
                 "test_cases": {"test1": {"status": "success"},
                                "test2": {"status": "failed", ""
                                          "traceback": "trace"}},
                 "set_name": "smoke"}
            ]
            deployment_table = db_utils.get_table(engine, "deployments")
            verifications_table = db_utils.get_table(engine, "verifications")
            vresults_table = db_utils.get_table(engine,
                                                "verification_results")

            deployment_status = consts.DeployStatus.DEPLOY_FINISHED
            vstatus = consts.TaskStatus.FINISHED
            with engine.connect() as conn:
                conn.execute(
                    deployment_table.insert(),
                    [{"uuid": self._484cd9413e66_deployment_uuid,
                      "name": self._484cd9413e66_deployment_uuid,
                      "config": six.b(json.dumps([])),
                      "enum_deployments_status": deployment_status,
                      "credentials": six.b(json.dumps([])),
                      "users": six.b(json.dumps([]))
                      }])

                for i in range(len(self._484cd9413e66_verifications)):
                    verification = self._484cd9413e66_verifications[i]
                    vuuid = "uuid-%s" % i
                    conn.execute(
                        verifications_table.insert(),
                        [{"uuid": vuuid,
                          "deployment_uuid":
                              self._484cd9413e66_deployment_uuid,
                          "status": vstatus,
                          "set_name": verification["set_name"],
                          "tests": verification["total"]["tests"],
                          "failures": verification["total"]["failures"],
                          "time": verification["total"]["time"],
                          "errors": 0,
                          }])
                    data = copy.deepcopy(verification)
                    data["total"]["test_cases"] = data["test_cases"]
                    data = data["total"]
                    conn.execute(
                        vresults_table.insert(),
                        [{"uuid": vuuid,
                          "verification_uuid": vuuid,
                          "data": json.dumps(data)
                          }])

    def _check_484cd9413e66(self, engine, data):
        self.assertEqual("484cd9413e66",
                         api.get_backend().schema_revision(engine=engine))

        verifications_table = db_utils.get_table(engine, "verifications")

        with engine.connect() as conn:
            verifications = conn.execute(
                verifications_table.select()).fetchall()
            for i in range(len(verifications)):
                verification_orig = self._484cd9413e66_verifications[i]
                verification = verifications[i]
                total = {"time": verification.tests_duration,
                         "failures": verification.failures,
                         "skipped": verification.skipped,
                         "success": verification.success,
                         "tests": verification.tests_count}
                results = verification_orig["test_cases"]

                old_format = "errors" in verification_orig["total"]
                if old_format:
                    total["errors"] = 0
                    for test_name in results:
                        status = results[test_name]["status"]
                        if status == "OK":
                            status = "success"
                        elif status == "FAIL":
                            status = "fail"
                            results[test_name]["traceback"] = results[
                                test_name]["failure"].pop("log")
                            results[test_name].pop("failure")
                        results[test_name]["status"] = status
                else:
                    uxsucess = verification.unexpected_success
                    total["unexpected_success"] = uxsucess
                    total["expected_failures"] = verification.expected_failures

                self.assertEqual(verification_orig["total"], total)

                self.assertEqual(results, json.loads(verification.tests))

                self.assertEqual(
                    {"pattern": "set=%s" % verification_orig["set_name"]},
                    json.loads(verification.run_args))

                self.assertEqual(
                    verification_orig["total"].get("unexpected_success", 0),
                    verification.unexpected_success)
                self.assertEqual(
                    verification_orig["total"].get("expected_failures", 0),
                    verification.expected_failures)

                conn.execute(
                    verifications_table.delete().where(
                        verifications_table.c.uuid == verification.uuid)
                )

            deployment_table = db_utils.get_table(engine, "deployments")
            conn.execute(
                deployment_table.delete().where(
                    deployment_table.c.uuid ==
                    self._484cd9413e66_deployment_uuid)
            )

    def _pre_upgrade_37fdbb373e8d(self, engine):
            self._37fdbb373e8d_deployment_uuid = "37fdbb373e8d-deployment"
            self._37fdbb373e8d_verifier_uuid = "37fdbb373e8d-verifier"
            self._37fdbb373e8d_verifications_tests = [
                {
                    "test_1[smoke, negative]": {
                        "name": "test_1",
                        "time": 2.32,
                        "status": "success",
                        "tags": ["smoke", "negative"]
                    },
                    "test_2[smoke, negative]": {
                        "name": "test_2",
                        "time": 4.32,
                        "status": "success",
                        "tags": ["smoke", "negative"]
                    }
                },
                {
                    "test_3[smoke, negative]": {
                        "name": "test_3",
                        "time": 6.32,
                        "status": "success",
                        "tags": ["smoke", "negative"]
                    },
                    "test_4[smoke, negative]": {
                        "name": "test_4",
                        "time": 8.32,
                        "status": "success",
                        "tags": ["smoke", "negative"]
                    }
                }
            ]

            deployment_table = db_utils.get_table(engine, "deployments")
            verifiers_table = db_utils.get_table(engine, "verifiers")
            verifications_table = db_utils.get_table(engine, "verifications")

            deployment_status = consts.DeployStatus.DEPLOY_FINISHED
            with engine.connect() as conn:
                conn.execute(
                    deployment_table.insert(),
                    [{"uuid": self._37fdbb373e8d_deployment_uuid,
                      "name": self._37fdbb373e8d_deployment_uuid,
                      "config": six.b(json.dumps([])),
                      "enum_deployments_status": deployment_status,
                      "credentials": six.b(json.dumps([])),
                      "users": six.b(json.dumps([]))
                      }])

                conn.execute(
                    verifiers_table.insert(),
                    [{"uuid": self._37fdbb373e8d_verifier_uuid,
                      "name": self._37fdbb373e8d_verifier_uuid,
                      "type": "some-type",
                      "status": consts.VerifierStatus.CONFIGURED
                      }])

                for i in range(len(self._37fdbb373e8d_verifications_tests)):
                    tests = self._37fdbb373e8d_verifications_tests[i]
                    conn.execute(
                        verifications_table.insert(),
                        [{"uuid": "verification-uuid-%s" % i,
                          "deployment_uuid":
                              self._37fdbb373e8d_deployment_uuid,
                          "verifier_uuid": self._37fdbb373e8d_verifier_uuid,
                          "status": consts.VerificationStatus.FINISHED,
                          "tests": json.dumps(tests)
                          }])

    def _check_37fdbb373e8d(self, engine, data):
        self.assertEqual("37fdbb373e8d",
                         api.get_backend().schema_revision(engine=engine))

        verifications_table = db_utils.get_table(engine, "verifications")
        with engine.connect() as conn:
            verifications = conn.execute(
                verifications_table.select()).fetchall()
            self.assertEqual(len(verifications),
                             len(self._37fdbb373e8d_verifications_tests))

            for i in range(len(verifications)):
                v = verifications[i]
                updated_tests = json.loads(v.tests)
                expected_tests = self._37fdbb373e8d_verifications_tests[i]
                for test in expected_tests.values():
                    duration = test.pop("time")
                    test["duration"] = duration

                self.assertEqual(expected_tests, updated_tests)
