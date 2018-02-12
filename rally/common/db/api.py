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

from oslo_db import api as db_api
from oslo_db import options as db_options

from rally.common import cfg

CONF = cfg.CONF


db_options.set_defaults(CONF, connection="sqlite:////tmp/rally.sqlite")


IMPL = None


def get_impl():
    global IMPL

    if not IMPL:
        _BACKEND_MAPPING = {"sqlalchemy": "rally.common.db.sqlalchemy.api"}
        IMPL = db_api.DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING)

    return IMPL


def engine_reset():
    """Reset DB engine."""
    get_impl().engine_reset()


def schema_cleanup():
    """Drop DB schema. This method drops existing database."""
    get_impl().schema_cleanup()


def schema_upgrade(revision=None):
    """Migrate the database to `revision` or the most recent revision."""
    return get_impl().schema_upgrade(revision)


def schema_create():
    """Create database schema from models description."""
    return get_impl().schema_create()


def schema_revision(detailed=False):
    """Return the schema revision."""
    return get_impl().schema_revision(detailed=detailed)


def schema_stamp(revision):
    """Stamps database with provided revision."""
    return get_impl().schema_stamp(revision)


def task_get(uuid, detailed=False):
    """Returns task by uuid.

    :param uuid: UUID of the task.
    :param detailed: whether return results of task or not (Defaults to False).
    :raises DBRecordNotFound: if the task does not exist.
    :returns: task dict with data on the task.
    """
    return get_impl().task_get(uuid, detailed=detailed)


def task_get_status(uuid):
    """Returns task by uuid.

    :param uuid: UUID of the task.
    :raises DBRecordNotFound: if the task does not exist.
    :returns: task dict with data on the task.
    """
    return get_impl().task_get_status(uuid)


def task_create(values):
    """Create task record in DB.

    :param values: dict with record values.
    :returns: task dict with data on the task.
    """
    return get_impl().task_create(values)


def task_update(uuid, values):
    """Update task by values.

    :param uuid: UUID of the task.
    :param values: dict with record values.
    :raises DBRecordNotFound: if task is not found.
    :returns: new updated task dict with data on the task.
    """
    return get_impl().task_update(uuid, values)


def task_update_status(task_uuid, status, allowed_statuses):
    """Update task status with specified value.

    :param task_uuid: string with UUID of Task instance.
    :param status: new value to be written into db instead of status.
    :param allowed_statuses: list of expected statuses to update in db.
    :raises DBConflict: if task is in improper status.
    :raises DBRecordNotFound: if task is not found.
    :returns: the count of rows match as returned by the database's
              "row count" feature
    """
    return get_impl().task_update_status(task_uuid, allowed_statuses,
                                         status)


def task_list(status=None, env=None, tags=None):
    """Get a list of tasks.

    :param status: Task status to filter the returned list on. If set to
        None, all the tasks will be returned.
    :param env: Environment UUID to filter the returned list on.
        If set to None, tasks from all environments will be returned.
    :param tags: A list of tags to filter tasks by.
    :returns: A list of dicts with data on the tasks.
    """
    return get_impl().task_list(status=status,
                                env=env,
                                tags=tags)


def task_delete(uuid, status=None):
    """Delete a task.

    This method removes the task by the uuid, but if the status
    argument is specified, then the task is removed only when these
    statuses are equal otherwise an exception is raised.

    :param uuid: UUID of the task.
    :raises DBRecordNotFound: if the task does not exist.
    :raises DBConflict: if the status of the task does not
                        equal to the status argument.
    """
    return get_impl().task_delete(uuid, status=status)


def subtask_create(task_uuid, title, description=None, contexts=None):
    """Create a subtask.

    :param task_uuid: string with UUID of Task instance.
    :param title: Subtask title.
    :param description: string with the description of Subtask
    :param contexts: a dict with config of Workload contexts
    :returns: a dict with data on the subtask.
    """
    return get_impl().subtask_create(task_uuid, title, description, contexts)


