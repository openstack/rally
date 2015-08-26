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

from rally.common import costilius
from rally.common import utils


class ActionTimerMixin(object):

    def __init__(self):
        self._atomic_actions = costilius.OrderedDict()

    def atomic_actions(self):
        """Returns the content of each atomic action."""
        return self._atomic_actions


class ActionTimer(utils.Timer):
    """A class to measure the duration of atomic operations

    This would simplify the way measure atomic operation duration
    in certain cases. For example if we want to get the duration
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
        self.name = self._get_atomic_action_name(name)
        self.instance._atomic_actions[self.name] = None

    def _get_atomic_action_name(self, name):
        # TODO(boris-42): It was quite bad idea to store atomic actions
        #                 inside {}. We should refactor this in 0.2.0 release
        #                 and store them inside array, that will allow us to
        #                 store atomic actions with the same name
        if name not in self.instance._atomic_actions:
            return name

        name_template = name + " (%i)"
        i = 2
        while name_template % i in self.instance._atomic_actions:
            i += 1
        return name_template % i

    def __exit__(self, type_, value, tb):
        super(ActionTimer, self).__exit__(type_, value, tb)
        if type_ is None:
            self.instance._atomic_actions[self.name] = self.duration()


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
