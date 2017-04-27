# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.neutron import utils
from rally.task import validation


"""Scenarios for Neutron Networking-Bgpvpn."""


@validation.restricted_parameters(["name"])
@validation.required_neutron_extensions("bgpvpn")
@validation.required_services(consts.Service.NEUTRON)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"admin_cleanup": ["neutron"]},
                    name="NeutronBGPVPN.create_and_delete_bgpvpns")
class CreateAndDeleteBgpvpns(utils.NeutronScenario):

    def run(self, bgpvpn_create_args=None):
        """Create bgpvpn and delete the bgpvpn.

        Measure the "neutron bgpvpn-create" and bgpvpn-delete
        command performance.
        :param bgpvpn_create_args: dict, POST /v2.0/bgpvpn/bgpvpns request
        options
        """
        bgpvpn = self._create_bgpvpn(bgpvpn_create_args or {})
        self._delete_bgpvpn(bgpvpn)
