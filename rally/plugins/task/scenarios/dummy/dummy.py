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

import random
import typing as t

from rally.common import utils
from rally.common import validation
from rally import exceptions
from rally.task import atomic
from rally.task import scenario


"""Dummy scenarios for testing Rally engine at scale."""


class DummyScenarioException(exceptions.RallyException):
    error_code = 244
    msg_fmt = "Dummy scenario expected exception: '%(message)s'"


@scenario.configure(name="Dummy.failure")
class DummyFailure(scenario.Scenario):

    def run(
        self,
        sleep: float = 0.1,
        from_iteration: int = 0,
        to_iteration: int = 0,
        each: int = 1,
    ) -> None:
        """Raise errors in some iterations.

        :param sleep: float iteration sleep time in seconds
        :param from_iteration: int iteration number which starts range
                             of failed iterations
        :param to_iteration: int iteration number which ends range of
                             failed iterations
        :param each: int cyclic number of iteration which actually raises
                     an error in selected range. For example, each=3 will
                     raise error in each 3rd iteration.
        """
        utils.interruptable_sleep(sleep)
        if from_iteration <= self.context["iteration"] <= to_iteration:
            if each and not self.context["iteration"] % each:
                raise DummyScenarioException("Expected failure")


@scenario.configure(name="Dummy.dummy")
class Dummy(scenario.Scenario):

    @atomic.action_timer("bar")
    def bar(self, sleep: float) -> None:
        utils.interruptable_sleep(sleep)

    @atomic.action_timer("foo")
    def foo(self, sleep: float) -> None:
        self.bar(sleep)

    def run(self, sleep: float = 0, **kwargs: t.Any) -> None:
        """Do nothing and sleep for the given number of seconds (0 by default).

        Dummy.dummy can be used for testing performance of different
        ScenarioRunners and of the ability of rally to store a large
        amount of results.

        :param sleep: idle time of method (in seconds).
        """
        self.foo(sleep)


@validation.add("number", param_name="size_of_message", minval=1,
                integer_only=True, nullable=True)
@scenario.configure(name="Dummy.dummy_exception")
class DummyException(scenario.Scenario):

    def run(
        self,
        size_of_message: int = 1,
        sleep: float = 1,
        message: str = ""
    ) -> None:
        """Throws an exception.

        Dummy.dummy_exception used for testing if exceptions are processed
        properly by task engine and analyze rally results storing & displaying
        capabilities.

        :param size_of_message: int size of the exception message
        :param sleep: idle time of method (in seconds).
        :param message: message of the exception
        :raises DummyScenarioException: raise exception for test
        """
        utils.interruptable_sleep(sleep)

        message = message or "M" * size_of_message
        raise DummyScenarioException(message)


@validation.add("number", param_name="exception_probability",
                minval=0, maxval=1, integer_only=False, nullable=True)
@scenario.configure(name="Dummy.dummy_exception_probability")
class DummyExceptionProbability(scenario.Scenario):

    def run(self, exception_probability: float = 0.5) -> None:
        """Throws an exception with given probability.

        Dummy.dummy_exception_probability used for testing if exceptions are
        processed properly by task engine and analyze rally results storing
        & displaying capabilities.

        :param exception_probability: Sets how likely it is that an exception
                                      will be thrown. Float between 0 and 1
                                      0=never 1=always.
        """
        if random.random() < exception_probability:
            raise DummyScenarioException(
                "Dummy Scenario Exception: Probability: %s"
                % exception_probability)


