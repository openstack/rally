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

import jsonschema
from novaclient import exceptions as nova_exc
import six

from rally.common.i18n import _
from rally.common import logging
from rally import consts
from rally import exceptions


LOG = logging.getLogger(__name__)


def get_status(resource, status_attr="status"):
    """Get the status of a given resource object.

    The status is returned in upper case. The status is checked for the
    standard field names with special cases for Heat and Ceilometer.

    :param resource: The resource object or dict.
    :param status_attr: Allows to specify non-standard status fields.
    :return: The status or "NONE" if it is not available.
    """

    for s_attr in ["stack_status", "state", status_attr]:
        status = getattr(resource, s_attr, None)
        if isinstance(status, six.string_types):
            return status.upper()

    # Dict case
    if ((isinstance(resource, dict) and status_attr in resource.keys() and
         isinstance(resource[status_attr], six.string_types))):
        return resource[status_attr].upper()

    return "NONE"


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

    def _get_from_manager(resource, id_attr="id"):
        # catch client side errors
        try:
            res = resource.manager.get(getattr(resource, id_attr))
        except Exception as e:
            if getattr(e, "code", getattr(e, "http_status", 400)) == 404:
                raise exceptions.GetResourceNotFound(resource=resource)
            raise exceptions.GetResourceFailure(resource=resource, err=e)

        # catch abnormal status, such as "no valid host" for servers
        status = get_status(res)

        if status in ("DELETED", "DELETE_COMPLETE"):
            raise exceptions.GetResourceNotFound(resource=res)
        if status in error_statuses:
            raise exceptions.GetResourceErrorStatus(
                resource=res, status=status,
                fault=getattr(res, "fault", "n/a"))

        return res

    return _get_from_manager


def manager_list_size(sizes):
    def _list(mgr):
        return len(mgr.list()) in sizes
    return _list


@logging.log_deprecated("Use wait_for_status instead.", "0.1.2", once=True)
def wait_for(resource, is_ready=None, ready_statuses=None,
             failure_statuses=None, status_attr="status", update_resource=None,
             timeout=60, check_interval=1, id_attr="id"):
    """Waits for the given resource to come into the one of the given statuses.

    The method can be used to check resource for status with a `is_ready`
    function or with a list of expected statuses and the status attribute

    In case when the is_ready checker is not provided the resource should have
    status_attr. It may be an object attribute or a dictionary key. The value
    of the attribute is checked against ready statuses list and failure
    statuses. In case of a failure the wait exits with an exception. The
    resource is updated between iterations with an update_resource call.

    :param is_ready: A predicate that should take the resource object and
                     return True iff it is ready to be returned
    :param ready_statuses: List of statuses which mean that the resource is
                         ready
    :param failure_statuses: List of statuses which mean that an error has
                           occurred while waiting for the resource
    :param status_attr: The name of the status attribute of the resource
    :param update_resource: Function that should take the resource object
                          and return an 'updated' resource. If set to
                          None, no result updating is performed
    :param timeout: Timeout in seconds after which a TimeoutException will be
                    raised
    :param check_interval: Interval in seconds between the two consecutive
                           readiness checks

    :returns: The "ready" resource object
    """

    if is_ready is not None:
        return wait_is_ready(resource=resource, is_ready=is_ready,
                             update_resource=update_resource, timeout=timeout,
                             check_interval=check_interval)
    else:
        return wait_for_status(resource=resource,
                               ready_statuses=ready_statuses,
                               failure_statuses=failure_statuses,
                               status_attr=status_attr,
                               update_resource=update_resource,
                               timeout=timeout,
                               check_interval=check_interval,
                               id_attr=id_attr)


@logging.log_deprecated("Use wait_for_status instead.", "0.1.2", once=True)
def wait_is_ready(resource, is_ready, update_resource=None,
                  timeout=60, check_interval=1):

    resource_repr = getattr(resource, "name", repr(resource))
    start = time.time()

    while True:
        if update_resource is not None:
            resource = update_resource(resource)

        if is_ready(resource):
            return resource

        time.sleep(check_interval)
        if time.time() - start > timeout:
            raise exceptions.TimeoutException(
                desired_status=str(is_ready),
                resource_name=resource_repr,
                resource_type=resource.__class__.__name__,
                resource_id=getattr(resource, "id", "<no id>"),
                resource_status=get_status(resource))


