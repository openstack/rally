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

import collections
import datetime as dt
import time

from oslo_db import exception as db_exc
from oslo_db import options as db_options
from oslo_db.sqlalchemy import session as db_session
import six
import sqlalchemy as sa
import sqlalchemy.orm   # noqa

from rally.common import cfg
from rally.common.db import models
from rally import consts
from rally import exceptions
from rally.task.processing import charts


CONF = cfg.CONF
db_options.set_defaults(CONF, connection="sqlite:////tmp/rally.sqlite")

_FACADE = None


def serialize_data(data):
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
    if isinstance(data, dict):
        return collections.OrderedDict((k, serialize_data(v))
                                       for k, v in data.items())
    if isinstance(data, (list, tuple)):
        return [serialize_data(i) for i in data]

    if isinstance(data, models.RallyBase):
        result = {}
        for key in data.__dict__:
            if not key.startswith("_"):
                result[key] = serialize_data(getattr(data, key))
        return result

    raise exceptions.DBException("Can not serialize %s" % data)


def serialize(fn):
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        return serialize_data(result)
    return wrapper


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


def engine_reset():
    global _FACADE
    _FACADE = None


def model_query(model, session=None):
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
    def issubclassof_rally_base(obj):
        return isinstance(obj, type) and issubclass(obj, models.RallyBase)

    if not issubclassof_rally_base(model):
        raise exceptions.DBException(
            "The model %s should be a subclass of RallyBase" % model)

    session = session or get_session()
    return session.query(model)


def _tags_get(uuid, tag_type, session=None):
    tags = (model_query(models.Tag, session=session).
            filter_by(uuid=uuid, type=tag_type).all())

    return list(set(t.tag for t in tags))


def _uuids_by_tags_get(tag_type, tags):
    tags = (model_query(models.Tag).
            filter(models.Tag.type == tag_type,
                   models.Tag.tag.in_(tags)).all())

    return list(set(tag.uuid for tag in tags))


def _task_get(uuid, load_only=None, session=None):
    pre_query = model_query(models.Task, session=session)
    if load_only:
        pre_query = pre_query.options(sa.orm.load_only(load_only))

    task = pre_query.filter_by(uuid=uuid).first()
    if not task:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="tasks")
    task.tags = sorted(_tags_get(uuid, consts.TagType.TASK, session))
    return task


def _task_workload_data_get_all(workload_uuid):
    session = get_session()
    with session.begin():
        results = (model_query(models.WorkloadData, session=session).
                   filter_by(workload_uuid=workload_uuid).
                   order_by(models.WorkloadData.chunk_order.asc()))

    return sorted([raw for workload_data in results
                   for raw in workload_data.chunk_data["raw"]],
                  key=lambda x: x["timestamp"])


@serialize
def task_get(uuid=None, detailed=False):
    session = get_session()
    task = serialize_data(_task_get(uuid, session=session))

    if detailed:
        task["subtasks"] = _subtasks_get_all_by_task_uuid(
            uuid, session=session)

    return task


@serialize
def task_get_status(uuid):
    return _task_get(uuid, load_only="status").status


@serialize
def task_create(values):
    tags = values.pop("tags", [])
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
    task.save(get_session())

    if tags:
        get_session().bulk_save_objects(
            models.Tag(uuid=task.uuid, tag=t,
                       type=consts.TagType.TASK)
            for t in set(tags)
        )
        task.tags = sorted(_tags_get(task.uuid, consts.TagType.TASK))
    else:
        task.tags = []
    return task


@serialize
def task_update(uuid, values):
    session = get_session()
    values.pop("uuid", None)
    tags = values.pop("tags", None)
    with session.begin():
        task = _task_get(uuid, session=session)
        task.update(values)

        if tags:
            for t in set(tags):
                tag = models.Tag()
                tag.update({"uuid": task.uuid,
                            "type": consts.TagType.TASK,
                            "tag": t})
                tag.save(session)
        # take an updated instance of task
        task = _task_get(uuid, session=session)
    return task