@scenario.configure(name="Dummy.dummy_output")
class DummyOutput(scenario.Scenario):

    def run(self, random_range: int = 25) -> None:
        """Generate dummy output.

        This scenario generates example of output data.
        :param random_range: max int limit for generated random values
        """
        rand = lambda n: [n, random.randint(1, random_range)]
        desc = "This is a description text for %s"

        self.add_output(additive={"title": "Additive StatsTable",
                                  "description": desc % "Additive StatsTable",
                                  "chart_plugin": "StatsTable",
                                  "data": [rand("foo stat"), rand("bar stat"),
                                           rand("spam stat")]})

        self.add_output(additive={"title": ("Additive StackedArea "
                                            "(no description)"),
                                  "chart_plugin": "StackedArea",
                                  "data": [rand("foo %d" % i)
                                           for i in range(1, 7)],
                                  "label": "Measure this in Foo units"})

        self.add_output(additive={"title": "Additive Lines",
                                  "description": (
                                      desc % "Additive Lines"),
                                  "chart_plugin": "Lines",
                                  "data": [rand("bar %d" % i)
                                           for i in range(1, 4)],
                                  "label": "Measure this in Bar units"})
        self.add_output(additive={"title": "Additive Pie",
                                  "description": desc % "Additive Pie",
                                  "chart_plugin": "Pie",
                                  "data": [rand("spam %d" % i)
                                           for i in range(1, 4)]},
                        complete={"title": "Complete Lines",
                                  "description": desc % "Complete Lines",
                                  "chart_plugin": "Lines",
                                  "data": [
                                      [name, [rand(i) for i in range(1, 8)]]
                                      for name in ("Foo", "Bar", "Spam")],
                                  "label": "Measure this is some units",
                                  "axis_label": ("This is a custom "
                                                 "X-axis label")})
        self.add_output(complete={"title": "Complete StackedArea",
                                  "description": desc % "Complete StackedArea",
                                  "chart_plugin": "StackedArea",
                                  "data": [
                                      [name, [rand(i) for i in range(50)]]
                                      for name in ("alpha", "beta", "gamma")],
                                  "label": "Yet another measurement units",
                                  "axis_label": ("This is a custom "
                                                 "X-axis label")})
        self.add_output(
            complete={"title": "Arbitrary Text",
                      "chart_plugin": "TextArea",
                      "data": ["Lorem ipsum dolor sit amet, consectetur "
                               "adipiscing elit, sed do eiusmod tempor "
                               "incididunt ut labore et dolore magna "
                               "aliqua." * 2] * 4})
        self.add_output(
            complete={"title": "Complete Pie (no description)",
                      "chart_plugin": "Pie",
                      "data": [rand("delta"), rand("epsilon"), rand("zeta"),
                               rand("theta"), rand("lambda"), rand("omega")]})

        data = {"cols": ["mu column", "xi column", "pi column",
                         "tau column", "chi column"],
                "rows": [([name + " row"] + [rand(i)[1] for i in range(4)])
                         for name in ("iota", "nu", "rho", "phi", "psi")]}
        self.add_output(complete={"title": "Complete Table",
                                  "description": desc % "Complete Table",
                                  "chart_plugin": "Table",
                                  "data": data})


@scenario.configure(name="Dummy.dummy_random_fail_in_atomic")
class DummyRandomFailInAtomic(scenario.Scenario):
    """Randomly throw exceptions in atomic actions."""

    def _play_roulette(self, exception_probability: float) -> None:
        """Throw an exception with given probability.

        :raises KeyError: when exception_probability is bigger
        """
        if random.random() < exception_probability:
            raise KeyError("Dummy test exception")

    def run(self, exception_probability: float = 0.5) -> None:
        """Dummy.dummy_random_fail_in_atomic in dummy actions.

        Can be used to test atomic actions
        failures processing.

        :param exception_probability: Probability with which atomic actions
                                      fail in this dummy scenario (0 <= p <= 1)
        """
        # divide probability on the number of possible places to fail
        if exception_probability != 1:
            exception_probability = exception_probability / 4.0
        with atomic.ActionTimer(self, "dummy_fail_test"):
            self._play_roulette(exception_probability)
            with atomic.ActionTimer(self, "dummy_fail_inner_test"):
                self._play_roulette(exception_probability)

        with atomic.ActionTimer(self, "dummy_fail_test"):
            self._play_roulette(exception_probability)
            with atomic.ActionTimer(self, "dummy_fail_inner_test"):
                self._play_roulette(exception_probability)


@scenario.configure(name="Dummy.dummy_random_action")
class DummyRandomAction(scenario.Scenario):

    def run(
        self,
        actions_num: int = 5,
        sleep_min: float = 0,
        sleep_max: float = 0
    ) -> None:
        """Sleep random time in dummy actions.

        :param actions_num: int number of actions to generate
        :param sleep_min: minimal time to sleep, numeric seconds
        :param sleep_max: maximum time to sleep, numeric seconds
        """
        for idx in range(actions_num):
            duration = random.uniform(sleep_min, sleep_max)
            with atomic.ActionTimer(self, "action_%d" % idx):
                utils.interruptable_sleep(duration)


@scenario.configure(name="Dummy.dummy_timed_atomic_actions")
class DummyTimedAtomicAction(scenario.Scenario):

    def run(
        self,
        number_of_actions: int = 5,
        sleep_factor: float = 1
    ) -> None:
        """Run some sleepy atomic actions for SLA atomic action tests.

        :param number_of_actions: int number of atomic actions to create
        :param sleep_factor: int multiplier for number of seconds to sleep
        """
        for sleeptime in range(number_of_actions):
            with atomic.ActionTimer(self, "action_%d" % sleeptime):
                utils.interruptable_sleep(sleeptime * sleep_factor)