def subtask_update(subtask_uuid, values):
    """Update a subtask.

    :param subtask_uuid: string with UUID of Subtask instance.
    :param values: dict with record values.
    :returns: a dict with data on the subtask.
    """
    return get_impl().subtask_update(subtask_uuid, values)


def workload_create(task_uuid, subtask_uuid, name, description, position,
                    runner, runner_type, hooks, contexts, sla, args):
    """Create a workload.

    :param task_uuid: string with UUID of Task instance.
    :param subtask_uuid: string with UUID of Subtask instance.
    :param name: string with the name of Workload
    :param description: string with the description of Workload
    :param position: integer with an order of Workload in Subtask
    :param runner: a dict with config of Workload runner
    :param runner_type: a type of Workload runner
    :param hooks: a list with Workload hooks config and results
    :param contexts: a dict with config of Workload contexts
    :param sla: a dict with config of Workload sla
    :param args: a dict with arguments of Workload
    :returns: a dict with data on the workload.
    """
    return get_impl().workload_create(
        task_uuid, subtask_uuid, name=name, description=description,
        position=position, runner=runner, runner_type=runner_type,
        hooks=hooks, contexts=contexts, sla=sla, args=args)


def workload_get(workload_uuid):
    """Get a workload.

    :param workload_uuid: string with UUID of Workload to fetch.
    :returns: a dict with data on the workload.
    """
    return get_impl().workload_get(workload_uuid)


def workload_data_create(task_uuid, workload_uuid, chunk_order, data):
    """Create a workload data.

    :param task_uuid: string with UUID of Task instance.
    :param workload_uuid: string with UUID of Workload instance.
    :param chunk_order: ordinal index of workload data.
    :param data: dict with record values on the workload data.
    :returns: a dict with data on the workload data.
    """
    return get_impl().workload_data_create(task_uuid, workload_uuid,
                                           chunk_order, data)


def workload_set_results(workload_uuid, subtask_uuid, task_uuid, load_duration,
                         full_duration, start_time, sla_results,
                         contexts_results, hooks_results=None):
    """Set workload results.

    :param workload_uuid: string with UUID of Workload instance.
    :param subtask_uuid: string with UUID of Workload's parent Subtask.
    :param task_uuid: string with UUID of Workload's parent Task.
    :param load_duration: float value of Workload's load duration
    :param full_duration: float value of Workload's full duration (
        generating load, executing contexts and etc)
    :param start_time: a timestamp of load start
    :param sla_results: a list with Workload's SLA results
    :param contexts_results: a list with Contexts execution results
    :param hooks_results: a list with Workload's Hooks results
    :returns: a dict with data on the workload.
    """
    return get_impl().workload_set_results(
        workload_uuid=workload_uuid,
        subtask_uuid=subtask_uuid,
        task_uuid=task_uuid,
        load_duration=load_duration,
        full_duration=full_duration,
        start_time=start_time,
        sla_results=sla_results,
        hooks_results=hooks_results,
        contexts_results=contexts_results)


def env_get(uuid_or_name):
    """Returns envs with corresponding uuid or name."""
    return get_impl().env_get(uuid_or_name)


def env_get_status(uuid):
    """Returns status of env with corresponding uuid."""
    return get_impl().env_get_status(uuid)


def env_list(status=None):
    """Return list of envs, filtered by status, if status provided."""
    return get_impl().env_list(status=status)


def env_create(name, status, description, extras, config, spec, platforms):
    """Created db record of env and platforms."""
    return get_impl().env_create(
        name, status, description, extras, config, spec, platforms)


def env_rename(uuid, old_name, new_name):
    """Renames env. Returns op result as bool"""
    return get_impl().env_rename(uuid, old_name, new_name)


def env_update(uuid, description=None, extras=None, config=None):
    """Update description and extra of envs. Returns op result as bool."""
    return get_impl().env_update(
        uuid, description=description, extras=extras, config=config)


def env_set_status(uuid, old_status, new_status):
    """Set new env status. """
    return get_impl().env_set_status(uuid, old_status, new_status)


