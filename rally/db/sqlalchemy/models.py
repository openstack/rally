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
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
import uuid

from rally import consts
from rally.db.sqlalchemy import types as sa_types
from rally.openstack.common.db.sqlalchemy import models
from rally.openstack.common.db.sqlalchemy import session


BASE = declarative_base()


def UUID():
    return str(uuid.uuid4())


class RallyBase(models.TimestampMixin,
                models.ModelBase):
    metadata = None


class Task(BASE, RallyBase):
    """Represents a Benchamrk task."""
    __tablename__ = 'tasks'
    __table_args__ = ()

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), default=UUID, nullable=False)
    status = sa.Column(sa.Enum(*list(consts.TaskStatus),
                               name='enum_tasks_status'),
                       default=consts.TaskStatus.INIT, nullable=False)
    failed = sa.Column(sa.Boolean, default=False, nullable=False)
    verification_log = sa.Column(sa.Text, default='', nullable=True)


class TaskResult(BASE, RallyBase):
    __tablename__ = "task_results"
    __table_args__ = ()

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    key = sa.Column(sa_types.MutableDict.as_mutable(sa_types.JSONEncodedDict),
                    nullable=False)
    data = sa.Column(sa_types.MutableDict.as_mutable(sa_types.JSONEncodedDict),
                     nullable=False)

    task_uuid = sa.Column(sa.String(36), sa.ForeignKey('tasks.uuid'))
    task = sa.orm.relationship(Task,
                               backref=sa.orm.backref('results'),
                               foreign_keys=task_uuid,
                               primaryjoin='TaskResult.task_uuid == Task.uuid')


def create_db():
    BASE.metadata.create_all(session.get_engine())


def drop_db():
    engine = session.get_engine()
    OLD_BASE = declarative_base()
    OLD_BASE.metadata.reflect(bind=engine)
    OLD_BASE.metadata.drop_all(engine, checkfirst=True)
