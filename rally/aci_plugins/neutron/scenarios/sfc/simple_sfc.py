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
@scenario.configure(name="ScenarioPlugin.simple_sfc", context={"cleanup@openstack": ["nova", "neutron"]}, platform="openstack")

class SimpleSFC(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                scenario.OpenStackScenario):
    
    def run(self, src_cidr, dest_cidr, image, flavor):
        
        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr)
        router = self._create_router({}, False)
        self.add_interface_to_router(router, sub_list)
  
        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        psrc, p1_id = self.create_port(net_list[0], port_create_args)
        src_vm = self.boot_vm(p1_id, image, flavor)
        pdest, p2_id = self.create_port(net_list[1], port_create_args)
        dest_vm = self.boot_vm(p2_id, image, flavor)
        pin, pin_id = self.create_port(net_list[2], port_create_args)
        pout, pout_id = self.create_port(net_list[3], port_create_args)
        service_vm = self.boot_vm([pin_id, pout_id], image, flavor)

        try:
            pp = self._create_port_pair(pin, pout)
            ppg = self._create_port_pair_group([pp])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc])
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()


