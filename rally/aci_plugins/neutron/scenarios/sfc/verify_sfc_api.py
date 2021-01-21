from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.verify_sfc_api", context={"cleanup@openstack": ["nova", "neutron"]}, platform="openstack")

class VerifySFCAPI(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                   nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, image, flavor, ipv6_cidr, ipv6_dest_cidr, dualstack):
        
        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr)
        router = self._create_router({}, False)
        self.add_interface_to_router(router, sub_list)
        
        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')

        port_create_args = {}
        inst, pin, pout = self.boot_server(net_list[2], port_create_args, image, flavor, net2=net_list[3], service_vm=True)
        try:
            pp = self._create_port_pair(pin, pout)
            ppg = self._create_port_pair_group([pp])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc])

            self._list_port_pairs()
            self._list_port_pair_groups()
            self._list_flow_classifiers()
            self._list_port_chains()

            self._show_port_pair(pp)
            self._show_port_pair_group(ppg)
            self._show_flow_classifier(fc)
            self._show_port_chain(pc)

            self._update_port_pair(pp)
            self._update_port_pair_group(ppg, [pp])
            self._update_flow_classifier(fc)
            self._update_port_chain(pc, [ppg], [fc])
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()




