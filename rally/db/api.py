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

Functions in this module are imported into the rally.db namespace. Call these
functions from rally.db namespace, not the rally.db.api namespace.

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

from rally.openstack.common.db import api as db_api


_BACKEND_MAPPING = {'sqlalchemy': 'rally.db.sqlalchemy.api'}

IMPL = db_api.DBAPI(backend_mapping=_BACKEND_MAPPING)


def db_cleanup():
    """Recreate engine."""
    IMPL.db_cleanup()


def db_create():
    """Initialize DB. This method will drop existing database."""
    IMPL.db_create()


def db_drop():
    """Drop DB. This method drop existing database."""
    IMPL.db_drop()


def task_get_by_uuid(uuid):
    """Returns task by uuid."""
    return IMPL.task_get_by_uuid(uuid)


def task_get_detailed(uuid):
    """Returns task with results by uuid."""
    return IMPL.task_get_detailed(uuid)


def task_create(values):
    """Create task record in DB.

    :param values: dict with record values
    Returns task UUID.
    """
    return IMPL.task_create(values)


def task_update(uuid, values):
    """Update task by values.

    Returns new updated task dict
    """
    return IMPL.task_update(uuid, values)


def task_list(status=None):
    """Get a list of tasks.

    :param status: Task status to filter the returned list on. If set to
                   None, all the tasks will be returned.

    :returns: A list of dicts with data on the tasks.
    """
    return IMPL.task_list(status=status)


def task_delete(uuid, status=None):
    """Delete a task.

    This method removes the task by the uuid, but if the status
    argument is specified, then the task is removed only when these
    statuses are equal otherwise an exception is raised.

    :param uuid: UUID of the task.
    :raises: :class:`rally.exceptions.Task` if the task does not exist.
    :raises: :class:`rally.exceptions.TaskInvalidStatus` if the status
             of the task does not equal to the status argument.
    """
    return IMPL.task_delete(uuid, status=status)


def task_result_get_all_by_uuid(task_uuid):
    """Get list of task results.

    :param task_uuid: string with UUID of Task instance
    :returns: list instances of TaskResult
    """
    return IMPL.task_result_get_all_by_uuid(task_uuid)


def task_result_create(task_uuid, key, data):
    """Append result record to task."""
    return IMPL.task_result_create(task_uuid, key, data)
