# Copyright 2016: Mirantis Inc.
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


"""
SLA (Service-level agreement) is set of details for determining compliance
with contracted values such as maximum error rate or minimum response time.
"""

from __future__ import annotations

import collections
import typing as t

from rally import consts
from rally.common import streaming_algorithms
from rally.task import sla


if t.TYPE_CHECKING:  # pragma: no cover
    from rally.task import atomic
    from rally.task import runner


def _iter_atomic_actions(
    atomic_actions: t.Sequence[atomic.AtomicAction],
) -> t.Iterator[atomic.AtomicAction]:
    """Iterate over atomic actions of all nesting levels."""
    for action in atomic_actions:
        yield action
        yield from _iter_atomic_actions(action.get("children") or [])


@sla.configure(name="max_avg_duration_per_atomic")
class MaxAverageDurationPerAtomic(sla.SLA):
    """Maximum average duration of an atomic action in seconds.

    A criterion name is matched against atomic actions of any nesting level,
    so nested atomic actions can be checked as well as top-level ones. Each
    execution of an atomic action counts as a separate one, so an action that
    is called several times per iteration is averaged per call, not per
    iteration.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "patternProperties": {
            ".*": {
                "type": "number",
                "description": "The name of atomic action.",
            }
        },
        "minProperties": 1,
        "additionalProperties": False,
    }

    def __init__(self, criterion_value: dict[str, float]) -> None:
        super().__init__(criterion_value)
        self.avg_by_action: dict[str, float] = {}
        self.avg_comp_by_action: collections.defaultdict[
            str, streaming_algorithms.MeanComputation
        ] = collections.defaultdict(streaming_algorithms.MeanComputation)
        self.criterion_items = self.criterion_value.items()

    def _check_criterion(self) -> bool:
        # NOTE(andreykurilin): an atomic action that had never been
        #   executed is not a reason to fail the SLA.
        return all(
            self.avg_by_action.get(atom, 0.0) <= val
            for atom, val in self.criterion_items
        )

    def add_iteration(self, iteration: runner.ScenarioRunnerResult) -> bool:
        if not iteration.get("error"):
            for action in _iter_atomic_actions(iteration["atomic_actions"]):
                started_at = action.get("started_at")
                finished_at = action.get("finished_at")
                if started_at is None or finished_at is None:
                    continue
                duration = finished_at - started_at
                name = action["name"]
                self.avg_comp_by_action[name].add(duration)
                self.avg_by_action[name] = (
                    self.avg_comp_by_action[name].result() or 0.0
                )
        self.success = self._check_criterion()
        return self.success

    def merge(self, other: MaxAverageDurationPerAtomic) -> bool:
        for atom, comp in other.avg_comp_by_action.items():
            self.avg_comp_by_action[atom].merge(comp)
        for atom, comp in self.avg_comp_by_action.items():
            self.avg_by_action[atom] = comp.result() or 0.0
        self.success = self._check_criterion()
        return self.success

    def details(self) -> str:
        strs = [
            "Action: '%s'. %.2fs <= %.2fs"
            % (atom, self.avg_by_action.get(atom, 0.0), val)
            for atom, val in self.criterion_items
        ]
        return "\n".join([
            "Average duration of one iteration for atomic actions:",
            *strs,
            f"Status: {self.status()}"
        ])
