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

"""Defines interface for DB access.

The underlying driver is loaded as a :class:`LazyPluggable`.

Functions in this module are imported into the rally.common.db namespace.
Call these functions from rally.common.db namespace, not the
rally.common.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface. Currently, many of these objects are sqlalchemy objects that
implement a dictionary interface. However, a future goal is to have all of
these objects be simple dictionaries.


**Related Flags**

:backend:  string to lookup in the list of LazyPluggable backends.
           `sqlalchemy` is the only supported backend right now.

:connection:  string specifying the sqlalchemy connection to use, like:
              `sqlite:///var/lib/cinder/cinder.sqlite`.

:enable_new_services:  when adding a new service to the database, is it in the
                       pool of available hardware (Default: True)

"""

import datetime as dt
import functools
import six
import tempfile
import time

from oslo_db import exception as db_exc
from oslo_db import options as db_options
from oslo_db.sqlalchemy import session as db_session
import sqlalchemy as sa
import sqlalchemy.orm   # noqa

from rally.common import cfg
from rally.common.db import models
from rally import consts
from rally import exceptions
from rally.task.processing import charts


CONF = cfg.CONF

db_options.set_defaults(
    CONF, connection="sqlite:///%s/rally.sqlite" % tempfile.gettempdir())

_FACADE = None
_SESSION_MAKER = None


def _create_facade_lazily():
    global _FACADE

    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)

    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session():
    global _SESSION_MAKER

    if not _SESSION_MAKER:
        _SESSION_MAKER = sa.orm.sessionmaker()
        _SESSION_MAKER.configure(bind=get_engine())

    return _SESSION_MAKER()


def engine_reset():
    global _FACADE, _SESSION_MAKER
    _FACADE = None
    _SESSION_MAKER = None


def serialize(data):
    if data is None:
        return None
    if isinstance(data, (six.integer_types,
                         six.string_types,
                         six.text_type,
                         dt.date,
                         dt.time,
                         float,
                         )):
        return data
    if isinstance(data, models.RallyBase):
        result = data.as_dict()
        for k in result:
            result[k] = serialize(result[k])
        return result
    if isinstance(data, (list, tuple)):
        return [serialize(d) for d in data]
    if isinstance(data, dict):
        result = {}
        for k in data:
            result[k] = serialize(data[k])
        return result

    raise ValueError("data has wrong type %s" % data)


def with_session(f):

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        session = get_session()
        session.expire_on_commit = False
        try:
            result = f(session, *args, **kwargs)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return serialize(result)

    return wrapper


@with_session
def tags_get(session, uuid, tag_type):
    query = session.query(models.Tag.tag).filter_by(uuid=uuid, type=tag_type)
    return [t.tag for t in query.distinct().all()]


def _uuids_by_tags_get(session, tag_type, tags):
    tags = (session.query(models.Tag.uuid)
                   .filter(models.Tag.type == tag_type,
                           models.Tag.tag.in_(tags)).distinct())
    return [t.uuid for t in tags.all()]


def _task_workload_data_get_all(session, workload_uuid):
    results = (session.query(models.WorkloadData)
                      .filter_by(workload_uuid=workload_uuid)
                      .order_by(models.WorkloadData.chunk_order.asc()))

    return sorted([raw for workload_data in results
                   for raw in workload_data.chunk_data["raw"]],
                  key=lambda x: x["timestamp"])


def _subtasks_get_all_by_task_uuid(session, task_uuid):
    result = session.query(models.Subtask).filter_by(task_uuid=task_uuid).all()
    subtasks = []
    for subtask in result:
        subtask = subtask.as_dict()
        subtask["workloads"] = []
        workloads = (session.query(models.Workload).
                     filter_by(subtask_uuid=subtask["uuid"]).all())
        for workload in workloads:
            workload = workload.as_dict()
            workload["data"] = _task_workload_data_get_all(
                session, workload["uuid"])
            subtask["workloads"].append(workload)
        subtasks.append(subtask)
    return subtasks


@with_session
def task_get(session, uuid=None, detailed=False):

    task = session.query(models.Task).filter_by(uuid=uuid).first()
    if not task:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="tasks")
    task = task.as_dict()
    task["tags"] = sorted(tags_get(uuid, consts.TagType.TASK))

    if detailed:
        task["subtasks"] = _subtasks_get_all_by_task_uuid(session, uuid)

    return task


@with_session
def task_get_status(session, uuid=None):
    task = (session.query(models.Task)
                   .options(sa.orm.load_only("status"))
                   .filter_by(uuid=uuid).first())
    if not task:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="tasks")

    return task.status


