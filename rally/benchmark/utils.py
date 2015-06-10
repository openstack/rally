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
from rally.common import log as logging
from rally import consts
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
                                                    status=status)

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


class ActionBuilder(object):
    """Builder class for mapping and creating action objects.

    An action list is an array of single key/value dicts which takes
    the form:

    [{"action": times}, {"action": times}...]

    Here 'action' is a string which indicates a action to perform and
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
