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

from oslo.config import cfg
import sqlalchemy as sa

from rally.db.sqlalchemy import models
from rally import exceptions
from rally.openstack.common.db.sqlalchemy import session as db_session


CONF = cfg.CONF

CONF.import_opt('connection',
                'rally.openstack.common.db.options',
                group='database')

_FACADE = None


def _create_facade_lazily():
    global _FACADE

    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(
            CONF.database.connection, CONF)

    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def db_cleanup():
    global _FACADE

    _FACADE = None


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
    session = session or get_session()
    query = session.query(model)

    def issubclassof_rally_base(obj):
        return isinstance(obj, type) and issubclass(obj, models.RallyBase)

    if not issubclassof_rally_base(model):
        raise Exception(_("The model should be a subclass of RallyBase"))

    return query


def _task_get(uuid, session=None):
    task = model_query(models.Task, session=session).\
                filter_by(uuid=uuid).\
                first()
    if not task:
        raise exceptions.TaskNotFound(uuid=uuid)
    return task


def task_get(uuid):
    return _task_get(uuid)


def task_get_detailed(uuid):
    return model_query(models.Task).\
                options(sa.orm.joinedload('results')).\
                filter_by(uuid=uuid).\
                first()


def task_get_detailed_last():
    return model_query(models.Task).\
                options(sa.orm.joinedload('results')).\
                order_by(models.Task.id.desc()).first()


def task_create(values):
    task = models.Task()
    task.update(values)
    task.save()
    return task


def task_update(uuid, values):
    session = get_session()
    values.pop('uuid', None)
    with session.begin():
        task = _task_get(uuid, session=session)
        task.update(values)
    return task


def task_list(status=None):
    query = model_query(models.Task)
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def task_delete(uuid, status=None):
    session = get_session()
    with session.begin():
        query = base_query = model_query(models.Task).filter_by(uuid=uuid)
        if status is not None:
            query = base_query.filter_by(status=status)

        model_query(models.TaskResult).\
            filter_by(task_uuid=uuid).\
            delete(synchronize_session=False)

        count = query.delete(synchronize_session=False)
        if not count:
            if status is not None:
                task = base_query.first()
                if task:
                    raise exceptions.TaskInvalidStatus(uuid=uuid,
                                                       require=status,
                                                       actual=task.status)
            raise exceptions.TaskNotFound(uuid=uuid)


def task_result_create(task_uuid, key, data):
    result = models.TaskResult()
    result.update({"task_uuid": task_uuid, "key": key, "data": data})
    result.save()
    return result


def task_result_get_all_by_uuid(uuid):
    return model_query(models.TaskResult).\
                filter_by(task_uuid=uuid).\
                all()


def _deployment_get(uuid, session=None):
    deploy = model_query(models.Deployment, session=session).\
                filter_by(uuid=uuid).\
                first()
    if not deploy:
        raise exceptions.DeploymentNotFound(uuid=uuid)
    return deploy


def deployment_create(values):
    deployment = models.Deployment()
    deployment.update(values)
    deployment.save()
    return deployment


def deployment_delete(uuid):
    session = get_session()
    with session.begin():
        count = model_query(models.Resource, session=session).\
                filter_by(deployment_uuid=uuid).\
                count()
        if count:
            raise exceptions.DeploymentIsBusy(uuid=uuid)

        count = model_query(models.Deployment, session=session).\
            filter_by(uuid=uuid).\
            delete(synchronize_session=False)
        if not count:
            raise exceptions.DeploymentNotFound(uuid=uuid)


def deployment_get(uuid):
    return _deployment_get(uuid)


def deployment_update(uuid, values):
    session = get_session()
    values.pop('uuid', None)
    with session.begin():
        deploy = _deployment_get(uuid, session=session)
        deploy.update(values)
    return deploy


def deployment_list(status=None, parent_uuid=None):
    query = model_query(models.Deployment).filter_by(parent_uuid=parent_uuid)
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def resource_create(values):
    resource = models.Resource()
    resource.update(values)
    resource.save()
    return resource


def resource_get_all(deployment_uuid, provider_name=None, type=None):
    query = model_query(models.Resource).\
                filter_by(deployment_uuid=deployment_uuid)
    if provider_name is not None:
        query = query.filter_by(provider_name=provider_name)
    if type is not None:
        query = query.filter_by(type=type)
    return query.all()


def resource_delete(id):
    count = model_query(models.Resource).\
                filter_by(id=id).\
                delete(synchronize_session=False)
    if not count:
        raise exceptions.ResourceNotFound(id=id)


def verification_create(deployment_uuid):
    verification = models.Verification()
    verification.update({"deployment_uuid": deployment_uuid})
    verification.save()
    return verification


def verification_get(verification_uuid, session=None):
    verification = model_query(models.Verification, session=session).\
        filter_by(uuid=verification_uuid).first()
    if not verification:
        raise exceptions.NotFoundException(
            "Can't find any verification with following UUID '%s'." %
            verification_uuid)
    return verification


def verification_update(verification_uuid, values):
    session = get_session()
    with session.begin():
        verification = verification_get(verification_uuid, session=session)
        verification.update(values)
    return verification


def verification_list(status=None):
    query = model_query(models.Verification)
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def verification_delete(verification_uuid):
    count = model_query(models.Verification).filter_by(id=verification_uuid).\
        delete(synchronize_session=False)
    if not count:
        raise exceptions.NotFoundException(
            "Can't find any verification with following UUID '%s'." %
            verification_uuid)


def verification_result_create(verification_uuid, data):
    result = models.VerificationResult()
    result.update({"verification_uuid": verification_uuid,
                   "data": data})
    result.save()
    return result


def verification_result_get(verification_uuid):
    result = model_query(models.VerificationResult).\
        filter_by(verification_uuid=verification_uuid).first()
    if not result:
        raise exceptions.NotFoundException(
            "No results for following UUID '%s'." % verification_uuid)
    return result