def task_update_status(uuid, status, allowed_statuses):
    session = get_session()
    result = (
        session
        .query(models.Task)
        .filter(models.Task.uuid == uuid,
                models.Task.status.in_(allowed_statuses))
        .update({"status": status}, synchronize_session=False)
    )
    if not result:
        raise exceptions.DBRecordNotFound(
            criteria="uuid=%(uuid)s and status in [%(statuses)s]"
                     % {"uuid": uuid, "statuses": ", ".join(allowed_statuses)},
            table="tasks")
    return result


@serialize
def task_list(status=None, env=None, tags=None):
    session = get_session()
    tasks = []
    with session.begin():
        query = model_query(models.Task)

        filters = {}
        if status is not None:
            filters["status"] = status
        if env is not None:
            filters["env_uuid"] = env_get(env)["uuid"]
        if filters:
            query = query.filter_by(**filters)

        if tags:
            uuids = _uuids_by_tags_get(consts.TagType.TASK, tags)
            if not uuids:
                return []
            query = query.filter(models.Task.uuid.in_(uuids))

        for task in query.all():
            task.tags = sorted(
                _tags_get(task.uuid, consts.TagType.TASK, session))
            tasks.append(task)

    return tasks


def task_delete(uuid, status=None):
    session = get_session()
    with session.begin():
        query = base_query = model_query(models.Task).filter_by(uuid=uuid)
        if status is not None:
            query = base_query.filter_by(status=status)

        (model_query(models.WorkloadData).filter_by(task_uuid=uuid).
         delete(synchronize_session=False))

        (model_query(models.Workload).filter_by(task_uuid=uuid).
         delete(synchronize_session=False))

        (model_query(models.Subtask).filter_by(task_uuid=uuid).
         delete(synchronize_session=False))

        (model_query(models.Tag).filter_by(
            uuid=uuid, type=consts.TagType.TASK).
         delete(synchronize_session=False))

        count = query.delete(synchronize_session=False)
        if not count:
            if status is not None:
                task = base_query.first()
                if task:
                    raise exceptions.DBConflict(
                        "Task `%(uuid)s` in `%(actual)s` status but "
                        "`%(require)s` is required."
                        % {"uuid": uuid,
                           "require": status, "actual": task.status})

            raise exceptions.DBRecordNotFound(
                criteria="uuid: %s" % uuid, table="tasks")


def _subtasks_get_all_by_task_uuid(task_uuid, session=None):
    result = model_query(models.Subtask, session=session).filter_by(
        task_uuid=task_uuid).all()
    subtasks = []
    for subtask in result:
        subtask = serialize_data(subtask)
        subtask["workloads"] = []
        workloads = (model_query(models.Workload, session=session).
                     filter_by(subtask_uuid=subtask["uuid"]).all())
        for workload in workloads:
            workload.data = _task_workload_data_get_all(workload.uuid)
            subtask["workloads"].append(serialize_data(workload))
        subtasks.append(subtask)
    return subtasks


@serialize
def subtask_create(task_uuid, title, description=None, contexts=None):
    subtask = models.Subtask(task_uuid=task_uuid)
    subtask.update({
        "title": title,
        "description": description or "",
        "contexts": contexts or {},
    })
    subtask.save(get_session())
    return subtask


@serialize
def subtask_update(subtask_uuid, values):
    subtask = model_query(models.Subtask).filter_by(uuid=subtask_uuid).first()
    subtask.update(values)
    subtask.save(get_session())
    return subtask


@serialize
def workload_get(workload_uuid):
    return model_query(models.Workload).filter_by(uuid=workload_uuid).first()


@serialize
def workload_create(task_uuid, subtask_uuid, name, description, position,
                    runner, runner_type, hooks, contexts, sla, args):
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
    workload.save(get_session())
    return workload


@serialize
def workload_data_create(task_uuid, workload_uuid, chunk_order, data):
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
    workload_data.save(get_session())
    return workload_data


