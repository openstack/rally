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
import time

from rally.benchmark.scenarios import base
from rally.benchmark import validation
from rally import exceptions


class DummyScenarioException(exceptions.RallyException):
    msg_fmt = _("Dummy scenario expected exception: '%(msg)s'")


class Dummy(base.Scenario):
    """Dummy benchmarks for testing Rally benchmark engine at scale."""

    @base.scenario()
    def dummy(self, sleep=0):
        """Do nothing and sleep for the given number of seconds (0 by default).

        Dummy.dummy can be used for testing performance of different
        ScenarioRunners and of the ability of rally to store a large
        amount of results.

        :param sleep: idle time of method (in seconds).
        """
        if sleep:
            time.sleep(sleep)

    @validation.number("size_of_message",
                       minval=1, integer_only=True, nullable=True)
    @base.scenario()
    def dummy_exception(self, size_of_message=1):
        """Throw an exception.

        Dummy.dummy_exception can be used for test if exceptions are processed
        properly by ScenarioRunners and benchmark and analyze rally
        results storing process.

        :param size_of_message: int size of the exception message
        :raises: DummyScenarioException
        """

        raise DummyScenarioException("M" * size_of_message)

    @validation.number("exception_probability",
                       minval=0, maxval=1, integer_only=False, nullable=True)
    @base.scenario()
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

    @base.scenario()
    def dummy_with_scenario_output(self):
        """Return a dummy scenario output.

        Dummy.dummy_with_scenario_output can be used to test the scenario
        output processing.
        """
        out = {
            'value_1': random.randint(1, 100),
            'value_2': random.random()
        }
        err = ""
        return {"data": out, "errors": err}

    @base.atomic_action_timer("dummy_fail_test")
    def _random_fail_emitter(self, exception_probability):
        """Throw an exception with given probability.

        :raises: KeyError
        """
        if random.random() < exception_probability:
            raise KeyError("Dummy test exception")

    @base.scenario()
    def dummy_random_fail_in_atomic(self, exception_probability=0.5):
        """Randomly throw exceptions in atomic actions.

        Dummy.dummy_random_fail_in_atomic can be used to test atomic actions
        failures processing.

        :param exception_probability: Probability with which atomic actions
                                      fail in this dummy scenario (0 <= p <= 1)
        """
        self._random_fail_emitter(exception_probability)
        self._random_fail_emitter(exception_probability)
