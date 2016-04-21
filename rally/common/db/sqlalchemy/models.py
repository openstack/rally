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
"""
SQLAlchemy models for rally data.
"""

import uuid

from oslo_db.sqlalchemy.compat import utils as compat_utils
from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import schema
from sqlalchemy import types

from rally.common.db.sqlalchemy import types as sa_types
from rally import consts


BASE = declarative_base()


def UUID():
    return str(uuid.uuid4())


class RallyBase(models.ModelBase):
    metadata = None
    created_at = sa.Column(sa.DateTime, default=lambda: timeutils.utcnow())
    updated_at = sa.Column(sa.DateTime, default=lambda: timeutils.utcnow(),
                           onupdate=lambda: timeutils.utcnow())

    def save(self, session=None):
        # NOTE(LimingWu): We can't direct import the api module. that will
        # result in the cyclic reference import since the api has imported
        # this module.
        from rally.common.db.sqlalchemy import api as sa_api

        if session is None:
            session = sa_api.get_session()

        super(RallyBase, self).save(session=session)


class Deployment(BASE, RallyBase):
    """Represent a deployment of OpenStack."""
    __tablename__ = "deployments"
    __table_args__ = (
        sa.Index("deployment_uuid", "uuid", unique=True),
        sa.Index("deployment_parent_uuid", "parent_uuid"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)
    parent_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(uuid, use_alter=True, name="fk_parent_uuid"),
        default=None,
    )
    name = sa.Column(sa.String(255), unique=True)
    started_at = sa.Column(sa.DateTime)
    completed_at = sa.Column(sa.DateTime)
    # XXX(akscram): Do we need to explicitly store a name of the
    #               deployment engine?
    # engine_name = sa.Column(sa.String(36))

    config = sa.Column(
        sa_types.MutableJSONEncodedDict,
        default={},
        nullable=False,
    )

    credentials = sa.Column(types.PickleType, default=[], nullable=False)

    status = sa.Column(
        sa.Enum(*consts.DeployStatus, name="enum_deploy_status"),
        name="enum_deployments_status",
        default=consts.DeployStatus.DEPLOY_INIT,
        nullable=False,
    )

    parent = sa.orm.relationship(
        "Deployment",
        backref=sa.orm.backref("subdeploys"),
        remote_side=[uuid],
        foreign_keys=parent_uuid,
    )

    # TODO(rpromyshlennikov): remove admin after credentials refactoring
    @property
    def admin(self):
        return self.credentials[0][1]["admin"]

    @admin.setter
    def admin(self, value):
        pass

    # TODO(rpromyshlennikov): remove users after credentials refactoring
    @property
    def users(self):
        return self.credentials[0][1]["users"]

    @users.setter
    def users(self, value):
        pass


class Resource(BASE, RallyBase):
    """Represent a resource of a deployment."""
    __tablename__ = "resources"
    __table_args__ = (
        sa.Index("resource_deployment_uuid", "deployment_uuid"),
        sa.Index("resource_provider_name", "deployment_uuid", "provider_name"),
        sa.Index("resource_type", "deployment_uuid", "type"),
        sa.Index("resource_provider_name_and_type", "deployment_uuid",
                 "provider_name", "type"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    provider_name = sa.Column(sa.String(255))
    type = sa.Column(sa.String(255))

    info = sa.Column(
        sa_types.MutableJSONEncodedDict,
        default={},
        nullable=False,
    )

    deployment_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Deployment.uuid),
        nullable=False,
    )
    deployment = sa.orm.relationship(
        Deployment,
        backref=sa.orm.backref("resources"),
        foreign_keys=deployment_uuid,
        primaryjoin=(deployment_uuid == Deployment.uuid),
    )


