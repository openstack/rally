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

import datetime as dt
import json
import os
import time

import alembic
from alembic import config as alembic_config
import alembic.migration as alembic_migration
from alembic import script as alembic_script
from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_utils import timeutils
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import load_only as sa_loadonly

from rally.common.db import api as db_api
from rally.common.db.sqlalchemy import models
from rally.common.i18n import _
from rally import consts
from rally import exceptions


CONF = cfg.CONF

_FACADE = None

INITIAL_REVISION_UUID = "ca3626f62937"


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


def _alembic_config():
    path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    config = alembic_config.Config(path)
    return config


def fix_deployment(fn):
    # NOTE(ikhudoshyn): Remove this once new deployment model
    # get adopted.
    # New DB schema for Deployment was introduced in
    # https://github.com/openstack/rally/
    #        commit/433cf080ea02f448df1ce33c620c8b30910338cd
    # yet old one is used over the codebase.
    # This decorator restores attributes that are missing from
    # the new model.
    """Restore old deployment model's attributes

    This decorator restores deployment properties "admin" and "users"
    moved into "credentials" attribute of DB model.
    """

    def fix(o):
        if isinstance(o, list):
            return [fix(deployment) for deployment in o]
        else:
            if not o.get("admin"):
                o["admin"] = o["credentials"][0][1]["admin"]
            if not o.get("users"):
                o["users"] = o["credentials"][0][1]["users"]
            return o

    def wrapper(*args, **kwargs):
        deployment = fn(*args, **kwargs)
        return fix(deployment)
    return wrapper


