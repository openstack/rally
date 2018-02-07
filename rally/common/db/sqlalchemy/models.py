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
from sqlalchemy.orm import deferred
from sqlalchemy import schema

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
        # NOTE(LimingWu): We can't direct import the api module. That will
        # result in the cyclic reference import since the api has imported
        # this module.
        from rally.common.db.sqlalchemy import api as sa_api

        if session is None:
            session = sa_api.get_session()

        super(RallyBase, self).save(session=session)


class Env(BASE, RallyBase):
    """Represent a environment."""
    __tablename__ = "envs"
    __table_args__ = (
        sa.Index("env_uuid", "uuid", unique=True),
        sa.Index("env_name", "name", unique=True),
        sa.Index("env_status", "status")
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text, default="")
    status = sa.Column(sa.String(36), nullable=False)
    extras = sa.Column(sa_types.MutableJSONEncodedDict, default={})
    config = sa.Column(sa_types.MutableJSONEncodedDict, default={})
    spec = sa.Column(sa_types.MutableJSONEncodedDict, default={})


class Platform(BASE, RallyBase):
    """Represent environment's platforms."""
    __tablename__ = "platforms"
    __table_args__ = (
        sa.Index("platform_uuid", "uuid", unique=True),
        sa.Index("platform_env_uuid", "env_uuid")
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)
    env_uuid = sa.Column(sa.String(36), nullable=False)

    status = sa.Column(sa.String(36), nullable=False)

    plugin_name = sa.Column(sa.String(36), nullable=False)
    plugin_spec = sa.Column(sa_types.MutableJSONEncodedDict, default={},
                            nullable=False)
    plugin_data = sa.Column(sa_types.MutableJSONEncodedDict, default={})

    platform_name = sa.Column(sa.String(36))
    platform_data = sa.Column(sa_types.MutableJSONEncodedDict, default={})


class Task(BASE, RallyBase):
    """Represents a task."""
    __tablename__ = "tasks"
    __table_args__ = (
        sa.Index("task_uuid", "uuid", unique=True),
        sa.Index("task_status", "status"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    env_uuid = sa.Column(sa.String(36), nullable=False)

    # we do not save the whole input task
    input_task = deferred(sa.Column(sa.Text, default=""))

    title = sa.Column(sa.String(128), default="")
    description = sa.Column(sa.Text, default="")

    validation_result = sa.Column(
        sa_types.MutableJSONEncodedDict, default={}, nullable=False)

    # we do not calculate the duration of a validation step yet
    validation_duration = deferred(sa.Column(sa.Float))

    task_duration = sa.Column(sa.Float, default=0.0)
    pass_sla = sa.Column(sa.Boolean, default=True)
    status = sa.Column(sa.String(36), default=consts.TaskStatus.INIT)


class Subtask(BASE, RallyBase):
    __tablename__ = "subtasks"
    __table_args__ = (
        sa.Index("subtask_uuid", "uuid", unique=True),
        sa.Index("subtask_status", "status"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    task_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Task.uuid),
        nullable=False,
    )

    task = sa.orm.relationship(
        Task,
        backref=sa.orm.backref("subtasks"),
        foreign_keys=task_uuid,
        primaryjoin=(task_uuid == Task.uuid),
    )

    title = sa.Column(sa.String(128), default="")
    description = sa.Column(sa.Text, default="")

    # we do not support subtask contexts feature yet, see
    # https://review.openstack.org/#/c/404168/
    contexts = deferred(sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False))

    contexts_results = deferred(sa.Column(
        sa_types.MutableJSONEncodedList, default=[], nullable=False))

    sla = sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False)

    # It is always False for now
    run_in_parallel = deferred(
        sa.Column(sa.Boolean, default=False, nullable=False))

    duration = sa.Column(sa.Float, default=0.0)
    pass_sla = sa.Column(sa.Boolean, default=True)
    status = sa.Column(sa.String(36), default=consts.SubtaskStatus.RUNNING)


