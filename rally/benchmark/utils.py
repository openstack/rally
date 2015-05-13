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

import itertools
import time
import traceback

from novaclient import exceptions as nova_exc
import six

from rally.common.i18n import _
from rally.common import log as logging
from rally import exceptions


LOG = logging.getLogger(__name__)


def get_status(resource):
    # workaround for heat resources - using stack_status instead of status
    if ((hasattr(resource, "stack_status") and
         isinstance(resource.stack_status, six.string_types))):
        return resource.stack_status.upper()
    # workaround for ceilometer alarms - using state instead of status
    if ((hasattr(resource, "state") and
         isinstance(resource.state, six.string_types))):
        return resource.state.upper()
    return getattr(resource, "status", "NONE").upper()


class resource_is(object):
    def __init__(self, desired_status, status_getter=None):
        self.desired_status = desired_status
        self.status_getter = status_getter or get_status

    def __call__(self, resource):
        return self.status_getter(resource) == self.desired_status.upper()

    def __str__(self):
        return str(self.desired_status)


def get_from_manager(error_statuses=None):
    error_statuses = error_statuses or ["ERROR"]
    error_statuses = map(lambda str: str.upper(), error_statuses)

    def _get_from_manager(resource):
        # catch client side errors
        try:
            res = resource.manager.get(resource.id)
        except Exception as e:
            if getattr(e, "code", getattr(e, "http_status", 400)) == 404:
                raise exceptions.GetResourceNotFound(resource=resource)
            raise exceptions.GetResourceFailure(resource=resource, err=e)

        # catch abnormal status, such as "no valid host" for servers
        status = get_status(res)

        if status in ("DELETED", "DELETE_COMPLETE"):
            raise exceptions.GetResourceNotFound(resource=res)
        if status in error_statuses:
            raise exceptions.GetResourceErrorStatus(resource=res,
                                                    status=status, fault="")

        return res

    return _get_from_manager


def manager_list_size(sizes):
    def _list(mgr):
        return len(mgr.list()) in sizes
    return _list


def wait_for(resource, is_ready, update_resource=None, timeout=60,
             check_interval=1):
    """Waits for the given resource to come into the desired state.

    Uses the readiness check function passed as a parameter and (optionally)
    a function that updates the resource being waited for.

    :param is_ready: A predicate that should take the resource object and
                     return True iff it is ready to be returned
    :param update_resource: Function that should take the resource object
                          and return an 'updated' resource. If set to
                          None, no result updating is performed
    :param timeout: Timeout in seconds after which a TimeoutException will be
                    raised
    :param check_interval: Interval in seconds between the two consecutive
                           readiness checks

    :returns: The "ready" resource object
    """

    start = time.time()
    while True:
        # NOTE(boden): mitigate 1st iteration waits by updating immediately
        if update_resource:
            resource = update_resource(resource)
        if is_ready(resource):
            break
        time.sleep(check_interval)
        if time.time() - start > timeout:
            raise exceptions.TimeoutException(
                desired_status=str(is_ready),
                resource_name=getattr(resource, "name", repr(resource)),
                resource_type=resource.__class__.__name__,
                resource_id=getattr(resource, "id", "<no id>"),
                resource_status=get_status(resource))

    return resource


def wait_for_delete(resource, update_resource=None, timeout=60,
                    check_interval=1):
    """Wait for the full deletion of resource.

    :param update_resource: Function that should take the resource object
                            and return an 'updated' resource, or raise
                            exception rally.exceptions.GetResourceNotFound
                            that means that resource is deleted.

    :param timeout: Timeout in seconds after which a TimeoutException will be
                    raised
    :param check_interval: Interval in seconds between the two consecutive
                           readiness checks
    """
    start = time.time()
    while True:
        try:
            resource = update_resource(resource)
        except exceptions.GetResourceNotFound:
            break
        time.sleep(check_interval)
        if time.time() - start > timeout:
            raise exceptions.TimeoutException(
                desired_status="deleted",
                resource_name=getattr(resource, "name", repr(resource)),
                resource_type=resource.__class__.__name__,
                resource_id=getattr(resource, "id", "<no id>"),
                resource_status=get_status(resource))


def format_exc(exc):
    return [exc.__class__.__name__, str(exc), traceback.format_exc()]


def infinite_run_args_generator(args_func):
    for i in itertools.count():
        yield args_func(i)


def check_service_status(client, service_name):
    """Check if given openstack service is enabled and state is up."""
    try:
        for service in client.services.list():
            if service_name in str(service):
                if service.status == "enabled" and service.state == "up":
                    return True
    except nova_exc.NotFound:
        LOG.warning(_("Unable to retrieve a list of available services from "
                      "nova. Pre-Grizzly OpenStack deployment?"))
        return False
    return False
