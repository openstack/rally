from rally import consts
from rally import exceptions
from rally.task import utils
from rally.task import atomic
from rally.task import validation
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.verify_sfc_api", context={"cleanup@openstack": ["nova", "neutron"]}, platform="openstack")

class VerifySFCAPI(neutron_utils.NeutronScenario, vcpe_utils.vCPEScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, image, flavor):
        
        net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": src_cidr}, 1, None)
        net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": dest_cidr}, 1, None)
        net3, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "1.1.0.0/24"}, 1, None)
        net4, sub4 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "2.2.0.0/24"}, 1, None)

        router = self._create_router({}, False)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub4[0].get("subnet"), router.get("router"))

        
        net1_id = net1.get('network', {}).get('id')
        net2_id = net2.get('network', {}).get('id')
        port_create_args = {}
        pin = self._create_port(net3, port_create_args)
        pout = self._create_port(net4, port_create_args)
        
        kwargs = {}
        pin_id = pin.get('port', {}).get('id')
        pout_id = pout.get('port', {}).get('id')
        nics = [{"port-id": pin_id}, {"port-id": pout_id}]
        kwargs.update({'nics': nics})
        
        inst = self._boot_server(image, flavor, False, **kwargs)
    
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

        self._delete_port_chain(pc)
        self._delete_port_pair_group(ppg)
        self._delete_flow_classifier(fc)
        self._delete_port_pair(pp)

