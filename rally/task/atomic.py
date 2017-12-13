# Copyright 2015: Mirantis Inc.
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

import collections
import functools

from rally.common import logging
from rally.common import utils

LOG = logging.getLogger(__name__)


class ActionTimerMixin(object):

    def __init__(self):
        self._atomic_actions = []

    def atomic_actions(self):
        """Returns the content of each atomic action."""
        return self._atomic_actions

    def reset_atomic_actions(self):
        """Clean all atomic action data."""
        self._atomic_actions = []


class ActionTimer(utils.Timer):
    """A class to measure the duration of atomic operations

    This would simplify the way measure atomic operation duration
    in certain cases. For example, if we want to get the duration
    for each operation which runs in an iteration
    for i in range(repetitions):
        with atomic.ActionTimer(instance_of_action_timer, "name_of_action"):
            self.clients(<client>).<operation>
    """

    def __init__(self, instance, name):
        """Create a new instance of the AtomicAction.

        :param instance: instance of subclass of ActionTimerMixin
        :param name: name of the ActionBuilder
        """
        super(ActionTimer, self).__init__()
        self.instance = instance
        self.name = name
        self._root = self._find_parent(self.instance._atomic_actions)
        self.atomic_action = {"name": self.name,
                              "children": [],
                              "started_at": None}
        self._root.append(self.atomic_action)

    def _find_parent(self, atomic_actions):
        while atomic_actions and "finished_at" not in atomic_actions[-1]:
            atomic_actions = atomic_actions[-1]["children"]
        return atomic_actions

    def __enter__(self):
        super(ActionTimer, self).__enter__()
        self.atomic_action["started_at"] = self.start

    def __exit__(self, type_, value, tb):
        super(ActionTimer, self).__exit__(type_, value, tb)
        self.atomic_action["finished_at"] = self.finish
        if type_:
            self.atomic_action["failed"] = True


def action_timer(name):
    """Provide measure of execution time.

    Decorates methods of the Scenario class.
    This provides duration in seconds of each atomic action.
    """
    def wrap(func):
        @functools.wraps(func)
        def func_atomic_actions(self, *args, **kwargs):
            with ActionTimer(self, name):
                f = func(self, *args, **kwargs)
            return f
        return func_atomic_actions
    return wrap


def optional_action_timer(name, argument_name="atomic_action", default=True):
    """Optionally provide measure of execution time.

    Decorates methods of the Scenario class. This provides duration in
    seconds of each atomic action. When the decorated function is
    called, this inspects the kwarg named by ``argument_name`` and
    optionally sets an ActionTimer around the function call.

    The ``atomic_action`` keyword argument does not need to be added
    to the function; it will be popped from the kwargs dict by the
    wrapper.

    :param name: The name of the timer
    :param argument_name: The name of the kwarg to inspect to
                          determine if a timer should be set.
    :param default: Whether or not to set a timer if ``argument_name``
                    is not present.
    """
    def wrap(func):
        @functools.wraps(func)
        def func_atomic_actions(self, *args, **kwargs):
            LOG.warning("'optional_action_timer' is deprecated"
                        "since rally v0.10.0."
                        "Please use action_timer instead, "
                        "we have improved atomic actions, "
                        "now do not need to explicitly close "
                        "original action.")
            if kwargs.pop(argument_name, default):
                with ActionTimer(self, name):
                    f = func(self, *args, **kwargs)
            else:
                f = func(self, *args, **kwargs)
            return f
        return func_atomic_actions
    return wrap


def merge_atomic_actions(atomic_actions, root=None, depth=0,
                         depth_of_processing=2):
    """Merge duplicates of atomic actions into one atomic action.

    :param atomic_actions: a list with atomic action
    :param root: an ordered dict to save atomics to (leave it with a default
        value, since the primary use case of that parameter is processing inner
        atomic actions)
    :param depth: current level of processing inner atomic actions
    :param depth_of_processing: the depth of processing of inner atomic actions
        (defaults to 2)
    """
    p_atomics = collections.OrderedDict() if root is None else root
    for action in atomic_actions:
        if action["name"] not in p_atomics:
            p_atomics[action["name"]] = {
                "duration": 0,
                "count": 0,
                "children": collections.OrderedDict()}
        duration = action["finished_at"] - action["started_at"]
        p_atomics[action["name"]]["duration"] += duration
        p_atomics[action["name"]]["count"] += 1
        if action.get("failed"):
            p_atomics[action["name"]]["failed"] = True
        if action["children"] and depth < depth_of_processing:
            merge_atomic_actions(
                action["children"],
                root=p_atomics[action["name"]]["children"],
                depth=depth + 1)

    return p_atomics
