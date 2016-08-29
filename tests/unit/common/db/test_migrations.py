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

import json
import pprint

import alembic
import mock
from oslo_db.sqlalchemy import test_migrations
from oslo_db.sqlalchemy import utils as db_utils
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
                    deployment_table.c.uuid == deployment_uuid)
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
