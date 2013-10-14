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


def task_list(status=None, active=True):
    """Get list of tasks.
    :param status: if None returns any task with any status.
    :param active: if None returns all tasks,
                   if True returns only active task,
                   if False returns only completed tasks.
    Retruns list of dicts with tasks data.
    """
    return IMPL.task_list(status, active)


def task_delete(uuid):
    """Mark task with correspondig uuid as deleted."""
    return IMPL.task_delete(uuid)


def task_result_create(task_uuid, key, data):
    """Append result record to task."""
    return IMPL.task_result_create(task_uuid, key, data)
