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

import functools

from rally.common import utils


class ActionTimerMixin(object):

    def __init__(self):
        self._atomic_actions = []

    def atomic_actions(self):
        """Returns the content of each atomic action."""
        return self._atomic_actions


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
        if atomic_actions and "finished_at" not in atomic_actions[-1]:
            return self._find_parent(atomic_actions[-1]["children"])
        else:
            return atomic_actions

    def __enter__(self):
        super(ActionTimer, self).__enter__()
        self.atomic_action["started_at"] = self.start

    def __exit__(self, type_, value, tb):
        super(ActionTimer, self).__exit__(type_, value, tb)
        self.atomic_action["finished_at"] = self.finish


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
            if kwargs.pop(argument_name, default):
                with ActionTimer(self, name):
                    f = func(self, *args, **kwargs)
            else:
                f = func(self, *args, **kwargs)
            return f
        return func_atomic_actions
    return wrap
