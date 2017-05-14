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


@validation.add("required_neutron_extensions", extensions=["bgpvpn"])
@validation.required_services(consts.Service.NEUTRON)
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup": ["neutron"]},
                    name="NeutronBGPVPN.create_and_delete_bgpvpns")
class CreateAndDeleteBgpvpns(utils.NeutronScenario):

    def run(self, route_targets=None, import_targets=None,
            export_targets=None, route_distinguishers=None, type="l3"):
        """Create bgpvpn and delete the bgpvpn.

        Measure the "neutron bgpvpn-create" and neutron bgpvpn-delete
        command performance.

        :param route_targets: Route Targets that will be both imported and
        used for export
        :param import_targets: Additional Route Targets that will be imported
        :param export_targets: Additional Route Targets that will be used
        for export.
        :param route_distinguishers: List of route distinguisher strings
        :param type: type of VPN and the technology behind it.
                     Acceptable formats: l2 and l3
        """
        bgpvpn = self._create_bgpvpn(route_targets=route_targets,
                                     import_targets=import_targets,
                                     export_targets=export_targets,
                                     route_distinguishers=route_distinguishers,
                                     type=type)
        self._delete_bgpvpn(bgpvpn)


@validation.add("required_neutron_extensions", extensions=["bgpvpn"])
@validation.required_services(consts.Service.NEUTRON)
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup": ["neutron"]},
                    name="NeutronBGPVPN.create_and_list_bgpvpns")
class CreateAndListBgpvpns(utils.NeutronScenario):

    def run(self, route_targets=None, import_targets=None,
            export_targets=None, route_distinguishers=None, type="l3"):
        """Create a bgpvpn and then list all bgpvpns

        Measure the "neutron bgpvpn-list" command performance.

        :param route_targets: Route Targets that will be both imported and
        used for export
        :param import_targets: Additional Route Targets that will be imported
        :param export_targets: Additional Route Targets that will be used
        for export.
        :param route_distinguishers: List of route distinguisher strings
        :param type: type of VPN and the technology behind it.
                     Acceptable formats: l2 and l3
        """
        bgpvpn = self._create_bgpvpn(route_targets=route_targets,
                                     import_targets=import_targets,
                                     export_targets=export_targets,
                                     route_distinguishers=route_distinguishers,
                                     type=type)
        bgpvpns = self._list_bgpvpns()
        self.assertIn(bgpvpn["bgpvpn"]["id"], [b["id"] for b in bgpvpns])


@validation.add("required_neutron_extensions", extensions=["bgpvpn"])
@validation.required_services(consts.Service.NEUTRON)
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup": ["neutron"]},
                    name="NeutronBGPVPN.create_and_update_bgpvpns")
class CreateAndUpdateBgpvpns(utils.NeutronScenario):

    def run(self, update_name=False, route_targets=None,
            import_targets=None, export_targets=None,
            route_distinguishers=None, updated_route_targets=None,
            updated_import_targets=None, updated_export_targets=None,
            updated_route_distinguishers=None, bgpvpn_type="l3"):
        """Create and Update bgpvpns

        Measure the "neutron bgpvpn-update" command performance.

        :param update_name: bool, whether or not to modify BGP VPN name
        :param route_targets: Route Targets that will be both imported
        and used for export
        :param updated_route_targets: Updated Route Targets that will be both
        imported and used for export
        :param import_targets: Additional Route Targets that will be imported
        :param updated_import_targets: Updated additional Route Targets that
        will be imported
        :param export_targets: additional Route Targets that will be used
        for export.
        :param updated_export_targets: Updated additional Route Targets that
        will be used for export.
        :param route_distinguishers: list of route distinguisher strings
        :param updated_route_distinguishers: Updated list of route
        distinguisher strings
        :param bgpvpn_type: type of VPN and the technology behind it.
                            Acceptable formats: l2 and l3
        """
        create_bgpvpn_args = {
            "route_targets": route_targets,
            "import_targets": import_targets,
            "export_targets": export_targets,
            "route_distinguishers": route_distinguishers,
            "type": bgpvpn_type
        }
        bgpvpn = self._create_bgpvpn(**create_bgpvpn_args)
        update_bgpvpn_args = {
            "update_name": update_name,
            "route_targets": updated_route_targets,
            "import_targets": updated_import_targets,
            "export_targets": updated_export_targets,
            "route_distinguishers": updated_route_distinguishers,
        }
        self._update_bgpvpn(bgpvpn, **update_bgpvpn_args)
