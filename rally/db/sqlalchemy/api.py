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
SQLAlchemy implementation for DB.API
"""

import sys

import sqlalchemy as sa

from rally.db.sqlalchemy import models
from rally import exceptions
from rally.openstack.common.db.sqlalchemy import session as db_session


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def db_cleanup():
    db_session.cleanup()


def db_create():
    models.create_db()


def db_drop():
    models.drop_db()


def model_query(model, session=None, read_deleted=False, **kwargs):
    session = session or db_session.get_session()
    query = session.query(model)

    if read_deleted is None:
        return query

    def issubclassof_rally_base(obj):
        return isinstance(obj, type) and issubclass(obj, models.RallyBase)

    base_model = model
    if not issubclassof_rally_base(base_model):
        base_model = kwargs.get('base_model', None)
        if not issubclassof_rally_base(base_model):
            raise Exception(_("model or base_model parameter should be "
                              "subclass of RallyBase"))

    default_deleted_value = base_model.__mapper__.c.deleted.default.arg
    if read_deleted:
        return query.filter(base_model.deleted != default_deleted_value)
    return query.filter(base_model.deleted == default_deleted_value)


def _task_get_by_uuid(uuid, session=None):
    task = model_query(models.Task, session=session).\
                filter_by(uuid=uuid).\
                first()
    if not task:
        raise exceptions.TaskNotFound(uuid=uuid)
    return task


def task_get_by_uuid(uuid):
    return _task_get_by_uuid(uuid)


def task_get_detailed(uuid):
    return model_query(models.Task).\
                options(sa.orm.joinedload('results')).\
                filter_by(uuid=uuid).\
                first()


def task_create(values):
    task = models.Task()
    task.update(values)
    task.save()
    return task


def task_update(uuid, values):
    session = db_session.get_session()
    values.pop('uuid', None)
    with session.begin():
        task = _task_get_by_uuid(uuid, session=session)
        task.update(values)
    return task


def task_list(status=None, active=True):
    read_deleted = None if active is None else not active
    query = model_query(models.Task, read_deleted=read_deleted)
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def task_delete(uuid):
    count = model_query(models.Task).\
                filter_by(uuid=uuid).\
                soft_delete()
    if not count:
        raise exceptions.TaskNotFound(uuid=uuid)


def task_result_create(task_uuid, name, data):
    result = models.TaskResult()
    result.update({"task_uuid": task_uuid, "name": name, "data": data})
    result.save()
    return result
