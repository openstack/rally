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

from __future__ import annotations

import collections
import functools
import typing as t
import typing_extensions as te

from rally.common import logging
from rally.common import utils

LOG = logging.getLogger(__name__)


class AtomicAction(t.TypedDict):
    """Structure for atomic action data."""
    name: str
    children: list[AtomicAction]
    started_at: float | None
    finished_at: te.NotRequired[float]
    failed: te.NotRequired[bool]


class MergedAtomicAction(t.TypedDict):
    """Structure for merged atomic action data."""
    duration: float
    count: int
    children: dict[str, MergedAtomicAction]
    failed: te.NotRequired[bool]


class ActionTimerMixin:

    def __init__(self) -> None:
        self._atomic_actions: list[AtomicAction] = []

    def atomic_actions(self) -> list[AtomicAction]:
        """Returns the content of each atomic action."""
        return self._atomic_actions

    def reset_atomic_actions(self) -> None:
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

    def __init__(self, instance: ActionTimerMixin, name: str) -> None:
        """Create a new instance of the AtomicAction.

        :param instance: instance of subclass of ActionTimerMixin
        :param name: name of the ActionBuilder
        """
        super(ActionTimer, self).__init__()
        self.instance = instance
        self.name = name
        self._root = self._find_parent(self.instance._atomic_actions)
        self.atomic_action: AtomicAction = {
            "name": self.name,
            "children": [],
            "started_at": None
        }
        self._root.append(self.atomic_action)

    def _find_parent(
        self, atomic_actions: list[AtomicAction]
    ) -> list[AtomicAction]:
        while atomic_actions and "finished_at" not in atomic_actions[-1]:
            atomic_actions = atomic_actions[-1]["children"]
        return atomic_actions

    def __enter__(self) -> ActionTimer:
        super(ActionTimer, self).__enter__()
        self.atomic_action["started_at"] = self.start
        return self

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        tb: t.Any
    ) -> None:
        super(ActionTimer, self).__exit__(type_, value, tb)
        self.atomic_action["finished_at"] = self.finish
        if type_:
            self.atomic_action["failed"] = True


def action_timer(
    name: str
) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
    """Provide measure of execution time.

    Decorates methods of the Scenario class.
    This provides duration in seconds of each atomic action.
    """
    def wrap(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        @functools.wraps(func)
        def func_atomic_actions(
            self: ActionTimerMixin, *args: t.Any, **kwargs: t.Any
        ) -> t.Any:
            with ActionTimer(self, name):
                f = func(self, *args, **kwargs)
            return f
        return func_atomic_actions
    return wrap


def merge_atomic_actions(
    atomic_actions: list[AtomicAction],
    root: collections.OrderedDict[str, MergedAtomicAction] | None = None,
    depth: int = 0,
    depth_of_processing: int = 2
) -> collections.OrderedDict[str, MergedAtomicAction]:
    """Merge duplicates of atomic actions into one atomic action.

    :param atomic_actions: a list with atomic action
    :param root: an ordered dict to save atomics to (leave it with a default
        value, since the primary use case of that parameter is processing inner
        atomic actions)
    :param depth: current level of processing inner atomic actions
    :param depth_of_processing: the depth of processing of inner atomic actions
        (defaults to 2)
    """
    p_atomics: collections.OrderedDict[str, MergedAtomicAction] = (
        collections.OrderedDict() if root is None else root
    )
    for action in atomic_actions:
        if action["name"] not in p_atomics:
            p_atomics[action["name"]] = {
                "duration": 0,
                "count": 0,
                "children": collections.OrderedDict()
            }
        started_at = action.get("started_at")
        if started_at is not None:
            duration = action["finished_at"] - started_at
        else:
            duration = 0.0
        p_atomics[action["name"]]["duration"] += duration
        p_atomics[action["name"]]["count"] += 1
        if action.get("failed"):
            p_atomics[action["name"]]["failed"] = True
        if action["children"] and depth < depth_of_processing:
            children_dict = p_atomics[action["name"]]["children"]
            if isinstance(children_dict, collections.OrderedDict):
                merge_atomic_actions(
                    action["children"],
                    root=children_dict,
                    depth=depth + 1)

    return p_atomics
