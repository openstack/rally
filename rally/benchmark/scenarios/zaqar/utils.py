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


class ZaqarScenario(base.Scenario):

    @base.atomic_action_timer('zaqar.create_queue')
    def _queue_create(self, name_length=10, **kwargs):
        """Creates Zaqar queue with random name.

        :param name_length: length of generated (random) part of name
        :param **kwargs: Other optional parameters to create queues like
                        "metadata".
        :returns: zaqar queue instance
        """

        name = self._generate_random_name(length=name_length)
        return self.clients("zaqar").queue(name, **kwargs)