class Task(BASE, RallyBase):
    """Represents a Benchmark task."""
    __tablename__ = "tasks"
    __table_args__ = (
        sa.Index("task_uuid", "uuid", unique=True),
        sa.Index("task_status", "status"),
        sa.Index("task_deployment", "deployment_uuid"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)
    status = sa.Column(sa.Enum(*list(consts.TaskStatus),
                       name="enum_tasks_status"),
                       default=consts.TaskStatus.INIT,
                       nullable=False)
    verification_log = sa.Column(sa.Text, default="")
    tag = sa.Column(sa.String(64), default="")

    deployment_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Deployment.uuid),
        nullable=False,
    )

    deployment = sa.orm.relationship(
        Deployment,
        backref=sa.orm.backref("tasks"),
        foreign_keys=deployment_uuid,
        primaryjoin=(deployment_uuid == Deployment.uuid),
    )


class TaskResult(BASE, RallyBase):
    __tablename__ = "task_results"
    __table_args__ = ()

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    key = sa.Column(sa_types.MutableJSONEncodedDict, nullable=False)
    data = sa.Column(sa_types.BigMutableJSONEncodedDict, nullable=False)

    task_uuid = sa.Column(sa.String(36), sa.ForeignKey("tasks.uuid"))
    task = sa.orm.relationship(Task,
                               backref=sa.orm.backref("results"),
                               foreign_keys=task_uuid,
                               primaryjoin="TaskResult.task_uuid == Task.uuid")


class Verification(BASE, RallyBase):
    """Represents a verifier result."""

    __tablename__ = "verifications"
    __table_args__ = (
        sa.Index("verification_uuid", "uuid", unique=True),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    deployment_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Deployment.uuid),
        nullable=False,
    )

    status = sa.Column(sa.Enum(*list(consts.TaskStatus),
                       name="enum_tasks_status"),
                       default=consts.TaskStatus.INIT,
                       nullable=False)
    set_name = sa.Column(sa.String(20))

    tests = sa.Column(sa.Integer, default=0)
    # TODO(andreykurilin): remove this variable, when rally will support db
    #   migrations. Reason: It is not used anywhere :)
    errors = sa.Column(sa.Integer, default=0)
    failures = sa.Column(sa.Integer, default=0)
    time = sa.Column(sa.Float, default=0.0)


class VerificationResult(BASE, RallyBase):
    __tablename__ = "verification_results"
    __table_args__ = ()

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    verification_uuid = sa.Column(sa.String(36),
                                  sa.ForeignKey("verifications.uuid"))

    data = sa.Column(sa_types.BigMutableJSONEncodedDict, nullable=False)


class Worker(BASE, RallyBase):
    __tablename__ = "workers"
    __table_args__ = (
        schema.UniqueConstraint("hostname", name="uniq_worker@hostname"),
    )
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    hostname = sa.Column(sa.String(255))


# TODO(boris-42): Remove it after oslo.db > 1.4.1 will be released.
def drop_all_objects(engine):
    """Drop all database objects.

    Drops all database objects remaining on the default schema of the given
    engine. Per-db implementations will also need to drop items specific to
    those systems, such as sequences, custom types (e.g. pg ENUM), etc.
    """
    with engine.begin() as conn:
        inspector = sa.inspect(engine)
        metadata = schema.MetaData()
        tbs = []
        all_fks = []

        for table_name in inspector.get_table_names():
            fks = []
            for fk in inspector.get_foreign_keys(table_name):
                if not fk["name"]:
                    continue
                fks.append(
                    schema.ForeignKeyConstraint((), (), name=fk["name"]))
            table = schema.Table(table_name, metadata, *fks)
            tbs.append(table)
            all_fks.extend(fks)

        if engine.name != "sqlite":
            for fkc in all_fks:
                conn.execute(schema.DropConstraint(fkc))
        for table in tbs:
            conn.execute(schema.DropTable(table))

        if engine.name == "postgresql":
            if compat_utils.sqla_100:
                enums = [e["name"] for e in sa.inspect(conn).get_enums()]
            else:
                enums = conn.dialect._load_enums(conn).keys()

            for e in enums:
                conn.execute("DROP TYPE %s" % e)


def drop_db():
    # NOTE(LimingWu): We can't direct import the api module. that will
    # result in the cyclic reference import since the api has imported
    # this module.
    from rally.common.db.sqlalchemy import api as sa_api
    drop_all_objects(sa_api.get_engine())