@with_session
def task_create(session, values):
    tags = values.pop("tags", [])
    # TODO(ikhudoshyn): currently 'input_task'
    # does not come in 'values'
    # After completely switching to the new
    # DB schema in API we should reconstruct
    # input_task's from associated workloads
    # the same is true for 'pass_sla',
    # 'task_duration', 'validation_result'
    # and 'validation_duration'
    task = models.Task(**values)
    session.add(task)
    session.commit()
    task = task.as_dict()

    if tags:
        session.bulk_save_objects(
            models.Tag(uuid=task["uuid"], tag=t,
                       type=consts.TagType.TASK)
            for t in set(tags))
    task["tags"] = tags
    return task


@with_session
def task_update(session, uuid, values):
    values.pop("uuid", None)
    tags = values.pop("tags", None)

    task = session.query(models.Task).filter_by(uuid=uuid).first()
    if not task:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="tasks")
    task.update(values)
    task = task.as_dict()

    if tags is not None:
        # TODO(boris-42): create separate method for tags editing
        tags_in_db = session.query(models.Tag.tag).filter_by(
            uuid=uuid, type=consts.TagType.TASK).distinct()
        new_tags = set(tags) - set(tags_in_db)
        removed_tags = set(tags_in_db) - set(tags)

        (session.query(models.Tag)
                .filter_by(uuid=uuid, type=consts.TagType.TASK)
                .filter(models.Tag.tag.in_(removed_tags))
                .delete(synchronize_session=False))

        if new_tags:
            session.bulk_save_objects(
                models.Tag(uuid=uuid, tag=t, type=consts.TagType.TASK)
                for t in set(new_tags))
        task["tags"] = tags
    else:
        task["tags"] = []
    return task


@with_session
def task_update_status(session, uuid, status, allowed_statuses):
    result = (session.query(models.Task)
                     .filter(models.Task.uuid == uuid,
                             models.Task.status.in_(allowed_statuses))
                     .update({"status": status}, synchronize_session=False))
    if not result:
        raise exceptions.DBRecordNotFound(
            criteria="uuid=%(uuid)s and status in [%(statuses)s]"
                     % {"uuid": uuid, "statuses": ", ".join(allowed_statuses)},
            table="tasks")
    return result


@with_session
def task_list(session, status=None, env=None, tags=None):
    tasks = []
    query = session.query(models.Task)

    filters = {}
    if status is not None:
        filters["status"] = status
    if env is not None:
        filters["env_uuid"] = env_get(env)["uuid"]
    if filters:
        query = query.filter_by(**filters)

    if tags:
        uuids = _uuids_by_tags_get(session, consts.TagType.TASK, tags)
        if not uuids:
            return []
        query = query.filter(models.Task.uuid.in_(uuids))

    for task in query.all():
        task = task.as_dict()
        task["tags"] = sorted(tags_get(task["uuid"], consts.TagType.TASK))
        tasks.append(task)

    return tasks


@with_session
def task_delete(session, uuid, status=None):
    (session.query(models.WorkloadData).filter_by(task_uuid=uuid).
     delete(synchronize_session=False))

    (session.query(models.Workload).filter_by(task_uuid=uuid).
     delete(synchronize_session=False))

    (session.query(models.Subtask).filter_by(task_uuid=uuid).
     delete(synchronize_session=False))

    (session.query(models.Tag).filter_by(
        uuid=uuid, type=consts.TagType.TASK).
     delete(synchronize_session=False))

    query = session.query(models.Task).filter_by(uuid=uuid)
    if status:
        count = query.filter_by(status=status).delete(
            synchronize_session="fetch")
    else:
        count = query.delete(synchronize_session="fetch")
    if not count:
        if status is not None:
            task = query.first()
            if task:
                raise exceptions.DBConflict(
                    "Task `%(uuid)s` in `%(actual)s` status but "
                    "`%(require)s` is required."
                    % {"uuid": uuid,
                       "require": status, "actual": task.status})

        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="tasks")


@with_session
def subtask_create(session, task_uuid, title, description=None, contexts=None):
    subtask = models.Subtask(task_uuid=task_uuid,
                             title=title,
                             description=description or "",
                             contexts=contexts or {})
    session.add(subtask)
    return subtask


@with_session
def subtask_update(session, subtask_uuid, values):
    subtask = session.query(models.Subtask).filter_by(
        uuid=subtask_uuid).first()
    subtask.update(values)
    return subtask


@with_session
def workload_get(session, workload_uuid):
    return session.query(models.Workload).filter_by(uuid=workload_uuid).first()


@with_session
def workload_create(session, task_uuid, subtask_uuid, name, description,
                    position, runner, runner_type, hooks, contexts, sla, args):
    workload = models.Workload(task_uuid=task_uuid,
                               subtask_uuid=subtask_uuid,
                               name=name,
                               description=description,
                               position=position,
                               runner=runner,
                               runner_type=runner_type,
                               hooks=hooks,
                               contexts=contexts or {},
                               sla=sla,
                               args=args)
    session.add(workload)
    return workload


