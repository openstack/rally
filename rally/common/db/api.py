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

from oslo_config import cfg
from oslo_db import api as db_api
from oslo_db import options as db_options
import six

from rally.common.i18n import _


CONF = cfg.CONF


db_options.set_defaults(CONF, connection="sqlite:////tmp/rally.sqlite")


IMPL = None


def serialize(fn):
    def conv(data):
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
            return {k: conv(v) for k, v in six.iteritems(data)}
        if isinstance(data, (list, tuple)):
            return [conv(i) for i in data]
        if hasattr(data, "_as_dict"):
            result = data._as_dict()
            for k, v in six.iteritems(result):
                result[k] = conv(v)
            return result

        raise ValueError(_("Can not serialize %s") % data)

    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        return conv(result)
    return wrapper


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


def schema_revision():
    """Return the schema revision."""
    return get_impl().schema_revision()


def schema_stamp(revision):
    """Stamps database with provided revision."""
    return get_impl().schema_stamp(revision)


def task_get(uuid):
    """Returns task by uuid.

    :param uuid: UUID of the task.
    :raises TaskNotFound: if the task does not exist.
    :returns: task dict with data on the task.
    """
    return get_impl().task_get(uuid)


def task_get_status(uuid):
    """Returns task by uuid.

    :param uuid: UUID of the task.
    :raises TaskNotFound: if the task does not exist.
    :returns: task dict with data on the task.
    """
    return get_impl().task_get_status(uuid)


def task_get_detailed_last():
    """Returns the most recently created task."""
    return get_impl().task_get_detailed_last()


