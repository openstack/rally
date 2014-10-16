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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.zaqar import utils as zutils
from rally.benchmark import validation


class ZaqarBasic(zutils.ZaqarScenario):

    @validation.number("name_length", minval=10)
    @base.scenario(context={"cleanup": ["zaqar"]})
    def create_queue(self, name_length=10, **kwargs):
        """Creates Zaqar queue with random name.

        :param name_length: length of generated (random) part of name
        :param **kwargs: Other optional parameters to create queues like
                        "metadata".
        """

        self._queue_create(name_length=name_length, **kwargs)