@with_session
def workload_data_create(session, task_uuid, workload_uuid, chunk_order, data):
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
    session.add(workload_data)
    return workload_data


@with_session
def workload_set_results(session, workload_uuid, subtask_uuid, task_uuid,
                         load_duration, full_duration, start_time,
                         sla_results, contexts_results, hooks_results=None):
    workload_results = _task_workload_data_get_all(session, workload_uuid)

    iter_count = len(workload_results)

    failed_iter_count = 0
    max_duration = None
    min_duration = None

    for d in workload_results:
        if d.get("error"):
            failed_iter_count += 1

        duration = d.get("duration", 0)

        if max_duration is None or duration > max_duration:
            max_duration = duration

        if min_duration is None or min_duration > duration:
            min_duration = duration

    durations_stat = charts.MainStatsTable(
        {"total_iteration_count": iter_count})

    for itr in workload_results:
        durations_stat.add_iteration(itr)

    sla = sla_results or []
    # NOTE(ikhudoshyn): we call it 'pass_sla'
    # for the sake of consistency with other models
    # so if no SLAs were specified, then we assume pass_sla == True
    success = all([s.get("success") for s in sla])

    session.query(models.Workload).filter_by(
        uuid=workload_uuid).update(
        {
            "sla_results": {"sla": sla},
            "contexts_results": contexts_results,
            "hooks": hooks_results or [],
            "load_duration": load_duration,
            "full_duration": full_duration,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "total_iteration_count": iter_count,
            "failed_iteration_count": failed_iter_count,
            "start_time": start_time,
            "statistics": {"durations": durations_stat.to_dict()},
            "pass_sla": success}
    )
    task_values = {
        "task_duration": models.Task.task_duration + load_duration}
    if not success:
        task_values["pass_sla"] = False

    subtask_values = {
        "duration": models.Subtask.duration + load_duration}
    if not success:
        subtask_values["pass_sla"] = False
    session.query(models.Task).filter_by(uuid=task_uuid).update(
        task_values)

    session.query(models.Subtask).filter_by(uuid=subtask_uuid).update(
        subtask_values)


@with_session
def env_get(session, uuid_or_name):
    env = (session.query(models.Env)
                  .filter(sa.or_(models.Env.uuid == uuid_or_name,
                                 models.Env.name == uuid_or_name))
                  .first())
    if not env:
        raise exceptions.DBRecordNotFound(
            criteria="uuid or name is %s" % uuid_or_name, table="envs")
    return env


@with_session
def env_get_status(session, uuid):
    resp = (session.query(models.Env)
                   .filter_by(uuid=uuid)
                   .options(sa.orm.load_only("status"))
                   .first())
    if not resp:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="envs")
    return resp.status


@with_session
def env_list(session, status=None):
    query = session.query(models.Env)
    if status:
        query = query.filter_by(status=status)
    return query.all()


@with_session
def env_create(session, name, status, description, extras, config,
               spec, platforms):
    try:
        env_uuid = models.UUID()
        for p in platforms:
            p["env_uuid"] = env_uuid

        env = models.Env(
            name=name, uuid=env_uuid,
            status=status, description=description,
            extras=extras, config=config, spec=spec
        )
        session.add(env)
        session.commit()
        session.bulk_save_objects(
            [models.Platform(**p) for p in platforms])
    except db_exc.DBDuplicateEntry:
        raise exceptions.DBRecordExists(
            field="name", value=name, table="envs")

    return env


@with_session
def env_rename(session, uuid, old_name, new_name):
    try:
        return bool(session.query(models.Env)
                           .filter_by(uuid=uuid, name=old_name)
                           .update({"name": new_name}))
    except db_exc.DBDuplicateEntry:
        raise exceptions.DBRecordExists(
            field="name", value=new_name, table="envs")


@with_session
def env_update(session, uuid, description=None, extras=None, config=None):
    values = {}
    if description is not None:
        values["description"] = description
    if extras is not None:
        values["extras"] = extras
    if config is not None:
        values["config"] = config

    if not values:
        return True

    return bool(session.query(models.Env).filter_by(uuid=uuid).update(values))


@with_session
def env_set_status(session, uuid, old_status, new_status):
    count = (session.query(models.Env)
                    .filter_by(uuid=uuid, status=old_status)
                    .update({"status": new_status}))
    if count:
        return True
    raise exceptions.DBConflict("Env %s should be in status %s actual %s"
                                % (uuid, old_status, env_get_status(uuid)))


@with_session
def env_delete_cascade(session, uuid):
    for model in [models.Task, models.Verification, models.Platform]:
        session.query(model).filter_by(env_uuid=uuid).delete()
    session.query(models.Env).filter_by(uuid=uuid).delete()


@with_session
def platforms_list(session, env_uuid):
    return session.query(models.Platform).filter_by(env_uuid=env_uuid).all()