def wait_for_status(resource, ready_statuses, failure_statuses=None,
                    status_attr="status", update_resource=None,
                    timeout=60, check_interval=1, check_deletion=False,
                    id_attr="id"):

    resource_repr = getattr(resource, "name", repr(resource))
    if not isinstance(ready_statuses, (set, list, tuple)):
        raise ValueError("Ready statuses should be supplied as set, list or "
                         "tuple")
    if failure_statuses and not isinstance(failure_statuses,
                                           (set, list, tuple)):
        raise ValueError("Failure statuses should be supplied as set, list or "
                         "tuple")

    # make all statuses upper case
    ready_statuses = set(s.upper() for s in ready_statuses or [])
    failure_statuses = set(s.upper() for s in failure_statuses or [])

    if (ready_statuses & failure_statuses):
        raise ValueError(
            "Can't wait for resource's %s status. Ready and Failure"
            "statuses conflict." % resource_repr)
    if not ready_statuses:
        raise ValueError(
            "Can't wait for resource's %s status. No ready "
            "statuses provided" % resource_repr)
    if not update_resource:
        raise ValueError(
            "Can't wait for resource's %s status. No update method."
            % resource_repr)

    start = time.time()

    latest_status = get_status(resource, status_attr)
    latest_status_update = start

    while True:
        try:
            if id_attr == "id":
                resource = update_resource(resource)
            else:
                resource = update_resource(resource, id_attr=id_attr)
        except exceptions.GetResourceNotFound:
            if check_deletion:
                return
            else:
                raise
        status = get_status(resource, status_attr)

        if status != latest_status:
            current_time = time.time()
            delta = current_time - latest_status_update
            LOG.debug(
                "Waiting for resource %(resource)s. Status changed: "
                "%(latest)s => %(current)s in %(delta)s" %
                {"resource": resource_repr, "latest": latest_status,
                 "current": status, "delta": delta})

            latest_status = status
            latest_status_update = current_time

        if status in ready_statuses:
            return resource
        if status in failure_statuses:
            raise exceptions.GetResourceErrorStatus(
                resource=resource,
                status=status,
                fault="Status in failure list %s" % str(failure_statuses))

        time.sleep(check_interval)
        if time.time() - start > timeout:
            raise exceptions.TimeoutException(
                desired_status="('%s')" % "', '".join(ready_statuses),
                resource_name=resource_repr,
                resource_type=resource.__class__.__name__,
                resource_id=getattr(resource, id_attr, "<no id>"),
                resource_status=get_status(resource, status_attr))


@logging.log_deprecated("Use wait_for_status instead.", "0.1.2", once=True)
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


class ActionBuilder(object):
    """Builder class for mapping and creating action objects.

    An action list is an array of single key/value dicts which takes
    the form:

    [{"action": times}, {"action": times}...]

    Here 'action' is a string which indicates an action to perform and
    'times' is a non-zero positive integer which specifies how many
    times to run the action in sequence.

    This utility builder class will build and return methods which
    wrapper the action call the given amount of times.
    """

    SCHEMA_TEMPLATE = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "items": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "minItems": 0
        }
    }

    ITEM_TEMPLATE = {
        "type": "integer",
        "minimum": 0,
        "exclusiveMinimum": True,
        "optional": True
    }

    def __init__(self, action_keywords):
        """Create a new instance of the builder for the given action keywords.

        :param action_keywords: A list of strings which are the keywords this
        instance of the builder supports.
        """
        self._bindings = {}
        self.schema = dict(ActionBuilder.SCHEMA_TEMPLATE)
        for kw in action_keywords:
            self.schema["items"]["properties"][kw] = (
                ActionBuilder.ITEM_TEMPLATE)

    def bind_action(self, action_key, action, *args, **kwargs):
        """Bind an action to an action key.

        Static args/kwargs can be optionally binded.
        :param action_key: The action keyword to bind the action to.
        :param action: A method/function to call for the action.
        :param args: (optional) Static positional args to prepend
        to all invocations of the action.
        :param kwargs: (optional) Static kwargs to prepend to all
        invocations of the action.
        """
        self.validate([{action_key: 1}])
        self._bindings[action_key] = {
            "action": action,
            "args": args or (),
            "kwargs": kwargs or {}
        }

    def validate(self, actions):
        """Validate the list of action objects against the builder schema.

        :param actions: The list of action objects to validate.
        """
        jsonschema.validate(actions, self.schema)

    def _build(self, func, times, *args, **kwargs):
        """Build the wrapper action call."""
        def _f():
            for i in range(times):
                func(*args, **kwargs)
        return _f

    def build_actions(self, actions, *args, **kwargs):
        """Build a list of callable actions.

        A list of callable actions based on the given action object list and
        the actions bound to this builder.

        :param actions: A list of action objects to build callable
        action for.
        :param args: (optional) Positional args to pass into each
        built action. These will be appended to any args set for the
        action via its binding.
        :param kwargs: (optional) Keyword args to pass into each built
        action. These will be appended to any kwards set for the action
        via its binding.
        """
        self.validate(actions)
        bound_actions = []
        for action in actions:
            action_key = list(action)[0]
            times = action.get(action_key)
            binding = self._bindings.get(action_key)
            dft_kwargs = dict(binding["kwargs"])
            dft_kwargs.update(kwargs or {})
            bound_actions.append(
                self._build(binding["action"], times,
                            *(binding["args"] + args), **dft_kwargs))
        return bound_actions