@serialize
def workload_set_results(workload_uuid, subtask_uuid, task_uuid,
                         load_duration, full_duration, start_time,
                         sla_results, contexts_results, hooks_results=None):
    session = get_session()
    with session.begin():
        workload_results = _task_workload_data_get_all(workload_uuid)

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


@serialize
def env_get(uuid_or_name):
    env = (model_query(models.Env)
           .filter(sa.or_(models.Env.uuid == uuid_or_name,
                          models.Env.name == uuid_or_name))
           .first())
    if not env:
        raise exceptions.DBRecordNotFound(
            criteria="uuid or name is %s" % uuid_or_name, table="envs")
    return env


@serialize
def env_get_status(uuid):
    resp = (model_query(models.Env)
            .filter_by(uuid=uuid)
            .options(sa.orm.load_only("status"))
            .first())
    if not resp:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % uuid, table="envs")
    return resp["status"]


@serialize
def env_list(status=None):
    query = model_query(models.Env)
    if status:
        query = query.filter_by(status=status)
    return query.all()


@serialize
def env_create(name, status, description, extras, config, spec, platforms):
    try:
        env_uuid = models.UUID()
        for p in platforms:
            p["env_uuid"] = env_uuid

        env = models.Env(
            name=name, uuid=env_uuid,
            status=status, description=description,
            extras=extras, config=config, spec=spec
        )
        get_session().bulk_save_objects([env] + [
            models.Platform(**p) for p in platforms
        ])
    except db_exc.DBDuplicateEntry:
        raise exceptions.DBRecordExists(
            field="name", value=name, table="envs")

    return env_get(env_uuid)


def env_rename(uuid, old_name, new_name):
    try:
        return bool(model_query(models.Env)
                    .filter_by(uuid=uuid, name=old_name)
                    .update({"name": new_name}))
    except db_exc.DBDuplicateEntry:
        raise exceptions.DBRecordExists(
            field="name", value=new_name, table="envs")


def env_update(uuid, description=None, extras=None, config=None):
    values = {}
    if description is not None:
        values["description"] = description
    if extras is not None:
        values["extras"] = extras
    if config is not None:
        values["config"] = config

    if not values:
        return True

    return bool(model_query(models.Env)
                .filter_by(uuid=uuid)
                .update(values))


def env_set_status(uuid, old_status, new_status):
    count = (model_query(models.Env)
             .filter_by(uuid=uuid, status=old_status)
             .update({"status": new_status}))
    if count:
        return True
    raise exceptions.DBConflict("Env %s should be in status %s actual %s"
                                % (uuid, old_status, env_get_status(uuid)))


def env_delete_cascade(uuid):
    session = get_session()
    with session.begin():
        (model_query(models.Task, session=session)
         .filter_by(env_uuid=uuid)
         .delete())
        (model_query(models.Verification, session=session)
         .filter_by(env_uuid=uuid)
         .delete())
        (model_query(models.Platform, session=session)
         .filter_by(env_uuid=uuid)
         .delete())
        (model_query(models.Env, session=session)
         .filter_by(uuid=uuid)
         .delete())


@serialize
def platforms_list(env_uuid):
    return model_query(models.Platform).filter_by(env_uuid=env_uuid).all()


@serialize
def platform_get(uuid):
    p = model_query(models.Platform).filter_by(uuid=uuid).first()
    if not p:
        raise exceptions.DBRecordNotFound(
            criteria="uuid = %s" % uuid, table="platforms")
    return p


def platform_set_status(uuid, old_status, new_status):
    count = (model_query(models.Platform)
             .filter_by(uuid=uuid, status=old_status)
             .update({"status": new_status}))
    if count:
        return True

    platform = platform_get(uuid)
    raise exceptions.DBConflict(
        "Platform %s should be in status %s actual %s"
        % (uuid, old_status, platform["status"]))


def platform_set_data(uuid, platform_data=None, plugin_data=None):
    values = {}
    if platform_data is not None:
        values["platform_data"] = platform_data
    if plugin_data is not None:
        values["plugin_data"] = plugin_data

    if not values:
        return True

    return bool(model_query(models.Platform)
                .filter_by(uuid=uuid)
                .update(values))