@with_session
def platform_get(session, uuid):
    p = session.query(models.Platform).filter_by(uuid=uuid).first()
    if not p:
        raise exceptions.DBRecordNotFound(
            criteria="uuid = %s" % uuid, table="platforms")
    return p


@with_session
def platform_set_status(session, uuid, old_status, new_status):
    count = (session.query(models.Platform)
                    .filter_by(uuid=uuid, status=old_status)
                    .update({"status": new_status}))
    if count:
        return True

    platform = platform_get(uuid)
    raise exceptions.DBConflict(
        "Platform %s should be in status %s actual %s"
        % (uuid, old_status, platform["status"]))


@with_session
def platform_set_data(session, uuid, platform_data=None, plugin_data=None):
    values = {}
    if platform_data is not None:
        values["platform_data"] = platform_data
    if plugin_data is not None:
        values["plugin_data"] = plugin_data

    if not values:
        return True

    return bool(
        session.query(models.Platform).filter_by(uuid=uuid).update(values))


@with_session
def verifier_create(session, name, vtype, platform, source, version,
                    system_wide, extra_settings=None):
    verifier = models.Verifier(name=name, type=vtype, platform=platform,
                               source=source, extra_settings=extra_settings,
                               version=version, system_wide=system_wide)
    session.add(verifier)
    return verifier


@with_session
def verifier_get(session, verifier_id):
    return _verifier_get(session, verifier_id)


def _verifier_get(session, verifier_id):
    verifier = (session.query(models.Verifier)
                       .filter(sa.or_(models.Verifier.name == verifier_id,
                                      models.Verifier.uuid == verifier_id))
                       .first())
    if not verifier:
        raise exceptions.DBRecordNotFound(
            criteria="name or uuid is %s" % verifier_id, table="verifiers")
    return verifier


@with_session
def verifier_list(session, status=None):
    query = session.query(models.Verifier)
    if status:
        query = query.filter_by(status=status)
    return query.all()


@with_session
def verifier_delete(session, verifier_id):
    count = (session.query(models.Verifier)
                    .filter(sa.or_(models.Verifier.name == verifier_id,
                                   models.Verifier.uuid == verifier_id))
                    .delete(synchronize_session=False))
    if not count:
        raise exceptions.DBRecordNotFound(
            criteria="name or uuid is %s" % verifier_id, table="verifiers")


@with_session
def verifier_update(session, verifier_id, **properties):
    verifier = _verifier_get(session, verifier_id)
    verifier.update(properties)
    return verifier


@with_session
def verification_create(session, verifier_id, env, tags=None, run_args=None):
    verifier = _verifier_get(session, verifier_id)
    env = env_get(env)
    verification = models.Verification(verifier_uuid=verifier.uuid,
                                       env_uuid=env["uuid"],
                                       run_args=run_args)
    session.add(verification)
    session.commit()

    if tags:
        session.bulk_save_objects(
            models.Tag(uuid=verification.uuid, tag=t,
                       type=consts.TagType.VERIFICATION)
            for t in set(tags)
        )
    return verification


@with_session
def verification_get(session, verification_uuid):
    verification = _verification_get(session, verification_uuid)
    verification.tags = sorted(tags_get(verification.uuid,
                                        consts.TagType.VERIFICATION))
    return verification


def _verification_get(session, verification_uuid):
    verification = session.query(models.Verification).filter_by(
        uuid=verification_uuid).first()
    if not verification:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % verification_uuid, table="verifications")
    return verification


@with_session
def verification_list(session,
                      verifier_id=None, env=None, tags=None, status=None):
    filter_by = {}
    if verifier_id:
        verifier = _verifier_get(session, verifier_id)
        filter_by["verifier_uuid"] = verifier.uuid
    if env:
        env = env_get(env)
        filter_by["env_uuid"] = env["uuid"]
    if status:
        filter_by["status"] = status

    query = session.query(models.Verification)
    if filter_by:
        query = query.filter_by(**filter_by)

    if tags:
        uuids = _uuids_by_tags_get(session,
                                   consts.TagType.VERIFICATION, tags)
        query = query.filter(models.Verification.uuid.in_(uuids))

    verifications = [verification.as_dict() for verification in query.all()]
    for verification in verifications:
        verification["tags"] = sorted(tags_get(verification["uuid"],
                                               consts.TagType.VERIFICATION))
    return verifications


@with_session
def verification_delete(session, uuid):
    count = session.query(models.Verification).filter_by(uuid=uuid).delete()
    if not count:
        raise exceptions.DBRecordNotFound(criteria="uuid: %s" % uuid,
                                          table="verifications")


@with_session
def verification_update(session, verification_uuid, **properties):
    verification = _verification_get(session, verification_uuid)
    verification.update(properties)
    return verification
