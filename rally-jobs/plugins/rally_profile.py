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


from rally.common import utils
from rally.task import atomic
from rally.task import scenario


@scenario.configure(name="RallyProfile.generate_names_in_atomic")
class GenerateNamesInAtomic(scenario.Scenario, utils.RandomNameGeneratorMixin):

    def run(self, number_of_names):
        """Generate random names in atomic.

        :param number_of_names: int number of names to create
        """
        with atomic.ActionTimer(self, "generate_%s_names" % number_of_names):
            for i in range(number_of_names):
                self.generate_random_name()


@scenario.configure(name="RallyProfile.calculate_atomic")
class CalculateAtomic(scenario.Scenario, utils.RandomNameGeneratorMixin):

    def run(self, number_of_atomics):
        """Calculate atomic actions.

        :param number_of_atomics: int number of atomics to run
        """
        tmp_name = "tmp_actions"

        calc_atomic_name = "calculate_%s_atomics" % number_of_atomics
        with atomic.ActionTimer(self, calc_atomic_name):
            for _ in range(number_of_atomics):
                with atomic.ActionTimer(self, tmp_name):
                    pass

        self._atomic_actions = {
            calc_atomic_name: self._atomic_actions[calc_atomic_name]}
