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

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_utils import timeutils
import sqlalchemy as sa
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import load_only as sa_loadonly

from rally.common.db.sqlalchemy import models
from rally.common.i18n import _
from rally import exceptions


CONF = cfg.CONF

_FACADE = None


def _create_facade_lazily():
    global _FACADE

    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)

    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


class Connection(object):

    def db_cleanup(self):
        global _FACADE

        _FACADE = None

    def db_create(self):
        models.create_db()

    def db_drop(self):
        models.drop_db()

    def model_query(self, model, session=None):
        """The helper method to create query.

        :param model: The instance of
                      :class:`rally.common.db.sqlalchemy.models.RallyBase` to
                      request it.
        :param session: Reuse the session object or get new one if it is
                        None.
        :returns: The query object.
        :raises: :class:`Exception` when the model is not a sublcass of
                 :class:`rally.common.db.sqlalchemy.models.RallyBase`.
        """
        session = session or get_session()
        query = session.query(model)

        def issubclassof_rally_base(obj):
            return isinstance(obj, type) and issubclass(obj, models.RallyBase)

        if not issubclassof_rally_base(model):
            raise Exception(_("The model should be a subclass of RallyBase"))

        return query

    def _task_get(self, uuid, load_only=None, session=None):
        pre_query = self.model_query(models.Task, session=session)
        if load_only:
            pre_query = pre_query.options(sa_loadonly(load_only))

        task = pre_query.filter_by(uuid=uuid).first()
        if not task:
            raise exceptions.TaskNotFound(uuid=uuid)
        return task

    def task_get(self, uuid):
        return self._task_get(uuid)

    def task_get_detailed(self, uuid):
        return (self.model_query(models.Task).
                options(sa.orm.joinedload("results")).
                filter_by(uuid=uuid).first())

    def task_get_status(self, uuid):
        return self._task_get(uuid, load_only="status").status

    def task_get_detailed_last(self):
        return (self.model_query(models.Task).
                options(sa.orm.joinedload("results")).
                order_by(models.Task.id.desc()).first())

    def task_create(self, values):
        task = models.Task()
        task.update(values)
        task.save()
        return task

    def task_update(self, uuid, values):
        session = get_session()
        values.pop("uuid", None)
        with session.begin():
            task = self._task_get(uuid, session=session)
            task.update(values)
        return task

    def task_update_status(self, uuid, statuses, status_value):
        session = get_session()
        query = (
            session.query(models.Task).filter(
                models.Task.uuid == uuid, models.Task.status.in_(
                    statuses)).
            update({"status": status_value}, synchronize_session=False)
        )
        if not query:
            status = " or ".join(statuses)
            msg = _("Task with uuid='%(uuid)s' and in statuses:'"
                    "%(statuses)s' not found.'") % {"uuid": uuid,
                                                    "statuses": status}
            raise exceptions.RallyException(msg)
        return query

    def task_list(self, status=None, deployment=None):
        query = self.model_query(models.Task)

        filters = {}
        if status is not None:
            filters["status"] = status
        if deployment is not None:
            filters["deployment_uuid"] = self.deployment_get(
                deployment)["uuid"]

        if filters:
            query = query.filter_by(**filters)
        return query.all()

    def task_delete(self, uuid, status=None):
        session = get_session()
        with session.begin():
            query = base_query = (self.model_query(models.Task).
                                  filter_by(uuid=uuid))
            if status is not None:
                query = base_query.filter_by(status=status)

            (self.model_query(models.TaskResult).filter_by(task_uuid=uuid).
             delete(synchronize_session=False))

            count = query.delete(synchronize_session=False)
            if not count:
                if status is not None:
                    task = base_query.first()
                    if task:
                        raise exceptions.TaskInvalidStatus(uuid=uuid,
                                                           require=status,
                                                           actual=task.status)
                raise exceptions.TaskNotFound(uuid=uuid)

    def task_result_create(self, task_uuid, key, data):
        result = models.TaskResult()
        result.update({"task_uuid": task_uuid, "key": key, "data": data})
        result.save()
        return result

    def task_result_get_all_by_uuid(self, uuid):
        return (self.model_query(models.TaskResult).
                filter_by(task_uuid=uuid).all())

    def _deployment_get(self, deployment, session=None):
        stored_deployment = self.model_query(
            models.Deployment,
            session=session).filter_by(name=deployment).first()
        if not stored_deployment:
            stored_deployment = self.model_query(
                models.Deployment,
                session=session).filter_by(uuid=deployment).first()

        if not stored_deployment:
            raise exceptions.DeploymentNotFound(deployment=deployment)
        return stored_deployment

    def deployment_create(self, values):
        deployment = models.Deployment()
        try:
            deployment.update(values)
            deployment.save()
        except db_exc.DBDuplicateEntry:
            raise exceptions.DeploymentNameExists(deployment=values["name"])
        return deployment

    def deployment_delete(self, uuid):
        session = get_session()
        with session.begin():
            count = (self.model_query(models.Resource, session=session).
                     filter_by(deployment_uuid=uuid).count())
            if count:
                raise exceptions.DeploymentIsBusy(uuid=uuid)

            count = (self.model_query(models.Deployment, session=session).
                     filter_by(uuid=uuid).delete(synchronize_session=False))
            if not count:
                raise exceptions.DeploymentNotFound(deployment=uuid)

    def deployment_get(self, deployment):
        return self._deployment_get(deployment)

    def deployment_update(self, deployment, values):
        session = get_session()
        values.pop("uuid", None)
        with session.begin():
            dpl = self._deployment_get(deployment, session=session)
            dpl.update(values)
        return dpl

    def deployment_list(self, status=None, parent_uuid=None, name=None):
        query = (self.model_query(models.Deployment).
                 filter_by(parent_uuid=parent_uuid))

        if name:
            query = query.filter_by(name=name)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def resource_create(self, values):
        resource = models.Resource()
        resource.update(values)
        resource.save()
        return resource

    def resource_get_all(self, deployment_uuid, provider_name=None, type=None):
        query = (self.model_query(models.Resource).
                 filter_by(deployment_uuid=deployment_uuid))
        if provider_name is not None:
            query = query.filter_by(provider_name=provider_name)
        if type is not None:
            query = query.filter_by(type=type)
        return query.all()

    def resource_delete(self, id):
        count = (self.model_query(models.Resource).
                 filter_by(id=id).delete(synchronize_session=False))
        if not count:
            raise exceptions.ResourceNotFound(id=id)

    def verification_create(self, deployment_uuid):
        verification = models.Verification()
        verification.update({"deployment_uuid": deployment_uuid})
        verification.save()
        return verification

    def verification_get(self, verification_uuid, session=None):
        verification = (self.model_query(models.Verification, session=session).
                        filter_by(uuid=verification_uuid).first())
        if not verification:
            raise exceptions.NotFoundException(
                "Can't find any verification with following UUID '%s'." %
                verification_uuid)
        return verification

    def verification_update(self, verification_uuid, values):
        session = get_session()
        with session.begin():
            verification = self.verification_get(verification_uuid,
                                                 session=session)
            verification.update(values)
        return verification

    def verification_list(self, status=None):
        query = self.model_query(models.Verification)
        if status is not None:
            query = query.filter_by(status=status)
        return query.all()

    def verification_delete(self, verification_uuid):
        count = (self.model_query(models.Verification).
                 filter_by(id=verification_uuid).
                 delete(synchronize_session=False))
        if not count:
            raise exceptions.NotFoundException(
                "Can't find any verification with following UUID '%s'." %
                verification_uuid)

    def verification_result_create(self, verification_uuid, data):
        result = models.VerificationResult()
        result.update({"verification_uuid": verification_uuid,
                       "data": data})
        result.save()
        return result

    def verification_result_get(self, verification_uuid):
        result = (self.model_query(models.VerificationResult).
                  filter_by(verification_uuid=verification_uuid).first())
        if not result:
            raise exceptions.NotFoundException(
                "No results for following UUID '%s'." % verification_uuid)
        return result

    def register_worker(self, values):
        try:
            worker = models.Worker()
            worker.update(values)
            worker.update({"updated_at": timeutils.utcnow()})
            worker.save()
            return worker
        except db_exc.DBDuplicateEntry:
            raise exceptions.WorkerAlreadyRegistered(
                worker=values["hostname"])

    def get_worker(self, hostname):
        try:
            return (self.model_query(models.Worker).
                    filter_by(hostname=hostname).one())
        except NoResultFound:
            raise exceptions.WorkerNotFound(worker=hostname)

    def unregister_worker(self, hostname):
        count = (self.model_query(models.Worker).
                 filter_by(hostname=hostname).delete())
        if count == 0:
            raise exceptions.WorkerNotFound(worker=hostname)

    def update_worker(self, hostname):
        count = (self.model_query(models.Worker).
                 filter_by(hostname=hostname).
                 update({"updated_at": timeutils.utcnow()}))
        if count == 0:
            raise exceptions.WorkerNotFound(worker=hostname)