class Connection(object):

    def engine_reset(self):
        global _FACADE

        _FACADE = None

    def schema_cleanup(self):
        models.drop_db()

    def schema_revision(self, config=None, engine=None, detailed=False):
        """Current database revision.

        :param config: Instance of alembic config
        :param engine: Instance of DB engine
        :param detailed: whether to return a dict with detailed data
        :rtype detailed: bool
        :returns: Database revision
        :rtype: string
        :rtype: dict
        """
        engine = engine or get_engine()
        with engine.connect() as conn:
            context = alembic_migration.MigrationContext.configure(conn)
            revision = context.get_current_revision()
        if detailed:
            config = config or _alembic_config()
            sc_dir = alembic_script.ScriptDirectory.from_config(config)
            return {"revision": revision,
                    "current_head": sc_dir.get_current_head()}
        return revision

    def schema_upgrade(self, revision=None, config=None, engine=None):
        """Used for upgrading database.

        :param revision: Desired database version
        :type revision: string
        :param config: Instance of alembic config
        :param engine: Instance of DB engine
        """
        revision = revision or "head"
        config = config or _alembic_config()
        engine = engine or get_engine()

        if self.schema_revision() is None:
            self.schema_stamp(INITIAL_REVISION_UUID, config=config)

        alembic.command.upgrade(config, revision or "head")

    def schema_create(self, config=None, engine=None):
        """Create database schema from models description.

        Can be used for initial installation instead of upgrade('head').
        :param config: Instance of alembic config
        :param engine: Instance of DB engine
        """
        engine = engine or get_engine()

        # NOTE(viktors): If we will use metadata.create_all() for non empty db
        #                schema, it will only add the new tables, but leave
        #                existing as is. So we should avoid of this situation.
        if self.schema_revision(engine=engine) is not None:
            raise db_exc.DbMigrationError("DB schema is already under version"
                                          " control. Use upgrade() instead")

        models.BASE.metadata.create_all(engine)
        self.schema_stamp("head", config=config)

    def schema_stamp(self, revision, config=None):
        """Stamps database with provided revision.

        Don't run any migrations.
        :param revision: Should match one from repository or head - to stamp
                         database with most recent revision
        :type revision: string
        :param config: Instance of alembic config
        """
        config = config or _alembic_config()
        return alembic.command.stamp(config, revision=revision)

    def model_query(self, model, session=None):
        """The helper method to create query.

        :param model: The instance of
                      :class:`rally.common.db.sqlalchemy.models.RallyBase` to
                      request it.
        :param session: Reuse the session object or get new one if it is
                        None.
        :returns: The query object.
        :raises Exception: when the model is not a sublcass of
                 :class:`rally.common.db.sqlalchemy.models.RallyBase`.
        """
        session = session or get_session()
        query = session.query(model)

        def issubclassof_rally_base(obj):
            return isinstance(obj, type) and issubclass(obj, models.RallyBase)

        if not issubclassof_rally_base(model):
            raise Exception(_("The model should be a subclass of RallyBase"))

        return query

    def _tags_get(self, uuid, tag_type):
        tags = (self.model_query(models.Tag).
                filter_by(uuid=uuid, type=tag_type).all())

        return list(set(t.tag for t in tags))

    def _task_get(self, uuid, load_only=None, session=None):
        pre_query = self.model_query(models.Task, session=session)
        if load_only:
            pre_query = pre_query.options(sa_loadonly(load_only))

        task = pre_query.filter_by(uuid=uuid).first()
        if not task:
            raise exceptions.TaskNotFound(uuid=uuid)
        return task

    def _make_old_task(self, task):
        tags = self._tags_get(task.uuid, consts.TagType.TASK)
        tag = tags[0] if tags else ""

        return {
            "id": task.id,
            "uuid": task.uuid,
            "deployment_uuid": task.deployment_uuid,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "tag": tag,
            "verification_log": json.dumps(task.validation_result)
        }

    def _make_old_task_result(self, workload, workload_data_list):
        raw_data = [data
                    for workload_data in workload_data_list
                    for data in workload_data.chunk_data["raw"]]
        return {
            "id": workload.id,
            "task_uuid": workload.task_uuid,
            "created_at": workload.created_at,
            "updated_at": workload.updated_at,
            "key": {
                "name": workload.name,
                "pos": workload.position,
                "kw": {
                    "args": workload.args,
                    "runner": workload.runner,
                    "context": workload.context,
                    "sla": workload.sla,
                    "hooks": [r["config"] for r in workload.hooks],
                }
            },
            "data": {
                "raw": raw_data,
                "load_duration": workload.load_duration,
                "full_duration": workload.full_duration,
                "sla": workload.sla_results["sla"],
                "hooks": workload.hooks
            }
        }

    def _task_workload_data_get_all(self, workload_uuid):
        return (self.model_query(models.WorkloadData).
                filter_by(workload_uuid=workload_uuid).
                order_by(models.WorkloadData.chunk_order.asc()))

    # @db_api.serialize
    def task_get(self, uuid):
        task = self._task_get(uuid)
        return self._make_old_task(task)

    # @db_api.serialize
    def task_get_detailed(self, uuid):
        task = self.task_get(uuid)
        task["results"] = self._task_result_get_all_by_uuid(uuid)
        return task

    @db_api.serialize
    def task_get_status(self, uuid):
        return self._task_get(uuid, load_only="status").status

    # @db_api.serialize
    def task_get_detailed_last(self):
        task = (self.model_query(models.Task).
                order_by(models.Task.id.desc()).first())
        task = self._make_old_task(task)
        task["results"] = self._task_result_get_all_by_uuid(task["uuid"])
        return task

    # @db_api.serialize
    def task_create(self, values):
        new_tag = values.pop("tag", None)
        # TODO(ikhudoshyn): currently 'input_task'
        # does not come in 'values'
        # After completely switching to the new
        # DB schema in API we should reconstruct
        # input_task's from associated workloads
        # the same is true for 'pass_sla',
        # 'task_duration', 'validation_result'
        # and 'validation_duration'
        task = models.Task()
        task.update(values)
        task.save()

        if new_tag:
            tag = models.Tag()
            tag.update({
                "uuid": task.uuid,
                "type": consts.TagType.TASK,
                "tag": new_tag
            })
            tag.save()

        return self._make_old_task(task)

    # @db_api.serialize
    def task_update(self, uuid, values):
        session = get_session()
        values.pop("uuid", None)
        new_tag = values.pop("tag", None)
        with session.begin():
            task = self._task_get(uuid, session=session)
            task.update(values)

            if new_tag:
                tag = models.Tag()
                tag.update({
                    "uuid": uuid,
                    "type": consts.TagType.TASK,
                    "tag": new_tag
                })
                tag.save()

        return self._make_old_task(task)

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

    # @db_api.serialize
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

        return [self._make_old_task(task) for task in query.all()]

    def task_delete(self, uuid, status=None):
        session = get_session()
        with session.begin():
            query = base_query = (self.model_query(models.Task).
                                  filter_by(uuid=uuid))
            if status is not None:
                query = base_query.filter_by(status=status)

            (self.model_query(models.WorkloadData).filter_by(task_uuid=uuid).
             delete(synchronize_session=False))

            (self.model_query(models.Workload).filter_by(task_uuid=uuid).
             delete(synchronize_session=False))

            (self.model_query(models.Subtask).filter_by(task_uuid=uuid).
             delete(synchronize_session=False))

            (self.model_query(models.Tag).filter_by(
                uuid=uuid, type=consts.TagType.TASK).
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

    def _task_result_get_all_by_uuid(self, uuid):
        results = []

        workloads = (self.model_query(models.Workload).
                     filter_by(task_uuid=uuid).all())

        for workload in workloads:
            workload_data_list = self._task_workload_data_get_all(
                workload.uuid)

            results.append(
                self._make_old_task_result(workload, workload_data_list))

        return results

    # @db_api.serialize
    def task_result_get_all_by_uuid(self, uuid):
        return self._task_result_get_all_by_uuid(uuid)

    @db_api.serialize
    def subtask_create(self, task_uuid, title, description=None, context=None):
        subtask = models.Subtask(task_uuid=task_uuid)
        subtask.update({
            "title": title,
            "description": description or "",
            "context": context or {},
        })
        subtask.save()
        return subtask

    @db_api.serialize
    def workload_create(self, task_uuid, subtask_uuid, key):
        workload = models.Workload(task_uuid=task_uuid,
                                   subtask_uuid=subtask_uuid)
        workload.update({
            "name": key["name"],
            "position": key["pos"],
            "runner": key["kw"]["runner"],
            "runner_type": key["kw"]["runner"]["type"],
            "context": key["kw"].get("context", {}),
            "sla": key["kw"].get("sla", {}),
            "args": key["kw"].get("args", {}),
            "context_execution": {},
            "statistics": {},
        })
        workload.save()
        return workload

    @db_api.serialize
    def workload_data_create(self, task_uuid, workload_uuid, chunk_order,
                             data):
        workload_data = models.WorkloadData(task_uuid=task_uuid,
                                            workload_uuid=workload_uuid)

        raw_data = data.get("raw", [])
        iter_count = len(raw_data)

        failed_iter_count = 0

        started_at = float("inf")
        finished_at = 0
        for d in raw_data:
            if d.get("error"):
                failed_iter_count += 1

            timestamp = d["timestamp"]
            duration = d["duration"]
            finished = timestamp + duration

            if timestamp < started_at:
                started_at = timestamp

            if finished > finished_at:
                finished_at = finished

        now = time.time()
        if started_at == float("inf"):
            started_at = now
        if finished_at == 0:
            finished_at = now

        workload_data.update({
            "task_uuid": task_uuid,
            "workload_uuid": workload_uuid,
            "chunk_order": chunk_order,
            "iteration_count": iter_count,
            "failed_iteration_count": failed_iter_count,
            "chunk_data": {"raw": raw_data},
            # TODO(ikhudoshyn)
            "chunk_size": 0,
            "compressed_chunk_size": 0,
            "started_at": dt.datetime.fromtimestamp(started_at),
            "finished_at": dt.datetime.fromtimestamp(finished_at)
        })
        workload_data.save()
        return workload_data

    @db_api.serialize
    def workload_set_results(self, workload_uuid, data):
        workload = self.model_query(models.Workload).filter_by(
            uuid=workload_uuid).first()

        workload_data_list = self._task_workload_data_get_all(workload.uuid)

        raw_data = [raw
                    for workload_data in workload_data_list
                    for raw in workload_data.chunk_data["raw"]]
        iter_count = len(raw_data)

        failed_iter_count = 0
        max_duration = 0
        min_duration = 0

        success = True

        for d in raw_data:
            if d.get("error"):
                failed_iter_count += 1

            duration = d.get("duration", 0)

            if duration > max_duration:
                max_duration = duration

            if min_duration and min_duration > duration:
                min_duration = duration

        sla = data.get("sla", [])
        # TODO(ikhudoshyn): if no SLA was specified and there are
        # failed iterations is it success?
        # NOTE(ikhudoshyn): we call it 'pass_sla'
        # for the sake of consistency with other models
        # so if no SLAs were specified, then we assume pass_sla == True
        success = all([s.get("success") for s in sla])

        now = timeutils.utcnow()
        delta = dt.timedelta(seconds=data.get("full_duration", 0))
        start = now - delta

        workload.update({
            "task_uuid": workload.task_uuid,
            "subtask_uuid": workload.subtask_uuid,
            "sla_results": {"sla": sla},
            "context_execution": {},
            "hooks": data.get("hooks", []),
            "load_duration": data.get("load_duration", 0),
            "full_duration": data.get("full_duration", 0),
            "min_duration": min_duration,
            "max_duration": max_duration,
            "total_iteration_count": iter_count,
            "failed_iteration_count": failed_iter_count,
            # TODO(ikhudoshyn)
            "start_time": start,
            "statistics": {},
            "pass_sla": success
        })

        # TODO(ikhudoshyn): if pass_sla is False,
        # then update task's and subtask's pass_sla

        # TODO(ikhudoshyn): update task.task_duration
        # and subtask.duration

        workload.save()
        return workload

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

    @fix_deployment
    @db_api.serialize
    def deployment_create(self, values):
        deployment = models.Deployment()
        try:
            # TODO(rpromyshlennikov): remove after credentials refactoring
            values.setdefault(
                "credentials",
                [
                    ["openstack",
                     {"admin": values.get("admin"),
                      "users": values.get("users", [])}]
                ]
            )
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

    @fix_deployment
    @db_api.serialize
    def deployment_get(self, deployment):
        return self._deployment_get(deployment)

    @fix_deployment
    @db_api.serialize
    def deployment_update(self, deployment, values):
        session = get_session()
        values.pop("uuid", None)
        with session.begin():
            dpl = self._deployment_get(deployment, session=session)
            dpl.update(values)
        return dpl

    @fix_deployment
    @db_api.serialize
    def deployment_list(self, status=None, parent_uuid=None, name=None):
        query = (self.model_query(models.Deployment).
                 filter_by(parent_uuid=parent_uuid))

        if name:
            query = query.filter_by(name=name)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    @db_api.serialize
    def resource_create(self, values):
        resource = models.Resource()
        resource.update(values)
        resource.save()
        return resource

    @db_api.serialize
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

    @db_api.serialize
    def verifier_create(self, name, vtype, namespace, source, version,
                        system_wide, extra_settings=None):
        verifier = models.Verifier()
        properties = {"name": name, "type": vtype, "namespace": namespace,
                      "source": source, "extra_settings": extra_settings,
                      "version": version, "system_wide": system_wide}
        verifier.update(properties)
        verifier.save()
        return verifier

    @db_api.serialize
    def verifier_get(self, verifier_id):
        return self._verifier_get(verifier_id)

    def _verifier_get(self, verifier_id, session=None):
        verifier = self.model_query(
            models.Verifier, session=session).filter(
                or_(models.Verifier.name == verifier_id,
                    models.Verifier.uuid == verifier_id)).first()
        if not verifier:
            raise exceptions.ResourceNotFound(id=verifier_id)
        return verifier

    @db_api.serialize
    def verifier_list(self, status=None):
        query = self.model_query(models.Verifier)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def verifier_delete(self, verifier_id):
        session = get_session()
        with session.begin():
            query = self.model_query(
                models.Verifier, session=session).filter(
                    or_(models.Verifier.name == verifier_id,
                        models.Verifier.uuid == verifier_id))
            count = query.delete(synchronize_session=False)
            if not count:
                raise exceptions.ResourceNotFound(id=verifier_id)

    @db_api.serialize
    def verifier_update(self, verifier_id, properties):
        session = get_session()
        with session.begin():
            verifier = self._verifier_get(verifier_id)
            verifier.update(properties)
            verifier.save()
        return verifier

    @db_api.serialize
    def verification_create(self, verifier_id, deployment_id, run_args):
        verifier = self._verifier_get(verifier_id)
        deployment = self._deployment_get(deployment_id)
        verification = models.Verification()
        verification.update({"verifier_uuid": verifier.uuid,
                             "deployment_uuid": deployment["uuid"],
                             "run_args": run_args})
        verification.save()
        return verification

    @db_api.serialize
    def verification_get(self, verification_uuid):
        return self._verification_get(verification_uuid)

    def _verification_get(self, verification_uuid, session=None):
        verification = self.model_query(
            models.Verification, session=session).filter_by(
            uuid=verification_uuid).first()
        if not verification:
            raise exceptions.ResourceNotFound(id=verification_uuid)
        return verification

    @db_api.serialize
    def verification_list(self, verifier_id=None, deployment_id=None,
                          status=None):
        session = get_session()
        with session.begin():
            filter_by = {}
            if verifier_id:
                verifier = self._verifier_get(verifier_id, session=session)
                filter_by["verifier_uuid"] = verifier.uuid
            if deployment_id:
                deployment = self._deployment_get(deployment_id,
                                                  session=session)
                filter_by["deployment_uuid"] = deployment.uuid
            if status:
                filter_by["status"] = status

            query = self.model_query(models.Verification, session=session)
            if filter_by:
                query = query.filter_by(**filter_by)
        return query.all()

    def verification_delete(self, verification_uuid):
        session = get_session()
        with session.begin():
            count = self.model_query(
                models.Verification, session=session).filter_by(
                uuid=verification_uuid).delete(synchronize_session=False)
        if not count:
            raise exceptions.ResourceNotFound(id=verification_uuid)

    @db_api.serialize
    def verification_update(self, verification_uuid, properties):
        session = get_session()
        with session.begin():
            verification = self._verification_get(verification_uuid)
            verification.update(properties)
            verification.save()
        return verification

    @db_api.serialize
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

    @db_api.serialize
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
