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


def model_query(model, session=None):
    """The helper method to create query.

    :param model: The instance of
                  :class:`rally.db.sqlalchemy.models.RallyBase` to
                  request it.
    :param session: Reuse the session object or get new one if it is
                    None.
    :returns: The query object.
    :raises: :class:`Exception` when the model is not a sublcass of
             :class:`rally.db.sqlalchemy.models.RallyBase`.
    """
    session = session or db_session.get_session()
    query = session.query(model)

    def issubclassof_rally_base(obj):
        return isinstance(obj, type) and issubclass(obj, models.RallyBase)

    if not issubclassof_rally_base(model):
        raise Exception(_("The model should be a subclass of RallyBase"))

    return query


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


def task_list(status=None):
    query = model_query(models.Task)
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def task_delete(uuid, status=None):
    session = db_session.get_session()
    with session.begin():
        query = base_query = model_query(models.Task).filter_by(uuid=uuid)
        if status is not None:
            query = base_query.filter_by(status=status)
        count = query.delete(synchronize_session=False)
        if not count:
            if status is not None:
                task = base_query.first()
                if task:
                    raise exceptions.TaskInvalidStatus(uuid=uuid,
                                                       require=status,
                                                       actual=task.status)
            raise exceptions.TaskNotFound(uuid=uuid)

        model_query(models.TaskResult).\
            filter_by(task_uuid=uuid).\
            delete(synchronize_session=False)


def task_result_create(task_uuid, key, data):
    result = models.TaskResult()
    result.update({"task_uuid": task_uuid, "key": key, "data": data})
    result.save()
    return result


def task_result_get_all_by_uuid(uuid):
    return model_query(models.TaskResult).\
                filter_by(task_uuid=uuid).\
                all()