class Workload(BASE, RallyBase):
    __tablename__ = "workloads"
    __table_args__ = (
        sa.Index("workload_uuid", "uuid", unique=True),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    task_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Task.uuid),
        nullable=False,
    )

    subtask_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Subtask.uuid),
        nullable=False,
    )

    subtask = sa.orm.relationship(
        Subtask,
        backref=sa.orm.backref("workloads"),
        foreign_keys=subtask_uuid,
        primaryjoin=(subtask_uuid == Subtask.uuid),
    )

    name = sa.Column(sa.String(64), nullable=False)
    description = sa.Column(sa.Text, default="")
    position = sa.Column(sa.Integer, default=0, nullable=False)

    runner = sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False)

    runner_type = sa.Column(sa.String(64), nullable=False)

    contexts = sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False)

    contexts_results = sa.Column(
        sa_types.MutableJSONEncodedList, default=[], nullable=False)

    sla = sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False)

    sla_results = sa.Column(
        sa_types.MutableJSONEncodedDict, default={}, nullable=False)

    args = sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False)

    hooks = sa.Column(
        sa_types.JSONEncodedList, default=[], nullable=False)

    start_time = sa.Column(sa_types.TimeStamp)

    load_duration = sa.Column(sa.Float, default=0)
    full_duration = sa.Column(sa.Float, default=0)
    min_duration = sa.Column(sa.Float)
    max_duration = sa.Column(sa.Float)
    total_iteration_count = sa.Column(sa.Integer, default=0)
    failed_iteration_count = sa.Column(sa.Integer, default=0)

    statistics = sa.Column(
        sa_types.MutableJSONEncodedDict, default={}, nullable=False)

    pass_sla = sa.Column(sa.Boolean, default=True)
    _profiling_data = deferred(sa.Column(sa.Text, default=""))


class WorkloadData(BASE, RallyBase):
    __tablename__ = "workloaddata"
    __table_args__ = (
        sa.Index("workload_data_uuid", "uuid", unique=True),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    task_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Task.uuid),
        nullable=False,
    )

    workload_uuid = sa.Column(
        sa.String(36),
        sa.ForeignKey(Workload.uuid),
        nullable=False,
    )

    workload = sa.orm.relationship(
        Workload,
        backref=sa.orm.backref("workload_data"),
        foreign_keys=workload_uuid,
        primaryjoin=(workload_uuid == Workload.uuid),
    )

    chunk_order = sa.Column(sa.Integer, nullable=False)
    chunk_data = sa.Column(
        sa_types.MutableJSONEncodedDict, default={}, nullable=False)
    # all these fields are not used
    iteration_count = deferred(sa.Column(sa.Integer, nullable=False))
    failed_iteration_count = deferred(sa.Column(sa.Integer, nullable=False))
    chunk_size = deferred(sa.Column(sa.Integer, nullable=False))
    compressed_chunk_size = deferred(sa.Column(sa.Integer, nullable=False))
    started_at = deferred(sa.Column(
        sa.DateTime, default=lambda: timeutils.utcnow(), nullable=False))
    finished_at = deferred(sa.Column(
        sa.DateTime, default=lambda: timeutils.utcnow(), nullable=False))


class Tag(BASE, RallyBase):
    __tablename__ = "tags"
    __table_args__ = (
        sa.Index("d_type_tag", "uuid", "type", "tag", unique=True),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    type = sa.Column(sa.String(36), nullable=False)

    tag = sa.Column(sa.String(255), nullable=False)


class Verifier(BASE, RallyBase):
    """Represents a verifier."""

    __tablename__ = "verifiers"
    __table_args__ = (
        sa.Index("verifier_uuid", "uuid", unique=True),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    name = sa.Column(sa.String(255), unique=True)
    description = sa.Column(sa.Text)

    type = sa.Column(sa.String(255), nullable=False)
    platform = sa.Column(sa.String(255))

    source = sa.Column(sa.String(255))
    version = sa.Column(sa.String(255))
    system_wide = sa.Column(sa.Boolean)

    status = sa.Column(sa.String(36), default=consts.VerifierStatus.INIT,
                       nullable=False)

    extra_settings = sa.Column(sa_types.MutableJSONEncodedDict)


class Verification(BASE, RallyBase):
    """Represents a verification."""

    __tablename__ = "verifications"
    __table_args__ = (
        sa.Index("verification_uuid", "uuid", unique=True),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

    verifier_uuid = sa.Column(sa.String(36),
                              sa.ForeignKey(Verifier.uuid),
                              nullable=False)
    env_uuid = sa.Column(sa.String(36), nullable=False)

    run_args = sa.Column(sa_types.MutableJSONEncodedDict)

    status = sa.Column(sa.String(36), default=consts.VerificationStatus.INIT,
                       nullable=False)

    tests_count = sa.Column(sa.Integer, default=0)
    failures = sa.Column(sa.Integer, default=0)
    skipped = sa.Column(sa.Integer, default=0)
    success = sa.Column(sa.Integer, default=0)
    unexpected_success = sa.Column(sa.Integer, default=0)
    expected_failures = sa.Column(sa.Integer, default=0)
    tests_duration = sa.Column(sa.Float, default=0.0)

    tests = sa.Column(sa_types.MutableJSONEncodedDict, default={})


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
    # NOTE(LimingWu): We can't direct import the api module. That will
    # result in the cyclic reference import since the api has imported
    # this module.
    from rally.common.db.sqlalchemy import api as sa_api
    drop_all_objects(sa_api.get_engine())
