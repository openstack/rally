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
import datetime as dt
import uuid

import six
import sqlalchemy as sa
import sqlalchemy.ext.declarative
import sqlalchemy.orm   # noqa (used as sa.orm)

from rally.common.db import sa_types
from rally import consts


BASE = sa.ext.declarative.declarative_base()


def UUID():
    return str(uuid.uuid4())


class RallyBase(six.Iterator):
    """Base class for models."""
    __table_initialized__ = False
    metadata = None

    created_at = sa.Column(sa.DateTime, default=dt.datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=dt.datetime.utcnow,
                           onupdate=dt.datetime.utcnow)

    def as_dict(self):
        result = {}
        res = sa.inspect(self)

        for c in self.__table__.columns:
            if c.key not in res.unloaded:
                result[c.name] = getattr(self, c.name)

        for r in self.__mapper__.relationships:
            if r.key not in res.unloaded:
                result[r.key] = getattr(self, r.key)

        return result

    def get(self, key, default=None):
        return getattr(self, key, default)

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.items():
            setattr(self, k, v)


class Env(BASE, RallyBase):
    """Represent an environment."""
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
    input_task = sa.orm.deferred(sa.Column(sa.Text, default=""))

    title = sa.Column(sa.String(128), default="")
    description = sa.Column(sa.Text, default="")

    validation_result = sa.Column(
        sa_types.MutableJSONEncodedDict, default={}, nullable=False)

    # we do not calculate the duration of a validation step yet
    validation_duration = sa.orm.deferred(sa.Column(sa.Float))

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
    contexts = sa.orm.deferred(sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False))

    contexts_results = sa.orm.deferred(sa.Column(
        sa_types.MutableJSONEncodedList, default=[], nullable=False))

    sla = sa.Column(
        sa_types.JSONEncodedDict, default={}, nullable=False)

    # It is always False for now
    run_in_parallel = sa.orm.deferred(
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

    load_duration = sa.Column(sa.Float, default=0.0)
    full_duration = sa.Column(sa.Float, default=0.0)
    min_duration = sa.Column(sa.Float)
    max_duration = sa.Column(sa.Float)
    total_iteration_count = sa.Column(sa.Integer, default=0)
    failed_iteration_count = sa.Column(sa.Integer, default=0)

    statistics = sa.Column(
        sa_types.MutableJSONEncodedDict, default={}, nullable=False)

    pass_sla = sa.Column(sa.Boolean, default=True)
    _profiling_data = sa.orm.deferred(sa.Column(sa.Text, default=""))


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
    iteration_count = sa.orm.deferred(sa.Column(sa.Integer, nullable=False))
    failed_iteration_count = sa.orm.deferred(sa.Column(
        sa.Integer, nullable=False))
    chunk_size = sa.orm.deferred(sa.Column(
        sa.Integer, nullable=False))
    compressed_chunk_size = sa.orm.deferred(sa.Column(
        sa.Integer, nullable=False))
    started_at = sa.orm.deferred(sa.Column(
        sa.DateTime, default=dt.datetime.utcnow, nullable=False))
    finished_at = sa.orm.deferred(sa.Column(
        sa.DateTime, default=dt.datetime.utcnow, nullable=False))


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
