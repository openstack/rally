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

from rally.plugins.openstack import scenario
from rally.task import atomic


class MagnumScenario(scenario.OpenStackScenario):
    """Base class for Magnum scenarios with basic atomic actions."""

    @atomic.action_timer("magnum.list_baymodels")
    def _list_baymodels(self, **kwargs):
        """Return list of baymodels.

        :param limit: (Optional) The maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of baymodels to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for baymodels listing

        :returns: baymodels list
        """

        return self.clients("magnum").baymodels.list(**kwargs)

    @atomic.action_timer("magnum.create_baymodel")
    def _create_baymodel(self, **kwargs):
        """Create a baymodel

        :param kwargs: optional additional arguments for baymodel creation
        :returns: magnum baymodel
        """

        kwargs["name"] = self.generate_random_name()

        return self.clients("magnum").baymodels.create(**kwargs)