def task_get_detailed(uuid):
    """Returns task with results by uuid.

    :param uuid: UUID of the task.
    :returns: task dict with data on the task and its results.
    """
    return get_impl().task_get_detailed(uuid)


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
    :raises TaskNotFound: if the task does not exist.
    :returns: new updated task dict with data on the task.
    """
    return get_impl().task_update(uuid, values)


def task_update_status(task_uuid, status, allowed_statuses):
    """Update task status with specified value.

    :param task_uuid: string with UUID of Task instance.
    :param status: new value to wrote into db instead of status.
    :param allowed_statuses: list of expected statuses to update in db.
    :raises RallyException: if task not found with specified status.
    :returns: the count of rows match as returned by the database's
              "row count" feature
    """
    return get_impl().task_update_status(task_uuid, allowed_statuses,
                                         status)


def task_list(status=None, deployment=None):
    """Get a list of tasks.

    :param status: Task status to filter the returned list on. If set to
                   None, all the tasks will be returned.
    :param deployment: deployment UUID to filter the returned list on.
                      if set to None tasks from all deployments well be
                      returned.
    :returns: A list of dicts with data on the tasks.
    """
    return get_impl().task_list(status=status, deployment=deployment)


def task_delete(uuid, status=None):
    """Delete a task.

    This method removes the task by the uuid, but if the status
    argument is specified, then the task is removed only when these
    statuses are equal otherwise an exception is raised.

    :param uuid: UUID of the task.
    :raises TaskNotFound: if the task does not exist.
    :raises TaskInvalidStatus: if the status of the task does not
                               equal to the status argument.
    """
    return get_impl().task_delete(uuid, status=status)


def task_result_get_all_by_uuid(task_uuid):
    """Get list of task results.

    :param task_uuid: string with UUID of Task instance.
    :returns: list instances of TaskResult.
    """
    return get_impl().task_result_get_all_by_uuid(task_uuid)


def task_result_create(task_uuid, key, data):
    """Append result record to task.

    :param task_uuid: string with UUID of Task instance.
    :param key: key expected to update in task result.
    :param data: data expected to update in task result.
    :returns: TaskResult instance appended.
    """
    return get_impl().task_result_create(task_uuid, key, data)


def deployment_create(values):
    """Create a deployment from the values dictionary.

    :param values: dict with record values on the deployment.
    :returns: a dict with data on the deployment.
    """
    return get_impl().deployment_create(values)


def deployment_delete(uuid):
    """Delete a deployment by UUID.

    :param uuid: UUID of the deployment.
    :raises DeploymentNotFound: if the deployment does not exist.
    :raises DeploymentIsBusy: if the resource is not enough.
    """
    return get_impl().deployment_delete(uuid)


def deployment_get(deployment):
    """Get a deployment by UUID.

    :param deployment: UUID or name of the deployment.
    :raises DeploymentNotFound: if the deployment does not exist.
    :returns: a dict with data on the deployment.
    """
    return get_impl().deployment_get(deployment)


def deployment_update(uuid, values):
    """Update a deployment by values.

    :param uuid: UUID of the deployment.
    :param values: dict with items to update.
    :raises DeploymentNotFound: if the deployment does not exist.
    :returns: a dict with data on the deployment.
    """
    return get_impl().deployment_update(uuid, values)


def deployment_list(status=None, parent_uuid=None, name=None):
    """Get list of deployments.

    :param status: if None returns any deployments with any status.
    :param parent_uuid: filter by parent. If None, return only "root"
                        deployments.
    :param name: Name of deployment
    :returns: a list of dicts with data on the deployments.
    """
    return get_impl().deployment_list(status=status, parent_uuid=parent_uuid,
                                      name=name)


def resource_create(values):
    """Create a resource from the values dictionary.

    :param values: a dict with data on the resource.
    :returns: a dict with updated data on the resource.
    """
    return get_impl().resource_create(values)


def resource_get_all(deployment_uuid, provider_name=None, type=None):
    """Return resources of a deployment.

    :param deployment_uuid: filter by uuid of a deployment
    :param provider_name: filter by provider_name, if is None, then
                          return all providers
    :param type: filter by type, if is None, then return all types
    :returns: a list of dicts with data on a resource
    """
    return get_impl().resource_get_all(deployment_uuid,
                                       provider_name=provider_name,
                                       type=type)


def resource_delete(id):
    """Delete a resource.

    :param id: ID of a resource.
    :raises ResourceNotFound: if the resource does not exist.
    """
    return get_impl().resource_delete(id)


def verification_create(deployment_uuid):
    """Create Verification record in DB.

    :param deployment_uuid: UUID of the deployment.
    :returns: a dict with verification data.
    """
    return get_impl().verification_create(deployment_uuid)


def verification_get(verification_uuid):
    """Returns verification by UUID.

    :param verification_uuid: UUID of the verification.
    :raises NotFoundException: if verification does not exist.
    :returns: a dict with verification data.
    """
    return get_impl().verification_get(verification_uuid)


def verification_delete(verification_uuid):
    """Delete verification.

    :param verification_uuid: UUID of the verification.
    :raises NotFoundException: if verification does not exist.
    """
    return get_impl().verification_delete(verification_uuid)


def verification_update(uuid, values):
    """Update verification by values.

    :param uuid: UUID of the verification.
    :param values: dict with record values.
    :raises NotFoundException: if verification does not exist.
    :returns: new updated task dict with data on the task.
    """
    return get_impl().verification_update(uuid, values)


def verification_list(status=None):
    """Get a list of verifications.

    :param status: Verification status to filter the returned list on.
    :returns: A list of dicts with data on the verifications.
    """
    return get_impl().verification_list(status=status)


def verification_result_get(verification_uuid):
    """Get dict of verification results.

    :param verification_uuid: string with UUID of Verification instance.
    :returns: dict instance of VerificationResult.
    """
    return get_impl().verification_result_get(verification_uuid)


def verification_result_create(verification_uuid, values):
    """Append result record to verification.

    :param verification_uuid: string with UUID of Verification instance.
    :param values: dict with record values.
    :returns: TaskResult instance appended.
    """
    return get_impl().verification_result_create(verification_uuid, values)


def register_worker(values):
    """Register a new worker service at the specified hostname.

    :param values: A dict of values which must contain the following:
                   {
                    "hostname": the unique hostname which identifies
                                this worker service.
                   }
    :returns: A worker.
    :raises WorkerAlreadyRegistered: if worker already registered
    """
    return get_impl().register_worker(values)


def get_worker(hostname):
    """Retrieve a worker service record from the database.

    :param hostname: The hostname of the worker service.
    :returns: A worker.
    :raises WorkerNotFound: if worker not found
    """
    return get_impl().get_worker(hostname)


def unregister_worker(hostname):
    """Unregister this worker with the service registry.

    :param hostname: The hostname of the worker service.
    :raises WorkerNotFound: if worker not found
    """
    get_impl().unregister_worker(hostname)


def update_worker(hostname):
    """Mark a worker as active by updating its "updated_at" property.

    :param hostname: The hostname of this worker service.
    :raises WorkerNotFound: if worker not found
    """
    get_impl().update_worker(hostname)
