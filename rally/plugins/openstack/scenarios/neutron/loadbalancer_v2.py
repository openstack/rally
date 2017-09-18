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
from rally.plugins.openstack.scenarios.neutron import utils
from rally.task import validation


"""Scenarios for Neutron Loadbalancer v2."""


@validation.add("required_neutron_extensions", extensions=["lbaasv2"])
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@validation.add("required_contexts", contexts=("network"))
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronLoadbalancerV2.create_and_list_loadbalancers",
                    platform="openstack")
class CreateAndListLoadbalancers(utils.NeutronScenario):

    def run(self, lb_create_args=None):
        """Create a loadbalancer(v2) and then list loadbalancers(v2).

        Measure the "neutron lbaas-loadbalancer-list" command performance.
        The scenario creates a loadbalancer for every subnet and then lists
        loadbalancers.

        :param lb_create_args: dict, POST /lbaas/loadbalancers
                               request options
        """
        lb_create_args = lb_create_args or {}
        subnets = []
        networks = self.context.get("tenant", {}).get("networks", [])
        for network in networks:
            subnets.extend(network.get("subnets", []))
        for subnet_id in subnets:
            self._create_lbaasv2_loadbalancer(subnet_id, **lb_create_args)
        self._list_lbaasv2_loadbalancers()
