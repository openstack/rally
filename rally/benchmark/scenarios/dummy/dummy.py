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


class Dummy(base.Scenario):
    """Benchmarks for testing Rally benchmark engine at scale."""

    @base.scenario()
    def dummy(self, sleep=0):
        """Test the performance of ScenarioRunners.

        Dummy.dummy can be used for testing performance of different
        ScenarioRunners and ability of rally to store a large
        amount of results.

        :param sleep: Idle time of method.
        """
        if sleep:
            time.sleep(sleep)

    @validation.number("size_of_message",
                       minval=1, integer_only=True, nullable=True)
    @base.scenario()
    def dummy_exception(self, size_of_message=1):
        """Test if exceptions are processed properly.

        Dummy.dummy_exception can be used for test if Exceptions are processed
        properly by ScenarioRunners and benchmark and analyze rally
        results storing process.

        :param size_of_message: the size of the message.
        """

        raise exceptions.DummyScenarioException("M" * size_of_message)

    @validation.number("exception_probability",
                       minval=0, maxval=1, integer_only=False, nullable=True)
    @base.scenario()
    def dummy_exception_probability(self, exception_probability=0.5):
        """Test if exceptions are processed properly.

        This scenario will throw an exception sometimes.

        :param exception_probability: Sets how likely it is that an exception
                                      will be thrown. Float between 0 and 1
                                      0=never 1=always.
        """

        if random.random() < exception_probability:
            raise exceptions.DummyScenarioException(
                "Dummy Scenario Exception: Probability: %s"
                % exception_probability
            )

    @base.scenario()
    def dummy_with_scenario_output(self):
        out = {
            'value_1': random.randint(1, 100),
            'value_2': random.random()
        }
        err = ""
        return {"data": out, "errors": err}
