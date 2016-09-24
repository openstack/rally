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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.magnum import utils
from rally.task import validation


"""Scenarios for Magnum cluster_templates."""


@validation.required_services(consts.Service.MAGNUM)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["magnum"]},
                    name="MagnumClusterTemplates.list_cluster_templates")
class ListClusterTemplates(utils.MagnumScenario):

    def run(self, **kwargs):
        """List all cluster_templates.

        Measure the "magnum cluster_template-list" command performance.

        :param limit: (Optional) The maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of cluster_templates to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: optional additional arguments for cluster_templates
                       listing
        """
        self._list_cluster_templates(**kwargs)