def env_delete_cascade(uuid):
    """Delete envs, platforms and all related to env resources."""
    return get_impl().env_delete_cascade(uuid)


def platforms_list(env_uuid):
    """List platforms related to some env."""
    return get_impl().platforms_list(env_uuid)


def platform_get(uuid):
    """Returns platforms with corresponding uuid."""
    return get_impl().platform_get(uuid)


def platform_set_status(uuid, old_status, new_status):
    """Set's new status to platform"""
    return get_impl().platform_set_status(uuid, old_status, new_status)


def platform_set_data(uuid, platform_data=None, plugin_data=None):
    """Set's platform data."""
    return get_impl().platform_set_data(uuid, platform_data, plugin_data)


def verifier_create(name, vtype, platform, source, version, system_wide,
                    extra_settings=None):
    """Create a verifier record.

    :param name: verifier name
    :param vtype: verifier plugin name
    :param platform: verifier plugin platform
    :param source: path or URL to a verifier repo
    :param version: branch, tag or commit ID of a verifier repo
    :param system_wide: whether or not to use the system-wide environment
    :param extra: verifier-specific installation options
    :returns: a dict with verifier data
    """
    return get_impl().verifier_create(name=name, vtype=vtype,
                                      platform=platform, source=source,
                                      version=version, system_wide=system_wide,
                                      extra_settings=extra_settings)


def verifier_get(verifier_id):
    """Get a verifier record.

    :param verifier_id: verifier name or UUID
    :raises DBRecordNotFound: if verifier does not exist
    :returns: a dict with verifier data
    """
    return get_impl().verifier_get(verifier_id)


def verifier_list(status=None):
    """Get all verifier records.

    :param status: status to filter verifiers by
    :returns: a list of dicts with verifiers data
    """
    return get_impl().verifier_list(status)


def verifier_delete(verifier_id):
    """Delete a verifier record.

    :param verifier_id: verifier name or UUID
    :raises DBRecordNotFound: if verifier does not exist
    """
    get_impl().verifier_delete(verifier_id)


def verifier_update(verifier_id, **properties):
    """Update a verifier record.

    :param verifier_id: verifier name or UUID
    :param properties: a dict with new properties to update verifier record
    :raises DBRecordNotFound: if verifier does not exist
    :returns: the updated dict with verifier data
    """
    return get_impl().verifier_update(verifier_id, properties)


def verification_create(verifier_uuid, env, tags=None, run_args=None):
    """Create a verification record.

    :param verifier_uuid: verification UUID
    :param env: Environment UUID
    :param tags: a list of tags to assign them to verification
    :param run_args: a dict with run arguments for verification
    :returns: a dict with verification data
    """
    return get_impl().verification_create(verifier_uuid,
                                          env=env,
                                          tags=tags,
                                          run_args=run_args)


def verification_get(verification_uuid):
    """Get a verification record.

    :param verification_uuid: verification UUID
    :raises DBRecordNotFound: if verification does not exist
    :returns: a dict with verification data
    """
    return get_impl().verification_get(verification_uuid)


def verification_list(verifier_id=None, env=None, tags=None,
                      status=None):
    """List all verification records.

    :param verifier_id: verifier name or UUID to filter verifications by
    :param env: Environment name or UUID to filter verifications by
    :param tags: tags to filter verifications by
    :param status: status to filter verifications by
    :returns: a list of dicts with verifications data
    """
    return get_impl().verification_list(verifier_id,
                                        env=env,
                                        tags=tags,
                                        status=status)


def verification_delete(verification_uuid):
    """Delete a verification record.

    :param verification_uuid: verification UUID
    :raises DBRecordNotFound: if verification does not exist
    """
    return get_impl().verification_delete(verification_uuid)


def verification_update(uuid, **properties):
    """Update a verification record.

    :param uuid: verification UUID
    :param properties: a dict with new properties to update verification record
    :raises DBRecordNotFound: if verification does not exist
    :returns: the updated dict with verification data
    """
    return get_impl().verification_update(uuid, properties)