@serialize
def verifier_create(name, vtype, platform, source, version,
                    system_wide, extra_settings=None):
    verifier = models.Verifier(name=name, type=vtype, platform=platform,
                               source=source, extra_settings=extra_settings,
                               version=version, system_wide=system_wide)
    verifier.save(get_session())
    return verifier


@serialize
def verifier_get(verifier_id):
    return _verifier_get(verifier_id)


def _verifier_get(verifier_id, session=None):
    verifier = model_query(
        models.Verifier, session=session).filter(
            sa.or_(models.Verifier.name == verifier_id,
                   models.Verifier.uuid == verifier_id)).first()
    if not verifier:
        raise exceptions.DBRecordNotFound(
            criteria="name or uuid is %s" % verifier_id, table="verifiers")
    return verifier


@serialize
def verifier_list(status=None):
    query = model_query(models.Verifier)
    if status:
        query = query.filter_by(status=status)
    return query.all()


def verifier_delete(verifier_id):
    count = (model_query(models.Verifier)
             .filter(sa.or_(models.Verifier.name == verifier_id,
                            models.Verifier.uuid == verifier_id))
             .delete(synchronize_session=False))
    if not count:
        raise exceptions.DBRecordNotFound(
            criteria="name or uuid is %s" % verifier_id, table="verifiers")


@serialize
def verifier_update(verifier_id, **properties):
    session = get_session()
    with session.begin():
        verifier = _verifier_get(verifier_id, session=session)
        verifier.update(properties)
        verifier.save(session)
    return verifier


@serialize
def verification_create(verifier_id, env, tags=None, run_args=None):
    verifier = _verifier_get(verifier_id)
    env = env_get(env)
    verification = models.Verification()
    verification.update({"verifier_uuid": verifier.uuid,
                         "env_uuid": env["uuid"],
                         "run_args": run_args})
    verification.save(get_session())

    if tags:
        get_session().bulk_save_objects(
            models.Tag(uuid=verification.uuid, tag=t,
                       type=consts.TagType.VERIFICATION)
            for t in set(tags)
        )
    return verification


@serialize
def verification_get(verification_uuid):
    verification = _verification_get(verification_uuid)
    verification.tags = sorted(_tags_get(verification.uuid,
                                         consts.TagType.VERIFICATION))
    return verification


def _verification_get(verification_uuid, session=None):
    verification = model_query(
        models.Verification, session=session).filter_by(
        uuid=verification_uuid).first()
    if not verification:
        raise exceptions.DBRecordNotFound(
            criteria="uuid: %s" % verification_uuid, table="verifications")
    return verification


@serialize
def verification_list(verifier_id=None, env=None, tags=None, status=None):
    session = get_session()
    with session.begin():
        filter_by = {}
        if verifier_id:
            verifier = _verifier_get(verifier_id, session=session)
            filter_by["verifier_uuid"] = verifier.uuid
        if env:
            env = env_get(env)
            filter_by["env_uuid"] = env["uuid"]
        if status:
            filter_by["status"] = status

        query = model_query(models.Verification, session=session)
        if filter_by:
            query = query.filter_by(**filter_by)

        def add_tags_to_verifications(verifications):
            for verification in verifications:
                verification.tags = sorted(_tags_get(
                    verification.uuid, consts.TagType.VERIFICATION))
            return verifications

        if tags:
            uuids = _uuids_by_tags_get(consts.TagType.VERIFICATION, tags)
            query = query.filter(models.Verification.uuid.in_(uuids))

    return add_tags_to_verifications(query.all())


def verification_delete(uuid):
    count = model_query(models.Verification).filter_by(uuid=uuid).delete()
    if not count:
        raise exceptions.DBRecordNotFound(criteria="uuid: %s" % uuid,
                                          table="verifications")


@serialize
def verification_update(verification_uuid, **properties):
    verification = _verification_get(verification_uuid)
    verification.update(properties)
    verification.save(get_session())
    return verification
