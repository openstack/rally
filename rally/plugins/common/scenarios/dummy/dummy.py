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

import random

from rally.common.i18n import _
from rally.common import utils
from rally import exceptions
from rally.task import atomic
from rally.task import scenario
from rally.task import validation


class DummyScenarioException(exceptions.RallyException):
    msg_fmt = _("Dummy scenario expected exception: '%(message)s'")


class Dummy(scenario.Scenario):
    """Dummy benchmarks for testing Rally benchmark engine at scale."""

    @scenario.configure()
    def dummy(self, sleep=0):
        """Do nothing and sleep for the given number of seconds (0 by default).

        Dummy.dummy can be used for testing performance of different
        ScenarioRunners and of the ability of rally to store a large
        amount of results.

        :param sleep: idle time of method (in seconds).
        """
        utils.interruptable_sleep(sleep)

    @validation.number("size_of_message",
                       minval=1, integer_only=True, nullable=True)
    @scenario.configure()
    def dummy_exception(self, size_of_message=1, sleep=0, message=""):
        """Throw an exception.

        Dummy.dummy_exception can be used for test if exceptions are processed
        properly by ScenarioRunners and benchmark and analyze rally
        results storing process.

        :param size_of_message: int size of the exception message
        :param sleep: idle time of method (in seconds).
        :param message: message of the exception
        :raises DummyScenarioException: raise exception for test
        """
        utils.interruptable_sleep(sleep)

        message = message or "M" * size_of_message
        raise DummyScenarioException(message)

    @validation.number("exception_probability",
                       minval=0, maxval=1, integer_only=False, nullable=True)
    @scenario.configure()
    def dummy_exception_probability(self, exception_probability=0.5):
        """Throw an exception with given probability.

        Dummy.dummy_exception_probability can be used to test if exceptions
        are processed properly by ScenarioRunners. This scenario will throw
        an exception sometimes, depending on the given exception probability.

        :param exception_probability: Sets how likely it is that an exception
                                      will be thrown. Float between 0 and 1
                                      0=never 1=always.
        """

        if random.random() < exception_probability:
            raise DummyScenarioException(
                "Dummy Scenario Exception: Probability: %s"
                % exception_probability
            )

    @scenario.configure()
    def dummy_output(self, random_range=25):
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

    @scenario.configure()
    def dummy_with_scenario_output(self):
        """Return a dummy scenario output.

        Dummy.dummy_with_scenario_output can be used to test the scenario
        output processing.
        """
        out = {
            "value_1": random.randint(1, 100),
            "value_2": random.random()
        }
        err = ""
        return {"data": out, "errors": err}

    @atomic.action_timer("dummy_fail_test")
    def _random_fail_emitter(self, exception_probability):
        """Throw an exception with given probability.

        :raises KeyError: when exception_probability is bigger
        """
        if random.random() < exception_probability:
            raise KeyError("Dummy test exception")

    @scenario.configure()
    def dummy_random_fail_in_atomic(self, exception_probability=0.5):
        """Randomly throw exceptions in atomic actions.

        Dummy.dummy_random_fail_in_atomic can be used to test atomic actions
        failures processing.

        :param exception_probability: Probability with which atomic actions
                                      fail in this dummy scenario (0 <= p <= 1)
        """
        self._random_fail_emitter(exception_probability)
        self._random_fail_emitter(exception_probability)
